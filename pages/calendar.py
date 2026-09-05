import calendar as cal
from datetime import date, timedelta
from urllib.parse import urlencode

from fasthtml import common as fast

from layout import layout
from family import FAMILY_MEMBERS, get_member
import db

router = fast.APIRouter()

WEEKDAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def _calendar_url(year, month, member_id=None, base="/calendar"):
    params = {"year": year, "month": month}
    if member_id:
        params["member_id"] = member_id
    return f"{base}?{urlencode(params)}"


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


def _is_checkbox_checked(value):
    return value in ("1", "true", "on")


def _month_grid(year, month):
    return cal.Calendar(firstweekday=6).monthdatescalendar(year, month)


def _events_by_date(events, grid_start, grid_end):
    by_date = {}
    for event in events:
        event_start = max(date.fromisoformat(event["start_date"]), grid_start)
        event_end = min(date.fromisoformat(event["end_date"]), grid_end)
        current = event_start
        while current <= event_end:
            by_date.setdefault(current, []).append(event)
            current += timedelta(days=1)
    return by_date


def _event_bar(event):
    member = get_member(event["owner_id"])
    color = member["color"] if member else "#999999"
    return fast.Div(cls="event-bar", style=f"background-color: {color}", title=event["title"])


def _day_square(day_date, events_for_day, in_current_month, is_today, year, month, member_id):
    classes = ["day-square"]
    if not in_current_month:
        classes.append("outside-month")
    if is_today:
        classes.append("today")
    if any(event["is_critical"] for event in events_for_day):
        classes.append("critical-day")
    return fast.Div(
        fast.Div(str(day_date.day), cls="day-number"),
        *[_event_bar(event) for event in events_for_day],
        cls=" ".join(classes),
        hx_get=_calendar_url(year, month, member_id, base=f"/calendar/day/{day_date.isoformat()}"),
        hx_target="#event-dialog-body",
        hx_swap="innerHTML",
        **{"hx-on::after-request": "document.getElementById('event-dialog').showModal()"},
    )


def _calendar_grid(weeks, month, events_by_date, today, year, member_id):
    cells = [fast.Div(label, cls="calendar-weekday") for label in WEEKDAY_LABELS]
    for week in weeks:
        for day_date in week:
            cells.append(
                _day_square(
                    day_date,
                    events_by_date.get(day_date, []),
                    day_date.month == month,
                    day_date == today,
                    year,
                    month,
                    member_id,
                )
            )
    return fast.Div(*cells, cls="calendar-grid")


def _month_nav(year, month, member_id):
    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    today = date.today()
    return fast.Div(
        fast.A("< Prev", href=_calendar_url(prev_year, prev_month, member_id)),
        fast.Span(f"{cal.month_name[month]} {year}", cls="month-label"),
        fast.A("Next >", href=_calendar_url(next_year, next_month, member_id)),
        fast.A("Today", href=_calendar_url(today.year, today.month, member_id)),
        cls="month-nav",
    )


def _filter_row(year, month, member_id):
    def link(label, target_member_id, is_active):
        href = f"/calendar?year={year}&month={month}"
        if target_member_id:
            href += f"&member_id={target_member_id}"
        return fast.A(label, href=href, cls="active" if is_active else "")

    links = [link("Everyone", None, member_id is None)]
    links += [link(member["name"], member["id"], member_id == member["id"]) for member in FAMILY_MEMBERS]
    return fast.Div(*links, cls="filter-row")


def _event_dialog():
    return fast.Dialog(fast.Div(id="event-dialog-body"), id="event-dialog")


def _add_event_form(default_date="", year="", month="", member_id=""):
    return fast.Form(
        fast.Input(name="title", placeholder="Title", required=True),
        fast.Input(name="start_date", type="date", value=default_date, required=True),
        fast.Input(name="end_date", type="date"),
        fast.Input(name="start_time", type="time"),
        fast.Input(name="end_time", type="time"),
        fast.Textarea(name="notes", placeholder="Notes (optional)"),
        fast.Label(fast.Input(name="is_critical", type="checkbox", value="1"), " Can't miss"),
        fast.Input(type="hidden", name="redirect_year", value=str(year)),
        fast.Input(type="hidden", name="redirect_month", value=str(month)),
        fast.Input(type="hidden", name="redirect_member_id", value=member_id or ""),
        fast.Button("Add Event", type="submit"),
        method="post",
        action="/calendar",
    )


