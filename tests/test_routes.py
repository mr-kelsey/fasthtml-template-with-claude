from datetime import date

import db
from family import FAMILY_MEMBERS

CAL_YEAR = 2026
CAL_MONTH = 9


def _calendar_url(year=CAL_YEAR, month=CAL_MONTH, member_id=None):
    url = f"/calendar?year={year}&month={month}"
    if member_id:
        url += f"&member_id={member_id}"
    return url


def _pick_member(client, member_id, year=CAL_YEAR, month=CAL_MONTH):
    return client.get(_calendar_url(year=year, month=month, member_id=member_id))


def test_home_page_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200


def test_home_page_shows_welcome_heading(client):
    response = client.get("/")
    assert "Welcome" in response.text


def test_about_page_returns_200(client):
    response = client.get("/about")
    assert response.status_code == 200


def test_about_page_shows_about_heading(client):
    response = client.get("/about")
    assert "About" in response.text


def test_notes_page_returns_200(client):
    response = client.get("/notes")
    assert response.status_code == 200


def test_notes_page_shows_empty_state_when_no_notes_exist(client):
    response = client.get("/notes")
    assert "No notes yet" in response.text


def test_add_note_redirects_with_303(client):
    response = client.post("/notes", data={"title": "T1", "body": "B1"}, follow_redirects=False)
    assert response.status_code == 303


def test_add_note_redirect_location_is_notes_page(client):
    response = client.post("/notes", data={"title": "T1", "body": "B1"}, follow_redirects=False)
    assert response.headers["location"] == "/notes"


def test_add_note_appears_in_notes_list(client):
    client.post("/notes", data={"title": "T1", "body": "B1"})
    response = client.get("/notes")
    assert "T1" in response.text and "B1" in response.text


def test_delete_note_redirects_with_303(client):
    client.post("/notes", data={"title": "ToDelete", "body": "x"})
    note_id = db.list_notes()[0]["id"]
    response = client.post(f"/notes/{note_id}/delete", follow_redirects=False)
    assert response.status_code == 303


def test_delete_note_removes_it_from_notes_list(client):
    client.post("/notes", data={"title": "ToDelete", "body": "x"})
    note_id = db.list_notes()[0]["id"]
    client.post(f"/notes/{note_id}/delete")
    response = client.get("/notes")
    assert "ToDelete" not in response.text


def test_add_note_rejects_blank_title(client):
    response = client.post("/notes", data={"title": "", "body": "Body"})
    assert response.status_code == 422


def test_add_note_rejects_blank_body(client):
    response = client.post("/notes", data={"title": "Title", "body": ""})
    assert response.status_code == 422


def test_add_note_rejects_whitespace_only_title(client):
    response = client.post("/notes", data={"title": "   ", "body": "Body"})
    assert response.status_code == 422


def test_add_note_does_not_persist_on_validation_failure(client):
    client.post("/notes", data={"title": "", "body": "Body"})
    assert db.list_notes() == []


def test_calendar_page_returns_200_without_identity(client):
    response = client.get("/calendar", follow_redirects=False)
    assert response.status_code == 200


