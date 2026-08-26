import db


def test_list_notes_returns_empty_list_when_no_notes_exist():
    assert db.list_notes() == []


def test_add_note_persists_title_and_body():
    db.add_note("Title A", "Body A")
    notes = db.list_notes()
    assert [(note["title"], note["body"]) for note in notes] == [("Title A", "Body A")]


def test_notes_ordered_most_recent_first():
    db.add_note("First", "1")
    db.add_note("Second", "2")
    notes = db.list_notes()
    assert [note["title"] for note in notes] == ["Second", "First"]


def test_delete_note_removes_it():
    db.add_note("To delete", "bye")
    note_id = db.list_notes()[0]["id"]
    db.delete_note(note_id)
    assert db.list_notes() == []


def test_delete_nonexistent_note_is_a_noop():
    db.delete_note(999999)
    assert db.list_notes() == []
