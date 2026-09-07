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


def test_list_seed_varieties_returns_empty_list_when_none_exist():
    assert db.list_seed_varieties() == []


def test_add_seed_variety_persists_common_name_and_family():
    db.add_seed_variety("Tomato", "Cherokee Purple", "Solanaceae")
    variety = db.list_seed_varieties()[0]
    assert (variety["common_name"], variety["name"], variety["plant_family"]) == ("Tomato", "Cherokee Purple", "Solanaceae")


def test_add_seed_variety_persists_optional_genus_species_and_agronomic_fields():
    db.add_seed_variety(
        "Tomato", "Cherokee Purple", "Solanaceae", genus="Solanum", species="lycopersicum", days_to_maturity_min=60
    )
    variety = db.list_seed_varieties()[0]
    assert (variety["genus"], variety["species"], variety["days_to_maturity_min"]) == ("Solanum", "lycopersicum", 60)


def test_add_seed_variety_defaults_optional_fields_to_none():
    db.add_seed_variety("Tomato", "Cherokee Purple", "Solanaceae")
    variety = db.list_seed_varieties()[0]
    assert (variety["genus"], variety["species"], variety["germination_days_min"]) == (None, None, None)


def test_seed_varieties_ordered_by_common_name_then_name():
    db.add_seed_variety("Zucchini", "Black Beauty", "Cucurbitaceae")
    db.add_seed_variety("Basil", "Genovese", "Lamiaceae")
    assert [v["common_name"] for v in db.list_seed_varieties()] == ["Basil", "Zucchini"]


def test_get_seed_variety_returns_matching_row():
    db.add_seed_variety("Tomato", "Cherokee Purple", "Solanaceae")
    variety_id = db.list_seed_varieties()[0]["id"]
    assert db.get_seed_variety(variety_id)["name"] == "Cherokee Purple"


def test_get_seed_variety_returns_none_when_not_found():
    assert db.get_seed_variety(999999) is None


def test_update_seed_variety_changes_name():
    db.add_seed_variety("Tomato", "Original", "Solanaceae")
    variety_id = db.list_seed_varieties()[0]["id"]
    db.update_seed_variety(variety_id, "Tomato", "Updated", "Solanaceae")
    assert db.get_seed_variety(variety_id)["name"] == "Updated"


def test_delete_seed_variety_removes_it():
    db.add_seed_variety("Tomato", "To delete", "Solanaceae")
    variety_id = db.list_seed_varieties()[0]["id"]
    db.delete_seed_variety(variety_id)
    assert db.list_seed_varieties() == []


def test_delete_nonexistent_seed_variety_is_a_noop():
    db.delete_seed_variety(999999)
    assert db.list_seed_varieties() == []


def _add_variety(common_name="Tomato", variety_name="Cherokee Purple", plant_family="Solanaceae", **kwargs):
    db.add_seed_variety(common_name, variety_name, plant_family, **kwargs)
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


def test_list_plantings_includes_maturity_from_variety_join():
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


def test_list_land_plots_returns_empty_list_when_none_exist():
    assert db.list_land_plots() == []


def test_add_land_plot_persists_name_and_dimensions():
    db.add_land_plot("Back Field", 40, 60)
    plot = db.list_land_plots()[0]
    assert (plot["name"], plot["width_ft"], plot["length_ft"]) == ("Back Field", 40, 60)


def test_land_plots_ordered_by_name():
    db.add_land_plot("Zeta Field", 10, 10)
    db.add_land_plot("Alpha Field", 10, 10)
    assert [p["name"] for p in db.list_land_plots()] == ["Alpha Field", "Zeta Field"]


def test_get_land_plot_returns_matching_row():
    db.add_land_plot("Back Field", 40, 60)
    plot_id = db.list_land_plots()[0]["id"]
    assert db.get_land_plot(plot_id)["name"] == "Back Field"


def test_get_land_plot_returns_none_when_not_found():
    assert db.get_land_plot(999999) is None


def test_update_land_plot_changes_dimensions():
    db.add_land_plot("Back Field", 40, 60)
    plot_id = db.list_land_plots()[0]["id"]
    db.update_land_plot(plot_id, "Back Field", 50, 70)
    plot = db.get_land_plot(plot_id)
    assert (plot["width_ft"], plot["length_ft"]) == (50, 70)


def test_delete_land_plot_removes_it():
    db.add_land_plot("To delete", 10, 10)
    plot_id = db.list_land_plots()[0]["id"]
    db.delete_land_plot(plot_id)
    assert db.list_land_plots() == []