def test_picking_member_via_filter_allows_adding_event(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    response = client.post(
        "/calendar", data={"title": "Soccer", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01"}, follow_redirects=False
    )
    assert response.status_code == 303


def test_add_event_rejects_when_no_member_picked(client):
    response = client.post("/calendar", data={"title": "Soccer", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01"})
    assert response.status_code == 422


def test_everyone_filter_does_not_clear_identity(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.get(_calendar_url())
    response = client.post(
        "/calendar", data={"title": "Soccer", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01"}, follow_redirects=False
    )
    assert response.status_code == 303


def test_calendar_page_shows_weekday_headers(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    response = client.get(_calendar_url())
    assert "Sun" in response.text


def test_add_event_appears_on_calendar_grid(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.post("/calendar", data={"title": "Soccer Practice", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01"})
    response = client.get(_calendar_url())
    assert "Soccer Practice" in response.text


def test_calendar_grid_shows_event_color_bar_for_owner(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.post("/calendar", data={"title": "Soccer Practice", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01"})
    response = client.get(_calendar_url())
    assert f'background-color: {FAMILY_MEMBERS[0]["color"]}' in response.text


def test_calendar_grid_stacks_multiple_events_on_same_day(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.post("/calendar", data={"title": "First", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01"})
    client.post("/calendar", data={"title": "Second", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01"})
    response = client.get(_calendar_url())
    assert response.text.count('class="event-bar"') == 2


def test_multi_day_event_shows_bar_on_each_spanned_day(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.post(
        "/calendar",
        data={
            "title": "Trip",
            "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01",
            "end_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-03",
        },
    )
    response = client.get(_calendar_url())
    assert response.text.count('class="event-bar"') == 3


def test_critical_event_adds_critical_day_class(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.post(
        "/calendar",
        data={"title": "Big Day", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01", "is_critical": "1"},
    )
    response = client.get(_calendar_url())
    assert "critical-day" in response.text


def test_non_critical_event_does_not_add_critical_day_class(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.post("/calendar", data={"title": "Normal Day", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01"})
    response = client.get(_calendar_url())
    assert "critical-day" not in response.text


def test_member_filter_shows_selected_members_event(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.post("/calendar", data={"title": "Mine", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01"})
    response = client.get(_calendar_url(member_id=FAMILY_MEMBERS[0]["id"]))
    assert "Mine" in response.text


def test_member_filter_hides_other_members_event(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.post("/calendar", data={"title": "Mine", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01"})
    _pick_member(client, FAMILY_MEMBERS[1]["id"])
    client.post("/calendar", data={"title": "Theirs", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01"})
    response = client.get(_calendar_url(member_id=FAMILY_MEMBERS[1]["id"]))
    assert "Mine" not in response.text


def test_month_navigation_shows_events_in_selected_month(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.post("/calendar", data={"title": "October Trip", "start_date": f"{CAL_YEAR}-10-15"})
    response = client.get(_calendar_url(month=10))
    assert "October Trip" in response.text


def test_month_navigation_hides_events_outside_selected_month(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.post("/calendar", data={"title": "October Trip", "start_date": f"{CAL_YEAR}-10-15"})
    response = client.get(_calendar_url(month=CAL_MONTH))
    assert "October Trip" not in response.text


def test_day_fragment_route_returns_prefilled_add_form(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    response = client.get(f"/calendar/day/{CAL_YEAR}-{CAL_MONTH:02d}-05")
    assert f'value="{CAL_YEAR}-{CAL_MONTH:02d}-05"' in response.text


def test_day_fragment_route_lists_existing_events_for_that_day(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.post("/calendar", data={"title": "Dentist", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-05"})
    response = client.get(f"/calendar/day/{CAL_YEAR}-{CAL_MONTH:02d}-05")
    assert "Dentist" in response.text


def test_day_fragment_member_filter_hides_other_members_event(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.post("/calendar", data={"title": "Mine", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-05"})
    _pick_member(client, FAMILY_MEMBERS[1]["id"])
    client.post("/calendar", data={"title": "Theirs", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-05"})
    response = client.get(
        f"/calendar/day/{CAL_YEAR}-{CAL_MONTH:02d}-05?member_id={FAMILY_MEMBERS[1]['id']}"
    )
    assert "Mine" not in response.text


def test_add_event_rejects_blank_title(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    response = client.post("/calendar", data={"title": "", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01"})
    assert response.status_code == 422


def test_add_event_rejects_end_date_before_start_date(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    response = client.post(
        "/calendar",
        data={"title": "Bad Range", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-05", "end_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01"},
    )
    assert response.status_code == 422


def test_add_event_rejects_malformed_start_date(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    response = client.post("/calendar", data={"title": "Bad Date", "start_date": "not-a-date"})
    assert response.status_code == 422


def test_add_event_rejects_malformed_end_date(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    response = client.post(
        "/calendar",
        data={"title": "Bad End Date", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01", "end_date": "not-a-date"},
    )
    assert response.status_code == 422


def test_day_fragment_rejects_malformed_date(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    response = client.get("/calendar/day/not-a-date")
    assert response.status_code == 422


def test_add_event_falls_back_to_start_date_year_when_redirect_year_is_garbage(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    response = client.post(
        "/calendar",
        data={
            "title": "Trip",
            "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01",
            "redirect_year": "garbage",
            "redirect_month": "garbage",
        },
        follow_redirects=False,
    )
    assert response.headers["location"] == f"/calendar?year={CAL_YEAR}&month={CAL_MONTH}"


def test_delete_event_falls_back_to_today_when_redirect_year_is_garbage(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.post("/calendar", data={"title": "Owned", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01"})
    event_id = db.list_events()[0]["id"]
    today = date.today()
    response = client.post(
        f"/calendar/{event_id}/delete",
        data={"redirect_year": "garbage", "redirect_month": "garbage"},
        follow_redirects=False,
    )
    assert response.headers["location"] == f"/calendar?year={today.year}&month={today.month}"


def test_add_event_redirects_to_requested_month_and_member_filter(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    response = client.post(
        "/calendar",
        data={
            "title": "Trip",
            "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01",
            "redirect_year": "2026",
            "redirect_month": "10",
            "redirect_member_id": FAMILY_MEMBERS[0]["id"],
        },
        follow_redirects=False,
    )
    assert response.headers["location"] == f"/calendar?year=2026&month=10&member_id={FAMILY_MEMBERS[0]['id']}"


def test_delete_event_by_non_owner_is_forbidden(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.post("/calendar", data={"title": "Owned", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01"})
    event_id = db.list_events()[0]["id"]
    _pick_member(client, FAMILY_MEMBERS[1]["id"])
    response = client.post(f"/calendar/{event_id}/delete")
    assert response.status_code == 403


def test_delete_event_by_owner_removes_it(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.post("/calendar", data={"title": "Owned", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01"})
    event_id = db.list_events()[0]["id"]
    client.post(f"/calendar/{event_id}/delete")
    assert db.list_events() == []


def test_day_fragment_add_form_is_hidden_when_day_has_events(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.post("/calendar", data={"title": "Dentist", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-05"})
    response = client.get(f"/calendar/day/{CAL_YEAR}-{CAL_MONTH:02d}-05")
    assert '<form enctype="multipart/form-data" method="post" action="/calendar" hidden' in response.text


def test_day_fragment_add_form_is_visible_when_day_has_no_events(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    response = client.get(f"/calendar/day/{CAL_YEAR}-{CAL_MONTH:02d}-05")
    assert '<form enctype="multipart/form-data" method="post" action="/calendar" id="add-event-form"' in response.text


def test_day_fragment_shows_add_event_button(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    response = client.get(f"/calendar/day/{CAL_YEAR}-{CAL_MONTH:02d}-05")
    assert ">Add Event<" in response.text


def test_day_fragment_shows_edit_button_for_owned_event(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.post("/calendar", data={"title": "Dentist", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-05"})
    response = client.get(f"/calendar/day/{CAL_YEAR}-{CAL_MONTH:02d}-05")
    assert ">Edit<" in response.text


def test_day_fragment_hides_edit_button_for_others_event(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.post("/calendar", data={"title": "Theirs", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-05"})
    _pick_member(client, FAMILY_MEMBERS[1]["id"])
    response = client.get(f"/calendar/day/{CAL_YEAR}-{CAL_MONTH:02d}-05")
    assert ">Edit<" not in response.text


def test_edit_event_by_owner_updates_title(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.post("/calendar", data={"title": "Original", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01"})
    event_id = db.list_events()[0]["id"]
    client.post(
        f"/calendar/{event_id}/edit",
        data={"title": "Updated", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01"},
    )
    assert db.get_event(event_id)["title"] == "Updated"


def test_edit_event_by_non_owner_is_forbidden(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.post("/calendar", data={"title": "Owned", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01"})
    event_id = db.list_events()[0]["id"]
    _pick_member(client, FAMILY_MEMBERS[1]["id"])
    response = client.post(
        f"/calendar/{event_id}/edit",
        data={"title": "Hijacked", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01"},
    )
    assert response.status_code == 403


def test_edit_event_rejects_blank_title(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.post("/calendar", data={"title": "Owned", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01"})
    event_id = db.list_events()[0]["id"]
    response = client.post(
        f"/calendar/{event_id}/edit",
        data={"title": "", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01"},
    )
    assert response.status_code == 422


def test_edit_event_rejects_end_date_before_start_date(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.post("/calendar", data={"title": "Owned", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-05"})
    event_id = db.list_events()[0]["id"]
    response = client.post(
        f"/calendar/{event_id}/edit",
        data={
            "title": "Owned",
            "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-05",
            "end_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01",
        },
    )
    assert response.status_code == 422


def test_calendar_recurring_page_returns_200(client):
    response = client.get("/calendar/recurring")
    assert response.status_code == 200


def test_add_recurring_event_redirects_with_303(client):
    response = client.post(
        "/calendar/recurring", data={"title": "Mom's Birthday", "month": "9", "day": "15"}, follow_redirects=False
    )
    assert response.status_code == 303


def test_add_recurring_event_appears_on_recurring_page(client):
    client.post("/calendar/recurring", data={"title": "Mom's Birthday", "month": "9", "day": "15"})
    response = client.get("/calendar/recurring")
    assert "Mom's Birthday" in response.text


def test_add_recurring_event_rejects_blank_title(client):
    response = client.post("/calendar/recurring", data={"title": "", "month": "9", "day": "15"})
    assert response.status_code == 422


def test_add_recurring_event_rejects_invalid_day_for_month(client):
    response = client.post("/calendar/recurring", data={"title": "Bad Date", "month": "4", "day": "31"})
    assert response.status_code == 422


def test_add_recurring_event_rejects_malformed_day(client):
    response = client.post("/calendar/recurring", data={"title": "Bad Date", "month": "9", "day": "not-a-number"})
    assert response.status_code == 422


def test_recurring_event_appears_on_calendar_grid(client):
    client.post("/calendar/recurring", data={"title": "Mom's Birthday", "month": str(CAL_MONTH), "day": "15"})
    response = client.get(_calendar_url())
    assert "Mom's Birthday" in response.text


def test_recurring_event_recurs_into_following_year(client):
    client.post("/calendar/recurring", data={"title": "Mom's Birthday", "month": str(CAL_MONTH), "day": "15"})
    response = client.get(_calendar_url(year=CAL_YEAR + 1))
    assert "Mom's Birthday" in response.text


def test_recurring_event_ignores_member_filter(client):
    client.post("/calendar/recurring", data={"title": "Mom's Birthday", "month": str(CAL_MONTH), "day": "15"})
    response = client.get(_calendar_url(member_id=FAMILY_MEMBERS[0]["id"]))
    assert "Mom's Birthday" in response.text


def test_recurring_event_does_not_appear_in_day_fragment(client):
    client.post("/calendar/recurring", data={"title": "Mom's Birthday", "month": str(CAL_MONTH), "day": "15"})
    response = client.get(f"/calendar/day/{CAL_YEAR}-{CAL_MONTH:02d}-15")
    assert "Mom's Birthday" not in response.text


def test_edit_recurring_event_updates_title(client):
    client.post("/calendar/recurring", data={"title": "Original", "month": "9", "day": "15"})
    event_id = db.list_recurring_events()[0]["id"]
    client.post(f"/calendar/recurring/{event_id}/edit", data={"title": "Updated", "month": "9", "day": "15"})
    response = client.get("/calendar/recurring")
    assert "Updated" in response.text


def test_delete_recurring_event_removes_it_from_grid(client):
    client.post("/calendar/recurring", data={"title": "Mom's Birthday", "month": str(CAL_MONTH), "day": "15"})
    event_id = db.list_recurring_events()[0]["id"]
    client.post(f"/calendar/recurring/{event_id}/delete")
    response = client.get(_calendar_url())
    assert "Mom's Birthday" not in response.text


def test_recurring_event_on_feb_29_does_not_appear_in_non_leap_year(client):
    client.post("/calendar/recurring", data={"title": "Leap Day", "month": "2", "day": "29"})
    response = client.get(_calendar_url(year=2026, month=2))
    assert "Leap Day" not in response.text


def test_recurring_event_on_feb_29_appears_in_leap_year(client):
    client.post("/calendar/recurring", data={"title": "Leap Day", "month": "2", "day": "29"})
    response = client.get(_calendar_url(year=2028, month=2))
    assert "Leap Day" in response.text


def test_edit_event_redirects_to_requested_month_and_member_filter(client):
    _pick_member(client, FAMILY_MEMBERS[0]["id"])
    client.post("/calendar", data={"title": "Owned", "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01"})
    event_id = db.list_events()[0]["id"]
    response = client.post(
        f"/calendar/{event_id}/edit",
        data={
            "title": "Owned",
            "start_date": f"{CAL_YEAR}-{CAL_MONTH:02d}-01",
            "redirect_year": "2026",
            "redirect_month": "10",
            "redirect_member_id": FAMILY_MEMBERS[0]["id"],
        },
        follow_redirects=False,
    )
    assert response.headers["location"] == f"/calendar?year=2026&month=10&member_id={FAMILY_MEMBERS[0]['id']}"
