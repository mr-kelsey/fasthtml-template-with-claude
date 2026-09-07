import calendar as cal
from datetime import date
from urllib.parse import urlencode

from fasthtml import common as fast

from layout import layout
from family import FAMILY_MEMBERS, get_member
from calendar_shared import month_grid, events_by_date, month_nav, day_square, calendar_grid
import db

router = fast.APIRouter()


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


def _validate_event_dates(title, start_date, end_date):
    "Returns (title, start_date, end_date, start_date_parsed) or an error fast.Response."
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
    return title, start_date, end_date, start_date_parsed


def _recurring_events_by_date(recurring_events, weeks):
    by_date = {}
    for week in weeks:
        for day_date in week:
            matches = [
                recurring_event for recurring_event in recurring_events 
                if recurring_event["month"] == day_date.month and recurring_event["day"] == day_date.day
                ]
            if matches:
                by_date[day_date] = matches
    return by_date


def _event_bar(event):
    member = get_member(event["owner_id"])
    color = member["color"] if member else "#999999"
    return fast.Div(cls="event-bar", style=f"background-color: {color}", title=event["title"])


def _recurring_label(recurring_event):
    return fast.Div(recurring_event["title"], cls="recurring-label")


def _family_day_square(day_date, in_current_month, is_today, events_for_day, recurring_for_day, year, month, member_id):
    badges = [
        fast.Div(*[_event_bar(event) for event in events_for_day], cls="event-bars"),
        fast.Div(*[_recurring_label(r) for r in recurring_for_day], cls="recurring-labels"),
    ]
    extra_classes = ["critical-day"] if any(event["is_critical"] for event in events_for_day) else []
    day_url = _calendar_url(year, month, member_id, base=f"/calendar/day/{day_date.isoformat()}")
    return day_square(day_date, in_current_month, is_today, badges, day_url, extra_classes=extra_classes)


def _calendar_grid(weeks, month, events_map, recurring_by_date, today, year, member_id):
    return calendar_grid(
        weeks,
        month,
        today,
        lambda day_date, in_current_month, is_today: _family_day_square(
            day_date,
            in_current_month,
            is_today,
            events_map.get(day_date, []),
            recurring_by_date.get(day_date, []),
            year,
            month,
            member_id,
        ),
    )


def _month_nav(year, month, member_id):
    return month_nav(year, month, lambda nav_year, nav_month: _calendar_url(nav_year, nav_month, member_id))


def _filter_row(year, month, member_id):
    def link(label, target_member_id, is_active):
        href = _calendar_url(year, month, target_member_id) if target_member_id else _calendar_url(year, month)
        return fast.A(label, href=href, cls="active" if is_active else "")

    links = [link("Everyone", None, member_id is None)]
    links += [link(member["name"], member["id"], member_id == member["id"]) for member in FAMILY_MEMBERS]
    return fast.Div(*links, cls="filter-row")


def _event_dialog():
    return fast.Dialog(fast.Div(id="event-dialog-body"), id="event-dialog")


def _show_form_js(form_id):
    return (
        "document.querySelectorAll('#event-dialog-body .event-form').forEach(f => f.hidden = true); "
        f"document.getElementById('{form_id}').hidden = false;"
    )


def _event_form(
    form_id, action, submit_label, event=None, default_date="", year="", month="", member_id="", hidden=True
):
    return fast.Form(
        fast.Input(name="title", placeholder="Title", value=event["title"] if event else "", required=True),
        fast.Input(
            name="start_date",
            type="date",
            value=event["start_date"] if event else default_date,
            required=True,
        ),
        fast.Input(name="end_date", type="date", value=event["end_date"] if event else ""),
        fast.Input(name="start_time", type="time", value=(event["start_time"] or "") if event else ""),
        fast.Input(name="end_time", type="time", value=(event["end_time"] or "") if event else ""),
        fast.Textarea(event["notes"] or "" if event else "", name="notes", placeholder="Notes (optional)"),
        fast.Label(
            fast.Input(
                name="is_critical",
                type="checkbox",
                value="1",
                checked=bool(event["is_critical"]) if event else False,
            ),
            " Can't miss",
        ),
        fast.Input(type="hidden", name="redirect_year", value=str(year)),
        fast.Input(type="hidden", name="redirect_month", value=str(month)),
        fast.Input(type="hidden", name="redirect_member_id", value=member_id or ""),
        fast.Button(submit_label, type="submit"),
        method="post",
        action=action,
        id=form_id,
        cls="event-form",
        hidden=hidden,
    )


def _validate_recurring_event(title, month, day):
    "Returns (title, month, day) or an error fast.Response. Validated against a leap year so Feb 29 is allowed."
    title = title.strip()
    if not title:
        return fast.Response("Title is required.", status_code=422)
    try:
        month, day = int(month), int(day)
        date(2000, month, day)
    except (TypeError, ValueError):
        return fast.Response("Invalid month/day.", status_code=422)
    return title, month, day


def _month_select(selected_month=None):
    return fast.Select(
        *[
            fast.Option(cal.month_name[month], value=str(month), selected=(month == selected_month))
            for month in range(1, 13)
        ],
        name="month",
        required=True,
    )


