import db


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
