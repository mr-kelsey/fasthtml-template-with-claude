from datetime import date
from urllib.parse import urlencode

from fasthtml import common as fast

from farm.layout import layout
from farm.helpers import (
    parse_optional_float,
    parse_optional_int,
    parse_required_float,
    validate_quantity_germinated,
    validate_non_negative,
    variety_photo_img,
)
from farm.pages.plantings import _harvest_batch_form, _validate_planting_ids
from calendar_shared import month_grid, events_by_date, month_nav, day_square, calendar_grid
import db

RECORDABLE_EVENT_TYPES = ("plant", "germination-check", "harvest")

router = fast.APIRouter()

EVENT_TYPE_COLORS = {
    "plant": "#2196f3",
    "germination-check": "#4caf50",
    "harvest": "#ff9800",
    "product-reminder": "#00897b",
    "custom": "#999999",
}

EVENT_TYPE_OPTIONS = ["custom", "plant", "germination-check", "harvest"]


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


def _farm_event_row(event, year, month):
    "Auto-generated events (linked_planting_id/linked_product_application_id set) link back to their source instead of offering delete."
    label = f"{event['title']} ({event['event_type']})"
    if event["linked_planting_id"] is not None:
        detail_href = (
            f"/beds/{event['planting_bed_id']}?on_date={event['start_date']}"
            if event["planting_bed_id"]
            else f"/plantings/{event['linked_planting_id']}/edit"
        )
        parts = [label, " — auto-generated — ", fast.A("View source", href=detail_href)]
        if event["event_type"] in RECORDABLE_EVENT_TYPES:
            parts += [" | ", fast.A("Record", href=_farm_calendar_url(year, month, base=f"/farm-calendar/{event['id']}/record"))]
        return fast.Li(*parts)
    if event["linked_product_application_id"] is not None:
        return fast.Li(label, " — auto-generated — ", fast.A("View source", href="/products"))
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
    rows = [_farm_event_row(event, year, month) for event in events]
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
    if event["linked_planting_id"] is not None or event["linked_product_application_id"] is not None:
        return fast.Response("Auto-generated events can't be deleted directly.", status_code=403)
    db.delete_farm_event(event_id)
    return fast.Redirect("/farm-calendar")


def _optional_value(row, field):
    return "" if row[field] is None else row[field]


def _germination_record_row(planting, event_id, year, month):
    label = f"#{planting['id']}"
    sown = planting["quantity"] if planting["quantity"] is not None else "?"
    return fast.Li(
        f"{label} (sown: {sown})",
        fast.Form(
            fast.Input(
                name="quantity_germinated", type="number", min="0", placeholder="Quantity germinated",
                value=_optional_value(planting, "quantity_germinated"),
            ),
            fast.Input(type="hidden", name="redirect_year", value=str(year)),
            fast.Input(type="hidden", name="redirect_month", value=str(month)),
            fast.Button("Save", type="submit"),
            method="post",
            action=f"/farm-calendar/{event_id}/record/germination/{planting['id']}",
        ),
    )


def _planting_record_row(planting, event_id, year, month):
    return fast.Li(
        f"#{planting['id']}",
        fast.Form(
            fast.Input(
                name="quantity", type="number", min="0", placeholder="Quantity planted",
                value=_optional_value(planting, "quantity"),
            ),
            fast.Input(
                name="soil_temp_f", type="number", step="0.1", placeholder="Soil temp (F)",
                value=_optional_value(planting, "soil_temp_f"),
            ),
            fast.Input(type="hidden", name="redirect_year", value=str(year)),
            fast.Input(type="hidden", name="redirect_month", value=str(month)),
            fast.Button("Save", type="submit"),
            method="post",
            action=f"/farm-calendar/{event_id}/record/planting/{planting['id']}",
        ),
    )


def _group_harvest_record_row(harvest):
    "Basket-then-weigh harvesting means one harvest can span several plantings -- list which ones."
    planting_ids = db.get_harvest_planting_ids(harvest["id"])
    label = f"{harvest['harvest_date']}: {harvest['weight_lb']} lb across " + ", ".join(f"#{i}" for i in planting_ids)
    if harvest["notes"]:
        label += f" — {harvest['notes']}"
    return fast.Li(label)


