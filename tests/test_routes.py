import db
from family import FAMILY_MEMBERS


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


def test_calendar_page_redirects_to_switch_user_when_no_identity(client):
    response = client.get("/calendar", follow_redirects=False)
    assert response.status_code == 303


def test_switch_user_page_returns_200(client):
    response = client.get("/calendar/switch-user")
    assert response.status_code == 200


def test_switch_user_sets_session_and_redirects(client):
    response = client.post(
        "/calendar/switch-user", data={"member_id": FAMILY_MEMBERS[0]["id"]}, follow_redirects=False
    )
    assert response.headers["location"] == "/calendar"


def test_calendar_page_returns_200_after_switching_user(client):
    client.post("/calendar/switch-user", data={"member_id": FAMILY_MEMBERS[0]["id"]})
    response = client.get("/calendar")
    assert response.status_code == 200


def test_add_event_appears_on_calendar_page(client):
    client.post("/calendar/switch-user", data={"member_id": FAMILY_MEMBERS[0]["id"]})
    client.post("/calendar", data={"title": "Soccer Practice", "start_date": "2026-09-01"})
    response = client.get("/calendar")
    assert "Soccer Practice" in response.text


def test_calendar_me_page_only_shows_own_events(client):
    client.post("/calendar/switch-user", data={"member_id": FAMILY_MEMBERS[0]["id"]})
    client.post("/calendar", data={"title": "Mine", "start_date": "2026-09-01"})
    client.post("/calendar/switch-user", data={"member_id": FAMILY_MEMBERS[1]["id"]})
    client.post("/calendar", data={"title": "Theirs", "start_date": "2026-09-01"})
    response = client.get("/calendar/me")
    assert "Theirs" in response.text and "Mine" not in response.text


def test_add_event_rejects_blank_title(client):
    client.post("/calendar/switch-user", data={"member_id": FAMILY_MEMBERS[0]["id"]})
    response = client.post("/calendar", data={"title": "", "start_date": "2026-09-01"})
    assert response.status_code == 422


def test_add_event_rejects_end_date_before_start_date(client):
    client.post("/calendar/switch-user", data={"member_id": FAMILY_MEMBERS[0]["id"]})
    response = client.post(
        "/calendar", data={"title": "Bad Range", "start_date": "2026-09-05", "end_date": "2026-09-01"}
    )
    assert response.status_code == 422


def test_multi_day_event_renders_as_date_range(client):
    client.post("/calendar/switch-user", data={"member_id": FAMILY_MEMBERS[0]["id"]})
    client.post("/calendar", data={"title": "Trip", "start_date": "2026-09-01", "end_date": "2026-09-05"})
    response = client.get("/calendar")
    assert "2026-09-01" in response.text and "2026-09-05" in response.text


def test_critical_event_shows_cant_miss_badge(client):
    client.post("/calendar/switch-user", data={"member_id": FAMILY_MEMBERS[0]["id"]})
    client.post(
        "/calendar", data={"title": "Big Day", "start_date": "2026-09-01", "is_critical": "1"}
    )
    response = client.get("/calendar")
    assert "Can't miss" in response.text


def test_delete_event_by_non_owner_is_forbidden(client):
    client.post("/calendar/switch-user", data={"member_id": FAMILY_MEMBERS[0]["id"]})
    client.post("/calendar", data={"title": "Owned", "start_date": "2026-09-01"})
    event_id = db.list_events()[0]["id"]
    client.post("/calendar/switch-user", data={"member_id": FAMILY_MEMBERS[1]["id"]})
    response = client.post(f"/calendar/{event_id}/delete")
    assert response.status_code == 403


def test_delete_event_by_owner_removes_it(client):
    client.post("/calendar/switch-user", data={"member_id": FAMILY_MEMBERS[0]["id"]})
    client.post("/calendar", data={"title": "Owned", "start_date": "2026-09-01"})
    event_id = db.list_events()[0]["id"]
    client.post(f"/calendar/{event_id}/delete")
    response = client.get("/calendar")
    assert "Owned" not in response.text