def _recurring_event_form(action, submit_label, recurring_event=None):
    return fast.Form(
        fast.Input(
            name="title", placeholder="Title", value=recurring_event["title"] if recurring_event else "", required=True
        ),
        _month_select(recurring_event["month"] if recurring_event else None),
        fast.Input(
            name="day",
            type="number",
            min="1",
            max="31",
            value=recurring_event["day"] if recurring_event else "",
            required=True,
        ),
        fast.Button(submit_label, type="submit"),
        method="post",
        action=action,
    )


def _recurring_event_row(recurring_event):
    return fast.Li(
        _recurring_event_form(
            action=f"/calendar/recurring/{recurring_event['id']}/edit",
            submit_label="Save",
            recurring_event=recurring_event,
        ),
        fast.Form(
            fast.Button("Delete", type="submit"),
            method="post",
            action=f"/calendar/recurring/{recurring_event['id']}/delete",
        ),
        cls="recurring-event-row",
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
    weeks = month_grid(year, month)
    grid_start, grid_end = weeks[0][0], weeks[-1][-1]
    events = db.list_events_in_range(grid_start.isoformat(), grid_end.isoformat(), owner_id=member_id or None)
    events_map = events_by_date(events, grid_start, grid_end)
    recurring_by_date = _recurring_events_by_date(db.list_recurring_events(), weeks)
    return layout(
        "Calendar",
        fast.H1("Family Calendar"),
        _month_nav(year, month, member_id),
        _filter_row(year, month, member_id),
        fast.A("Manage yearly events", href="/calendar/recurring", cls="manage-recurring-link"),
        _calendar_grid(weeks, month, events_map, recurring_by_date, today, year, member_id),
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
    edit_forms = []
    for event in events:
        member = get_member(event["owner_id"])
        owner_name = member["name"] if member else event["owner_id"]
        actions = []
        if event["owner_id"] == session_member_id:
            edit_form_id = f"edit-event-form-{event['id']}"
            actions.append(fast.Button("Edit", type="submit", onclick=_show_form_js(edit_form_id)))
            actions.append(_delete_event_form(event["id"], year, month, member_id))
            edit_forms.append(
                _event_form(
                    form_id=edit_form_id,
                    action=f"/calendar/{event['id']}/edit",
                    submit_label="Save Changes",
                    event=event,
                    year=year,
                    month=month,
                    member_id=member_id,
                )
            )
        rows.append(fast.Li(f"{event['title']} — {owner_name}", *actions))
    return (
        fast.H3(day.isoformat()),
        fast.Ul(*rows) if rows else fast.P("No events yet."),
        *edit_forms,
        fast.Div(
            fast.Button("Add Event", type="button", onclick=_show_form_js("add-event-form")),
            _event_form(
                form_id="add-event-form",
                action="/calendar",
                submit_label="Add Event",
                default_date=event_date,
                year=year,
                month=month,
                member_id=member_id,
                hidden=bool(events),
            ),
        ),
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
    validated = _validate_event_dates(title, start_date, end_date)
    if isinstance(validated, fast.Response):
        return validated
    title, start_date, end_date, start_date_parsed = validated
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


@router("/calendar/{event_id}/edit", methods=["post"])
def edit_event_route(
    sess,
    event_id: int,
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
    event = db.get_event(event_id)
    if event is None:
        return fast.Redirect("/calendar")
    if event["owner_id"] != member_id:
        return fast.Response("You can only edit your own events.", status_code=403)
    validated = _validate_event_dates(title, start_date, end_date)
    if isinstance(validated, fast.Response):
        return validated
    title, start_date, end_date, start_date_parsed = validated
    db.update_event(
        event_id,
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


@router("/calendar/recurring", methods=["get"])
def recurring_events_page(sess):
    recurring_events = db.list_recurring_events()
    return layout(
        "Yearly Events",
        fast.H1("Yearly Events"),
        fast.P("These repeat every year and are visible to everyone, regardless of the family member filter."),
        fast.Ul(*[_recurring_event_row(r) for r in recurring_events])
        if recurring_events
        else fast.P("No yearly events yet."),
        _recurring_event_form(action="/calendar/recurring", submit_label="Add Yearly Event"),
        fast.A("Back to calendar", href="/calendar"),
    )


@router("/calendar/recurring", methods=["post"])
def add_recurring_event_route(sess, title: str, month: str, day: str):
    validated = _validate_recurring_event(title, month, day)
    if isinstance(validated, fast.Response):
        return validated
    title, month, day = validated
    db.add_recurring_event(title, month, day)
    return fast.Redirect("/calendar/recurring")


@router("/calendar/recurring/{event_id}/edit", methods=["post"])
def edit_recurring_event_route(sess, event_id: int, title: str, month: str, day: str):
    validated = _validate_recurring_event(title, month, day)
    if isinstance(validated, fast.Response):
        return validated
    title, month, day = validated
    db.update_recurring_event(event_id, title, month, day)
    return fast.Redirect("/calendar/recurring")


@router("/calendar/recurring/{event_id}/delete", methods=["post"])
def delete_recurring_event_route(sess, event_id: int):
    db.delete_recurring_event(event_id)
    return fast.Redirect("/calendar/recurring")