@router("/farm-calendar/{event_id}/record", methods=["get"])
def record_event_page(event_id: int, year: int = None, month: int = None):
    "Small form(s) for recording germination-check/harvest results against the event's (variety, planted_date) group."
    event = db.get_farm_event(event_id)
    if event is None or event["event_type"] not in RECORDABLE_EVENT_TYPES or event["linked_planting_id"] is None:
        return fast.Response("Not found.", status_code=404)
    today = date.today()
    year = year or today.year
    month = month or today.month
    anchor = db.get_planting(event["linked_planting_id"])
    if anchor is None:
        return fast.Response("Linked planting no longer exists.", status_code=404)
    variety = db.get_seed_variety(anchor["variety_id"])
    variety_label = f"{variety['common_name']} - {variety['name']}" if variety else "Unknown variety"
    if event["event_type"] == "plant":
        group = db.list_plantings_in_group(anchor["variety_id"], anchor["planted_date"])
        content = (
            fast.H2(f"Record planting: {variety_label}"),
            fast.Ul(*[_planting_record_row(p, event_id, year, month) for p in group]),
        )
    elif event["event_type"] == "germination-check":
        group = db.list_plantings_in_group(anchor["variety_id"], anchor["planted_date"])
        reference_photo = variety_photo_img(variety, cls="variety-photo-reference") if variety else None
        content = (
            fast.H2(f"Record germination: {variety_label}"),
            *((reference_photo,) if reference_photo is not None else ()),
            fast.Ul(*[_germination_record_row(p, event_id, year, month) for p in group]),
        )
    else:
        group = db.list_plantings_in_group(anchor["variety_id"], anchor["planted_date"])
        harvests = db.list_harvests_for_group(anchor["variety_id"], anchor["planted_date"])
        content = (
            fast.H2(f"Record harvest: {variety_label}"),
            fast.Ul(*[_group_harvest_record_row(h) for h in harvests]) if harvests else fast.P("No harvests logged yet."),
            _harvest_batch_form(
                action=f"/farm-calendar/{event_id}/record/harvest",
                plantings=group,
                checked_ids=set(),
                redirect_fields=[
                    fast.Input(type="hidden", name="redirect_year", value=str(year)),
                    fast.Input(type="hidden", name="redirect_month", value=str(month)),
                ],
            ),
        )
    return layout(
        "Record Farm Event",
        fast.H1(event["title"]),
        *content,
        fast.A("Back to calendar", href=_farm_calendar_url(year, month)),
    )


@router("/farm-calendar/{event_id}/record/planting/{planting_id}", methods=["post"])
def record_planting_route(
    event_id: int, planting_id: int, quantity: str = "", soil_temp_f: str = "",
    redirect_year: str = "", redirect_month: str = "",
):
    event = db.get_farm_event(event_id)
    if event is None or event["event_type"] != "plant":
        return fast.Response("Not found.", status_code=404)
    planting = db.get_planting(planting_id)
    if planting is None:
        return fast.Response("Planting not found.", status_code=404)
    ok, quantity_value = parse_optional_int(quantity)
    if not ok:
        return fast.Response("Quantity must be a number.", status_code=422)
    error = validate_non_negative(quantity_value, "Quantity")
    if error:
        return fast.Response(error, status_code=422)
    ok, soil_temp_value = parse_optional_float(soil_temp_f)
    if not ok:
        return fast.Response("Soil temp must be a number.", status_code=422)
    db.record_planting(planting_id, quantity_value, soil_temp_value)
    today = date.today()
    year = _parse_int_or(redirect_year, today.year)
    month = _parse_int_or(redirect_month, today.month)
    return fast.Redirect(_farm_calendar_url(year, month, base=f"/farm-calendar/{event_id}/record"))


@router("/farm-calendar/{event_id}/record/germination/{planting_id}", methods=["post"])
def record_germination_route(
    event_id: int, planting_id: int, quantity_germinated: str = "", redirect_year: str = "", redirect_month: str = ""
):
    event = db.get_farm_event(event_id)
    if event is None or event["event_type"] != "germination-check":
        return fast.Response("Not found.", status_code=404)
    planting = db.get_planting(planting_id)
    if planting is None:
        return fast.Response("Planting not found.", status_code=404)
    ok, value = parse_optional_int(quantity_germinated)
    if not ok:
        return fast.Response("Quantity germinated must be a number.", status_code=422)
    error = validate_non_negative(value, "Quantity germinated")
    if error:
        return fast.Response(error, status_code=422)
    error = validate_quantity_germinated(value, planting["quantity"])
    if error:
        return fast.Response(error, status_code=422)
    db.set_quantity_germinated(planting_id, value)
    today = date.today()
    year = _parse_int_or(redirect_year, today.year)
    month = _parse_int_or(redirect_month, today.month)
    return fast.Redirect(_farm_calendar_url(year, month, base=f"/farm-calendar/{event_id}/record"))


@router("/farm-calendar/{event_id}/record/harvest", methods=["post"])
def record_harvest_route(
    event_id: int, harvest_date: str, weight_lb: str, planting_ids: list[str] = None,
    notes: str = "", redirect_year: str = "", redirect_month: str = "",
):
    event = db.get_farm_event(event_id)
    if event is None or event["event_type"] != "harvest" or event["linked_planting_id"] is None:
        return fast.Response("Not found.", status_code=404)
    harvest_date = harvest_date.strip()
    if not harvest_date or _parse_date(harvest_date) is None:
        return fast.Response("Invalid harvest date.", status_code=422)
    weight_lb_value, error = parse_required_float(weight_lb, "Weight")
    if error:
        return fast.Response(error, status_code=422)
    error = validate_non_negative(weight_lb_value, "Weight")
    if error:
        return fast.Response(error, status_code=422)
    ids = _validate_planting_ids(planting_ids or [])
    if isinstance(ids, fast.Response):
        return ids
    db.add_harvest(ids, harvest_date, weight_lb_value, notes=notes.strip() or None)
    today = date.today()
    year = _parse_int_or(redirect_year, today.year)
    month = _parse_int_or(redirect_month, today.month)
    return fast.Redirect(_farm_calendar_url(year, month, base=f"/farm-calendar/{event_id}/record"))
