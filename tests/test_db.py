import pytest
from dotenv import dotenv_values
from sqlalchemy import text

import db


def test_app_and_test_env_files_configure_different_db_paths():
    app_db_path = dotenv_values(".env").get("DB_PATH")
    test_db_path = dotenv_values(".env.test").get("DB_PATH")
    assert app_db_path != test_db_path


def test_db_module_loaded_the_test_env_files_configured_path():
    test_db_path = dotenv_values(".env.test").get("DB_PATH")
    assert db.DB_PATH == test_db_path


@pytest.fixture
def probe_table():
    "A scratch table for exercising the SCHEMA_STATEMENTS ADD COLUMN entry format without touching real schema."
    with db.engine.begin() as db_connection:
        db_connection.execute(text("CREATE TABLE _schema_evolution_probe (id INTEGER PRIMARY KEY)"))
    yield "_schema_evolution_probe"
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DROP TABLE _schema_evolution_probe"))


def _probe_table_columns(probe_table):
    with db.engine.connect() as db_connection:
        return [row[1] for row in db_connection.execute(text(f"PRAGMA table_info({probe_table})")).all()]


def test_init_db_adds_a_new_column_declared_as_a_schema_statements_tuple(monkeypatch, probe_table):
    "Locks in the schema-evolution pattern later phases use to grow seed_varieties/plantings without a migration framework -- SQLite has no ADD COLUMN IF NOT EXISTS clause, so init_db() guards it itself via PRAGMA table_info."
    monkeypatch.setattr(
        db._instance, "SCHEMA_STATEMENTS", db._instance.SCHEMA_STATEMENTS + [(probe_table, "probe_col", "TEXT")]
    )
    db.init_db()
    assert "probe_col" in _probe_table_columns(probe_table)


def test_init_db_is_idempotent_when_the_added_column_already_exists(monkeypatch, probe_table):
    "init_db() re-runs via the startup hook on every app boot, so a previously-applied ADD COLUMN entry must not raise the second time."
    monkeypatch.setattr(
        db._instance, "SCHEMA_STATEMENTS", db._instance.SCHEMA_STATEMENTS + [(probe_table, "probe_col", "TEXT")]
    )
    db.init_db()
    db.init_db()
    assert _probe_table_columns(probe_table).count("probe_col") == 1


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


def test_list_events_in_range_excludes_event_fully_before_range():
    db.add_event("member1", "Before", "2026-09-01", "2026-09-02", None, None, None, False)
    events = db.list_events_in_range("2026-09-10", "2026-09-20")
    assert events == []


def test_list_events_in_range_excludes_event_fully_after_range():
    db.add_event("member1", "After", "2026-09-25", "2026-09-26", None, None, None, False)
    events = db.list_events_in_range("2026-09-10", "2026-09-20")
    assert events == []


def test_list_events_in_range_includes_event_spanning_entire_range():
    db.add_event("member1", "Spanning", "2026-09-01", "2026-09-30", None, None, None, False)
    events = db.list_events_in_range("2026-09-10", "2026-09-20")
    assert [e["title"] for e in events] == ["Spanning"]


def test_list_events_in_range_includes_event_touching_start_boundary():
    db.add_event("member1", "TouchesStart", "2026-09-05", "2026-09-10", None, None, None, False)
    events = db.list_events_in_range("2026-09-10", "2026-09-20")
    assert [e["title"] for e in events] == ["TouchesStart"]


def test_list_events_in_range_includes_event_touching_end_boundary():
    db.add_event("member1", "TouchesEnd", "2026-09-20", "2026-09-25", None, None, None, False)
    events = db.list_events_in_range("2026-09-10", "2026-09-20")
    assert [e["title"] for e in events] == ["TouchesEnd"]


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


def test_update_event_changes_title():
    db.add_event("member1", "Original", "2026-09-01", None, None, None, None, False)
    event_id = db.list_events()[0]["id"]
    db.update_event(event_id, "Updated", "2026-09-01", None, None, None, None, False)
    assert db.get_event(event_id)["title"] == "Updated"


def test_update_event_defaults_end_date_to_start_date_when_omitted():
    db.add_event("member1", "Trip", "2026-09-01", "2026-09-05", None, None, None, False)
    event_id = db.list_events()[0]["id"]
    db.update_event(event_id, "Trip", "2026-09-02", None, None, None, None, False)
    assert db.get_event(event_id)["end_date"] == "2026-09-02"


def test_list_recurring_events_returns_empty_list_when_none_exist():
    assert db.list_recurring_events() == []


def test_add_recurring_event_persists_title_month_day():
    db.add_recurring_event("Birthday", 9, 15)
    events = db.list_recurring_events()
    assert [(e["title"], e["month"], e["day"]) for e in events] == [("Birthday", 9, 15)]


def test_recurring_events_ordered_by_month_then_day():
    db.add_recurring_event("December", 12, 1)
    db.add_recurring_event("January", 1, 1)
    events = db.list_recurring_events()
    assert [e["title"] for e in events] == ["January", "December"]


def test_get_recurring_event_returns_matching_row():
    db.add_recurring_event("Lookup", 6, 10)
    event_id = db.list_recurring_events()[0]["id"]
    event = db.get_recurring_event(event_id)
    assert event["title"] == "Lookup"


def test_get_recurring_event_returns_none_when_not_found():
    assert db.get_recurring_event(999999) is None


def test_update_recurring_event_changes_title():
    db.add_recurring_event("Original", 6, 10)
    event_id = db.list_recurring_events()[0]["id"]
    db.update_recurring_event(event_id, "Updated", 6, 10)
    assert db.get_recurring_event(event_id)["title"] == "Updated"


def test_delete_recurring_event_removes_it():
    db.add_recurring_event("To delete", 6, 10)
    event_id = db.list_recurring_events()[0]["id"]
    db.delete_recurring_event(event_id)
    assert db.list_recurring_events() == []


def test_delete_nonexistent_recurring_event_is_a_noop():
    db.delete_recurring_event(999999)
    assert db.list_recurring_events() == []
