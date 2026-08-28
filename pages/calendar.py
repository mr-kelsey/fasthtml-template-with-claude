from fasthtml import common as fast

from layout import layout
from family import FAMILY_MEMBERS, get_member
import db

router = fast.APIRouter()


def _date_range(event):
    if event["start_date"] == event["end_date"]:
        return event["start_date"]
    return f"{event['start_date']} - {event['end_date']}"


def _time_range(event):
    if not event["start_time"]:
        return ""
    if event["end_time"]:
        return f"{event['start_time']} - {event['end_time']}"
    return event["start_time"]


def _event_row(event, current_member_id):
    member = get_member(event["owner_id"])
    owner_name = member["name"] if member else event["owner_id"]
    owner_color = member["color"] if member else "#999999"
    delete_cell = ""
    if current_member_id == event["owner_id"]:
        delete_cell = fast.Form(
            fast.Button("Delete", type="submit"),
            method="post",
            action=f"/calendar/{event['id']}/delete",
        )
    return fast.Tr(
        fast.Td(
            event["title"],
            fast.Span("⚠ Can't miss", cls="event-critical") if event["is_critical"] else "",
            style=f"border-left: 4px solid {owner_color}; padding-left: 0.5rem;",
        ),
        fast.Td(owner_name),
        fast.Td(_date_range(event)),
        fast.Td(_time_range(event)),
        fast.Td(event["notes"] or ""),
        fast.Td(delete_cell),
    )


def _events_table(events, current_member_id):
    rows = (
        [_event_row(event, current_member_id) for event in events]
        if events
        else [fast.Tr(fast.Td("No events yet.", colspan="6"))]
    )
    return fast.Table(
        fast.Thead(
            fast.Tr(
                fast.Th("Title"),
                fast.Th("Who"),
                fast.Th("Date"),
                fast.Th("Time"),
                fast.Th("Notes"),
                fast.Th(""),
            )
        ),
        fast.Tbody(*rows),
    )


def _add_event_form():
    return fast.Form(
        fast.Input(name="title", placeholder="Title", required=True),
        fast.Input(name="start_date", type="date", required=True),
        fast.Input(name="end_date", type="date"),
        fast.Input(name="start_time", type="time"),
        fast.Input(name="end_time", type="time"),
        fast.Textarea(name="notes", placeholder="Notes (optional)"),
        fast.Label(fast.Input(name="is_critical", type="checkbox", value="1"), " Can't miss"),
        fast.Button("Add Event", type="submit"),
        method="post",
        action="/calendar",
    )


def _identity_banner(current_member_id):
    member = get_member(current_member_id)
    label = f"Viewing as {member['name']}" if member else "No user selected"
    return fast.P(
        f"{label} — ",
        fast.A("My Calendar", href="/calendar/me"),
        " · ",
        fast.A("Everyone's Calendar", href="/calendar"),
        " · ",
        fast.A("Switch User", href="/calendar/switch-user"),
    )


@router("/calendar/switch-user", methods=["get"])
def switch_user_page():
    pickers = [
        fast.Form(
            fast.Input(type="hidden", name="member_id", value=member["id"]),
            fast.Button(member["name"], type="submit", style=f"background-color: {member['color']}; border-color: {member['color']};"),
            method="post",
            action="/calendar/switch-user",
        )
        for member in FAMILY_MEMBERS
    ]
    return layout("Switch User", fast.H1("Who's using the calendar?"), *pickers)


@router("/calendar/switch-user", methods=["post"])
def switch_user_route(sess, member_id: str):
    if get_member(member_id) is None:
        return fast.Response("Unknown family member.", status_code=422)
    sess["member_id"] = member_id
    return fast.Redirect("/calendar")


@router("/calendar", methods=["get"])
def calendar_page(sess):
    member_id = sess.get("member_id")
    if member_id is None:
        return fast.Redirect("/calendar/switch-user")
    events = db.list_events()
    return layout(
        "Calendar",
        fast.H1("Family Calendar"),
        _identity_banner(member_id),
        fast.H2("Add an event"),
        _add_event_form(),
        fast.H2("Everyone's schedule"),
        _events_table(events, member_id),
    )


@router("/calendar/me", methods=["get"])
def my_calendar_page(sess):
    member_id = sess.get("member_id")
    if member_id is None:
        return fast.Redirect("/calendar/switch-user")
    events = db.list_events_for_owner(member_id)
    member = get_member(member_id)
    return layout(
        "My Calendar",
        fast.H1(f"{member['name']}'s Calendar"),
        _identity_banner(member_id),
        fast.H2("Add an event"),
        _add_event_form(),
        fast.H2("My schedule"),
        _events_table(events, member_id),
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
):
    member_id = sess.get("member_id")
    if member_id is None:
        return fast.Redirect("/calendar/switch-user")
    title = title.strip()
    start_date = start_date.strip()
    end_date = end_date.strip()
    if not title or not start_date:
        return fast.Response("Title and start date are required.", status_code=422)
    if end_date and end_date < start_date:
        return fast.Response("End date cannot be before start date.", status_code=422)
    db.add_event(
        owner_id=member_id,
        title=title,
        start_date=start_date,
        end_date=end_date or None,
        start_time=start_time.strip() or None,
        end_time=end_time.strip() or None,
        notes=notes.strip() or None,
        is_critical=bool(is_critical),
    )
    return fast.Redirect("/calendar")


@router("/calendar/{event_id}/delete", methods=["post"])
def delete_event_route(sess, event_id: int):
    member_id = sess.get("member_id")
    event = db.get_event(event_id)
    if event is None:
        return fast.Redirect("/calendar")
    if event["owner_id"] != member_id:
        return fast.Response("You can only delete your own events.", status_code=403)
    db.delete_event(event_id)
    return fast.Redirect("/calendar")
