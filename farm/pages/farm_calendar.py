from datetime import date
from urllib.parse import urlencode

from fasthtml import common as fast

from farm.layout import layout
from calendar_shared import month_grid, events_by_date, month_nav, day_square, calendar_grid
import db

router = fast.APIRouter()

EVENT_TYPE_COLORS = {
    "germination-check": "#4caf50",
    "harvest": "#ff9800",
    "custom": "#999999",
}

EVENT_TYPE_OPTIONS = ["custom", "germination-check", "harvest"]


def _farm_calendar_url(year, month, base="/farm-calendar"):
    return f"{base}?{urlencode({'year': year, 'month': month})}"


def _parse_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_int_or(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _event_bar(event):
    color = EVENT_TYPE_COLORS.get(event["event_type"], "#999999")
    return fast.Div(cls="event-bar", style=f"background-color: {color}", title=event["title"])


def _farm_day_square(day_date, in_current_month, is_today, events_for_day, year, month):
    badges = [fast.Div(*[_event_bar(event) for event in events_for_day], cls="event-bars")]
    day_url = _farm_calendar_url(year, month, base=f"/farm-calendar/day/{day_date.isoformat()}")
    return day_square(day_date, in_current_month, is_today, badges, day_url)


def _calendar_grid(weeks, month, events_map, today, year):
    return calendar_grid(
        weeks,
        month,
        today,
        lambda day_date, in_current_month, is_today: _farm_day_square(
            day_date, in_current_month, is_today, events_map.get(day_date, []), year, month
        ),
    )


def _month_nav(year, month):
    return month_nav(year, month, lambda nav_year, nav_month: _farm_calendar_url(nav_year, nav_month))


def _event_dialog():
    return fast.Dialog(fast.Div(id="event-dialog-body"), id="event-dialog")


def _custom_event_form(default_date, year, month):
    return fast.Form(
        fast.Input(name="title", placeholder="Title", required=True),
        fast.Select(
            *[fast.Option(event_type, value=event_type) for event_type in EVENT_TYPE_OPTIONS],
            name="event_type",
            required=True,
        ),
        fast.Input(name="start_date", type="date", value=default_date, required=True),
        fast.Textarea("", name="notes", placeholder="Notes (optional)"),
        fast.Input(type="hidden", name="redirect_year", value=str(year)),
        fast.Input(type="hidden", name="redirect_month", value=str(month)),
        fast.Button("Add Event", type="submit"),
        method="post",
        action="/farm-calendar",
    )


def _farm_event_row(event):
    "Auto-generated events (linked_planting_id set) link back to their source instead of offering delete."
    label = f"{event['title']} ({event['event_type']})"
    if event["linked_planting_id"] is not None:
        detail_href = (
            f"/beds/{event['planting_bed_id']}" if event["planting_bed_id"] else f"/plantings/{event['linked_planting_id']}/edit"
        )
        return fast.Li(label, " — auto-generated — ", fast.A("View source", href=detail_href))
    return fast.Li(
        label,
        fast.Form(
            fast.Button("Delete", type="submit"), method="post", action=f"/farm-calendar/{event['id']}/delete"
        ),
    )


@router("/farm-calendar", methods=["get"])
def farm_calendar_page(year: int = None, month: int = None):
    today = date.today()
    year = year or today.year
    month = month or today.month
    weeks = month_grid(year, month)
    grid_start, grid_end = weeks[0][0], weeks[-1][-1]
    events = db.list_farm_events_in_range(grid_start.isoformat(), grid_end.isoformat())
    events_map = events_by_date(events, grid_start, grid_end)
    return layout(
        "Farm Calendar",
        fast.H1("Farm Calendar"),
        _month_nav(year, month),
        _calendar_grid(weeks, month, events_map, today, year),
        _event_dialog(),
    )


@router("/farm-calendar/day/{event_date}", methods=["get"])
def farm_calendar_day_fragment(event_date: str, year: int = None, month: int = None):
    day = _parse_date(event_date)
    if day is None:
        return fast.Response("Invalid date.", status_code=422)
    year = year or day.year
    month = month or day.month
    events = db.list_farm_events_in_range(event_date, event_date)
    rows = [_farm_event_row(event) for event in events]
    return (
        fast.H3(day.isoformat()),
        fast.Ul(*rows) if rows else fast.P("No events yet."),
        _custom_event_form(default_date=event_date, year=year, month=month),
        fast.Button("Close", type="button", onclick="document.getElementById('event-dialog').close()"),
    )


def _validate_custom_event(title, start_date):
    "Returns (title, start_date) or an error fast.Response."
    title = title.strip()
    if not title:
        return fast.Response("Title is required.", status_code=422)
    start_date = start_date.strip()
    if not start_date or _parse_date(start_date) is None:
        return fast.Response("Invalid date.", status_code=422)
    return title, start_date


@router("/farm-calendar", methods=["post"])
def add_farm_event_route(
    title: str,
    event_type: str = "custom",
    start_date: str = "",
    notes: str = "",
    redirect_year: str = "",
    redirect_month: str = "",
):
    validated = _validate_custom_event(title, start_date)
    if isinstance(validated, fast.Response):
        return validated
    title, start_date = validated
    db.add_farm_event(event_type.strip() or "custom", title, start_date, start_date, notes=notes.strip() or None)
    today = date.today()
    year = _parse_int_or(redirect_year, today.year)
    month = _parse_int_or(redirect_month, today.month)
    return fast.Redirect(_farm_calendar_url(year, month))


@router("/farm-calendar/{event_id}/delete", methods=["post"])
def delete_farm_event_route(event_id: int):
    event = db.get_farm_event(event_id)
    if event is None:
        return fast.Redirect("/farm-calendar")
    if event["linked_planting_id"] is not None:
        return fast.Response("Auto-generated events can't be deleted directly.", status_code=403)
    db.delete_farm_event(event_id)
    return fast.Redirect("/farm-calendar")