def test_delete_land_plot_cascades_to_its_beds():
    db.add_land_plot("Back Field", 40, 60)
    plot_id = db.list_land_plots()[0]["id"]
    db.add_bed(plot_id, "Bed 1", 4, 8)
    db.delete_land_plot(plot_id)
    assert db.list_beds_for_plot(plot_id) == []


def test_delete_nonexistent_land_plot_is_a_noop():
    db.delete_land_plot(999999)
    assert db.list_land_plots() == []


def _add_plot(name="Back Field", width_ft=40, length_ft=60):
    db.add_land_plot(name, width_ft, length_ft)
    return db.list_land_plots()[0]["id"]


def test_list_beds_for_plot_returns_empty_list_when_none_exist():
    plot_id = _add_plot()
    assert db.list_beds_for_plot(plot_id) == []


def test_add_bed_persists_label_and_dimensions():
    plot_id = _add_plot()
    db.add_bed(plot_id, "Bed 1", 4, 8)
    bed = db.list_beds_for_plot(plot_id)[0]
    assert (bed["label"], bed["width_ft"], bed["length_ft"]) == ("Bed 1", 4, 8)


def test_add_bed_starts_unplaced():
    plot_id = _add_plot()
    db.add_bed(plot_id, "Bed 1", 4, 8)
    bed = db.list_beds_for_plot(plot_id)[0]
    assert (bed["x"], bed["y"]) == (None, None)


def test_add_bed_defaults_rotation_to_zero():
    plot_id = _add_plot()
    db.add_bed(plot_id, "Bed 1", 4, 8)
    assert db.list_beds_for_plot(plot_id)[0]["rotation_deg"] == 0


def test_beds_for_plot_ordered_by_label():
    plot_id = _add_plot()
    db.add_bed(plot_id, "Bed 2", 4, 8)
    db.add_bed(plot_id, "Bed 1", 4, 8)
    assert [b["label"] for b in db.list_beds_for_plot(plot_id)] == ["Bed 1", "Bed 2"]


def test_get_bed_returns_matching_row():
    plot_id = _add_plot()
    db.add_bed(plot_id, "Bed 1", 4, 8)
    bed_id = db.list_beds_for_plot(plot_id)[0]["id"]
    assert db.get_bed(bed_id)["label"] == "Bed 1"


def test_get_bed_returns_none_when_not_found():
    assert db.get_bed(999999) is None


def test_update_bed_changes_label_and_rotation():
    plot_id = _add_plot()
    db.add_bed(plot_id, "Original", 4, 8)
    bed_id = db.list_beds_for_plot(plot_id)[0]["id"]
    db.update_bed(bed_id, "Updated", 4, 8, 90)
    bed = db.get_bed(bed_id)
    assert (bed["label"], bed["rotation_deg"]) == ("Updated", 90)


def test_update_bed_does_not_change_position():
    plot_id = _add_plot()
    db.add_bed(plot_id, "Bed 1", 4, 8)
    bed_id = db.list_beds_for_plot(plot_id)[0]["id"]
    db.update_bed_position(bed_id, 5, 6)
    db.update_bed(bed_id, "Bed 1", 4, 8, 0)
    bed = db.get_bed(bed_id)
    assert (bed["x"], bed["y"]) == (5, 6)


def test_update_bed_position_persists_coordinates():
    plot_id = _add_plot()
    db.add_bed(plot_id, "Bed 1", 4, 8)
    bed_id = db.list_beds_for_plot(plot_id)[0]["id"]
    db.update_bed_position(bed_id, 12, 20)
    bed = db.get_bed(bed_id)
    assert (bed["x"], bed["y"]) == (12, 20)


def test_update_bed_size_persists_dimensions():
    plot_id = _add_plot()
    db.add_bed(plot_id, "Bed 1", 4, 8)
    bed_id = db.list_beds_for_plot(plot_id)[0]["id"]
    db.update_bed_size(bed_id, 6, 10)
    bed = db.get_bed(bed_id)
    assert (bed["width_ft"], bed["length_ft"]) == (6, 10)


def test_delete_bed_removes_it():
    plot_id = _add_plot()
    db.add_bed(plot_id, "To delete", 4, 8)
    bed_id = db.list_beds_for_plot(plot_id)[0]["id"]
    db.delete_bed(bed_id)
    assert db.list_beds_for_plot(plot_id) == []


def test_delete_nonexistent_bed_is_a_noop():
    db.delete_bed(999999)
    assert db.list_beds_for_plot(999999) == []
