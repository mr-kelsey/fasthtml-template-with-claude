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


def test_list_plants_returns_empty_list_when_no_plants_exist():
    assert db.list_plants() == []


def test_add_plant_persists_name():
    db.add_plant("Tomato")
    assert db.list_plants()[0]["name"] == "Tomato"


def test_add_plant_persists_optional_agronomic_fields():
    db.add_plant("Tomato", species="Solanum lycopersicum", plant_family="Nightshade", days_to_maturity_min=60)
    plant = db.list_plants()[0]
    assert (plant["plant_family"], plant["days_to_maturity_min"]) == ("Nightshade", 60)


def test_add_plant_defaults_optional_fields_to_none():
    db.add_plant("Tomato")
    plant = db.list_plants()[0]
    assert plant["germination_days_min"] is None


def test_plants_ordered_by_name():
    db.add_plant("Zucchini")
    db.add_plant("Basil")
    assert [p["name"] for p in db.list_plants()] == ["Basil", "Zucchini"]


def test_get_plant_returns_matching_row():
    db.add_plant("Tomato")
    plant_id = db.list_plants()[0]["id"]
    assert db.get_plant(plant_id)["name"] == "Tomato"


def test_get_plant_returns_none_when_not_found():
    assert db.get_plant(999999) is None


def test_update_plant_changes_name():
    db.add_plant("Original")
    plant_id = db.list_plants()[0]["id"]
    db.update_plant(plant_id, "Updated")
    assert db.get_plant(plant_id)["name"] == "Updated"


def test_delete_plant_removes_it():
    db.add_plant("To delete")
    plant_id = db.list_plants()[0]["id"]
    db.delete_plant(plant_id)
    assert db.list_plants() == []


def test_delete_nonexistent_plant_is_a_noop():
    db.delete_plant(999999)
    assert db.list_plants() == []


def test_list_seed_varieties_returns_empty_list_when_none_exist():
    assert db.list_seed_varieties() == []


def test_add_seed_variety_persists_name_and_plant():
    db.add_plant("Tomato")
    plant_id = db.list_plants()[0]["id"]
    db.add_seed_variety(plant_id, "Cherokee Purple")
    variety = db.list_seed_varieties()[0]
    assert (variety["name"], variety["plant_name"]) == ("Cherokee Purple", "Tomato")


def test_seed_varieties_ordered_by_name():
    db.add_plant("Tomato")
    plant_id = db.list_plants()[0]["id"]
    db.add_seed_variety(plant_id, "Roma")
    db.add_seed_variety(plant_id, "Cherokee Purple")
    assert [v["name"] for v in db.list_seed_varieties()] == ["Cherokee Purple", "Roma"]


def test_get_seed_variety_returns_matching_row():
    db.add_plant("Tomato")
    plant_id = db.list_plants()[0]["id"]
    db.add_seed_variety(plant_id, "Cherokee Purple")
    variety_id = db.list_seed_varieties()[0]["id"]
    assert db.get_seed_variety(variety_id)["name"] == "Cherokee Purple"


def test_get_seed_variety_returns_none_when_not_found():
    assert db.get_seed_variety(999999) is None


def test_update_seed_variety_changes_name():
    db.add_plant("Tomato")
    plant_id = db.list_plants()[0]["id"]
    db.add_seed_variety(plant_id, "Original")
    variety_id = db.list_seed_varieties()[0]["id"]
    db.update_seed_variety(variety_id, plant_id, "Updated")
    assert db.get_seed_variety(variety_id)["name"] == "Updated"


def test_delete_seed_variety_removes_it():
    db.add_plant("Tomato")
    plant_id = db.list_plants()[0]["id"]
    db.add_seed_variety(plant_id, "To delete")
    variety_id = db.list_seed_varieties()[0]["id"]
    db.delete_seed_variety(variety_id)
    assert db.list_seed_varieties() == []


def test_delete_nonexistent_seed_variety_is_a_noop():
    db.delete_seed_variety(999999)
    assert db.list_seed_varieties() == []


def test_seed_variety_inherits_plant_default_when_no_override():
    db.add_plant("Tomato", days_to_maturity_min=60, days_to_maturity_max=80)
    plant_id = db.list_plants()[0]["id"]
    db.add_seed_variety(plant_id, "Cherokee Purple")
    variety = db.list_seed_varieties()[0]
    assert (variety["days_to_maturity_min"], variety["days_to_maturity_max"]) == (60, 80)


def test_seed_variety_override_wins_over_plant_default():
    db.add_plant("Tomato", days_to_maturity_min=60, days_to_maturity_max=80)
    plant_id = db.list_plants()[0]["id"]
    db.add_seed_variety(plant_id, "Early Girl", days_to_maturity_min=50, days_to_maturity_max=60)
    variety = db.list_seed_varieties()[0]
    assert (variety["days_to_maturity_min"], variety["days_to_maturity_max"]) == (50, 60)


def _add_variety(plant_name="Tomato", variety_name="Cherokee Purple", **plant_kwargs):
    db.add_plant(plant_name, **plant_kwargs)
    plant_id = db.list_plants()[0]["id"]
    db.add_seed_variety(plant_id, variety_name)
    return db.list_seed_varieties()[0]["id"]


def test_list_plantings_returns_empty_list_when_none_exist():
    assert db.list_plantings() == []


def test_add_planting_persists_variety_and_date():
    variety_id = _add_variety()
    db.add_planting(variety_id, "2026-05-01")
    planting = db.list_plantings()[0]
    assert (planting["variety_name"], planting["planted_date"]) == ("Cherokee Purple", "2026-05-01")


def test_add_planting_defaults_bed_id_and_location_to_none():
    variety_id = _add_variety()
    db.add_planting(variety_id, "2026-05-01")
    planting = db.list_plantings()[0]
    assert (planting["bed_id"], planting["location"]) == (None, None)


def test_plantings_ordered_by_planted_date_descending():
    variety_id = _add_variety()
    db.add_planting(variety_id, "2026-05-01")
    db.add_planting(variety_id, "2026-06-01")
    assert [p["planted_date"] for p in db.list_plantings()] == ["2026-06-01", "2026-05-01"]


def test_list_plantings_includes_effective_maturity_from_join():
    variety_id = _add_variety(days_to_maturity_min=60, days_to_maturity_max=80)
    db.add_planting(variety_id, "2026-05-01")
    planting = db.list_plantings()[0]
    assert (planting["days_to_maturity_min"], planting["days_to_maturity_max"]) == (60, 80)


def test_get_planting_returns_matching_row():
    variety_id = _add_variety()
    db.add_planting(variety_id, "2026-05-01", quantity=10)
    planting_id = db.list_plantings()[0]["id"]
    assert db.get_planting(planting_id)["quantity"] == 10


def test_get_planting_returns_none_when_not_found():
    assert db.get_planting(999999) is None


def test_update_planting_changes_quantity():
    variety_id = _add_variety()
    db.add_planting(variety_id, "2026-05-01", quantity=10)
    planting_id = db.list_plantings()[0]["id"]
    db.update_planting(planting_id, variety_id, "2026-05-01", quantity=20)
    assert db.get_planting(planting_id)["quantity"] == 20


def test_delete_planting_removes_it():
    variety_id = _add_variety()
    db.add_planting(variety_id, "2026-05-01")
    planting_id = db.list_plantings()[0]["id"]
    db.delete_planting(planting_id)
    assert db.list_plantings() == []


def test_delete_nonexistent_planting_is_a_noop():
    db.delete_planting(999999)
    assert db.list_plantings() == []