def _delete_event_form(event_id, year, month, member_id):
    return fast.Form(
        fast.Input(type="hidden", name="redirect_year", value=str(year)),
        fast.Input(type="hidden", name="redirect_month", value=str(month)),
        fast.Input(type="hidden", name="redirect_member_id", value=member_id or ""),
        fast.Button("Delete", type="submit"),
        method="post",
        action=f"/calendar/{event_id}/delete",
    )


@router("/calendar", methods=["get"])
def calendar_page(sess, year: int = None, month: int = None, member_id: str = None):
    if member_id and get_member(member_id) is not None:
        sess["member_id"] = member_id
    today = date.today()
    year = year or today.year
    month = month or today.month
    weeks = _month_grid(year, month)
    grid_start, grid_end = weeks[0][0], weeks[-1][-1]
    events = db.list_events_in_range(grid_start.isoformat(), grid_end.isoformat(), owner_id=member_id or None)
    events_by_date = _events_by_date(events, grid_start, grid_end)
    return layout(
        "Calendar",
        fast.H1("Family Calendar"),
        _month_nav(year, month, member_id),
        _filter_row(year, month, member_id),
        _calendar_grid(weeks, month, events_by_date, today, year, member_id),
        _event_dialog(),
    )


@router("/calendar/day/{event_date}", methods=["get"])
def calendar_day_fragment(sess, event_date: str, year: int = None, month: int = None, member_id: str = None):
    session_member_id = sess.get("member_id")
    day = _parse_date(event_date)
    if day is None:
        return fast.Response("Invalid date.", status_code=422)
    year = year or day.year
    month = month or day.month
    events = db.list_events_in_range(event_date, event_date, owner_id=member_id or None)
    rows = []
    for event in events:
        member = get_member(event["owner_id"])
        owner_name = member["name"] if member else event["owner_id"]
        delete_form = ""
        if event["owner_id"] == session_member_id:
            delete_form = _delete_event_form(event["id"], year, month, member_id)
        rows.append(fast.Li(f"{event['title']} — {owner_name}", delete_form))
    return (
        fast.H3(day.isoformat()),
        fast.Ul(*rows) if rows else fast.P("No events yet."),
        _add_event_form(default_date=event_date, year=year, month=month, member_id=member_id),
        fast.Button("Close", type="button", onclick="document.getElementById('event-dialog').close()"),
    )


@router("/calendar", methods=["post"])
def add_event_route(
    sess,
    title: str,
    start_date: str,
    end_date: str = "",
    start_time: str = "",
    end_time: str = "",
    notes: str = "",
    is_critical: str = "",
    redirect_year: str = "",
    redirect_month: str = "",
    redirect_member_id: str = "",
):
    member_id = sess.get("member_id")
    if member_id is None:
        return fast.Response("Pick a family member from the filter before adding events.", status_code=422)
    title = title.strip()
    start_date = start_date.strip()
    end_date = end_date.strip()
    if not title or not start_date:
        return fast.Response("Title and start date are required.", status_code=422)
    start_date_parsed = _parse_date(start_date)
    if start_date_parsed is None:
        return fast.Response("Invalid start date.", status_code=422)
    if end_date:
        end_date_parsed = _parse_date(end_date)
        if end_date_parsed is None:
            return fast.Response("Invalid end date.", status_code=422)
        if end_date_parsed < start_date_parsed:
            return fast.Response("End date cannot be before start date.", status_code=422)
    db.add_event(
        owner_id=member_id,
        title=title,
        start_date=start_date,
        end_date=end_date or None,
        start_time=start_time.strip() or None,
        end_time=end_time.strip() or None,
        notes=notes.strip() or None,
        is_critical=_is_checkbox_checked(is_critical),
    )
    year = _parse_int_or(redirect_year, start_date_parsed.year)
    month = _parse_int_or(redirect_month, start_date_parsed.month)
    return fast.Redirect(_calendar_url(year, month, redirect_member_id))


@router("/calendar/{event_id}/delete", methods=["post"])
def delete_event_route(
    sess, event_id: int, redirect_year: str = "", redirect_month: str = "", redirect_member_id: str = ""
):
    member_id = sess.get("member_id")
    event = db.get_event(event_id)
    if event is None:
        return fast.Redirect("/calendar")
    if event["owner_id"] != member_id:
        return fast.Response("You can only delete your own events.", status_code=403)
    db.delete_event(event_id)
    today = date.today()
    year = _parse_int_or(redirect_year, today.year)
    month = _parse_int_or(redirect_month, today.month)
    return fast.Redirect(_calendar_url(year, month, redirect_member_id))
