from dotenv import dotenv_values

import db


def test_app_and_test_env_files_configure_different_db_paths():
    app_db_path = dotenv_values(".env").get("DB_PATH")
    test_db_path = dotenv_values(".env.test").get("DB_PATH")
    assert app_db_path != test_db_path


def test_db_module_loaded_the_test_env_files_configured_path():
    test_db_path = dotenv_values(".env.test").get("DB_PATH")
    assert db.DB_PATH == test_db_path


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


def test_list_events_returns_empty_list_when_no_events_exist():
    assert db.list_events() == []


def test_add_event_persists_title_and_owner():
    db.add_event("member1", "Dentist", "2026-09-01", "2026-09-01", None, None, None, False)
    events = db.list_events()
    assert [(e["title"], e["owner_id"]) for e in events] == [("Dentist", "member1")]


def test_add_event_defaults_end_date_to_start_date_when_omitted():
    db.add_event("member1", "Trip", "2026-09-01", None, None, None, None, False)
    event = db.list_events()[0]
    assert event["end_date"] == "2026-09-01"


def test_add_event_keeps_explicit_multi_day_end_date():
    db.add_event("member1", "Vacation", "2026-09-01", "2026-09-05", None, None, None, False)
    event = db.list_events()[0]
    assert event["end_date"] == "2026-09-05"


def test_events_ordered_by_start_date():
    db.add_event("member1", "Later", "2026-09-10", None, None, None, None, False)
    db.add_event("member1", "Earlier", "2026-09-02", None, None, None, None, False)
    events = db.list_events()
    assert [e["title"] for e in events] == ["Earlier", "Later"]


def test_list_events_for_owner_excludes_other_members_events():
    db.add_event("member1", "Mine", "2026-09-01", None, None, None, None, False)
    db.add_event("member2", "Theirs", "2026-09-01", None, None, None, None, False)
    events = db.list_events_for_owner("member1")
    assert [e["title"] for e in events] == ["Mine"]


def test_add_event_persists_is_critical_flag():
    db.add_event("member1", "Important", "2026-09-01", None, None, None, None, True)
    event = db.list_events()[0]
    assert event["is_critical"] == 1


def test_delete_event_removes_it():
    db.add_event("member1", "To delete", "2026-09-01", None, None, None, None, False)
    event_id = db.list_events()[0]["id"]
    db.delete_event(event_id)
    assert db.list_events() == []


def test_delete_nonexistent_event_is_a_noop():
    db.delete_event(999999)
    assert db.list_events() == []


def test_get_event_returns_matching_row():
    db.add_event("member1", "Lookup", "2026-09-01", None, None, None, None, False)
    event_id = db.list_events()[0]["id"]
    event = db.get_event(event_id)
    assert event["title"] == "Lookup"


def test_get_event_returns_none_when_not_found():
    assert db.get_event(999999) is None
