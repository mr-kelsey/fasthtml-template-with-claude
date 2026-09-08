from datetime import date, timedelta

import db

ALL_TIME = ("2000-01-01", "2100-01-01")


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


def test_add_seed_variety_persists_soil_and_feeding_fields():
    db.add_seed_variety(
        "Tomato", "Cherokee Purple", "Solanaceae",
        soil_type="loam", soil_ph_min=6.0, soil_ph_max=6.8, feeding_frequency_days=14,
        growth_npk_n=10.0, growth_npk_p=5.0, growth_npk_k=5.0,
        produce_npk_n=5.0, produce_npk_p=10.0, produce_npk_k=10.0,
    )
    variety = db.list_seed_varieties()[0]
    assert (variety["soil_type"], variety["soil_ph_min"], variety["soil_ph_max"]) == ("loam", 6.0, 6.8)
    assert variety["feeding_frequency_days"] == 14
    assert (variety["growth_npk_n"], variety["growth_npk_p"], variety["growth_npk_k"]) == (10.0, 5.0, 5.0)
    assert (variety["produce_npk_n"], variety["produce_npk_p"], variety["produce_npk_k"]) == (5.0, 10.0, 10.0)


def test_add_seed_variety_defaults_soil_and_feeding_fields_to_none():
    db.add_seed_variety("Tomato", "Cherokee Purple", "Solanaceae")
    variety = db.list_seed_varieties()[0]
    assert (variety["soil_type"], variety["soil_ph_min"], variety["feeding_frequency_days"], variety["growth_npk_n"]) == (
        None, None, None, None,
    )


def test_update_seed_variety_changes_soil_and_feeding_fields():
    db.add_seed_variety("Tomato", "Original", "Solanaceae")
    variety_id = db.list_seed_varieties()[0]["id"]
    db.update_seed_variety(variety_id, "Tomato", "Original", "Solanaceae", soil_type="clay", feeding_frequency_days=21)
    variety = db.get_seed_variety(variety_id)
    assert (variety["soil_type"], variety["feeding_frequency_days"]) == ("clay", 21)


def test_add_seed_variety_persists_sun_needs():
    db.add_seed_variety("Tomato", "Cherokee Purple", "Solanaceae", sun_needs="full_sun")
    assert db.list_seed_varieties()[0]["sun_needs"] == "full_sun"


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


def test_list_seed_lots_for_variety_returns_empty_list_when_none_exist():
    variety_id = _add_variety()
    assert db.list_seed_lots_for_variety(variety_id) == []


def test_add_seed_lot_persists_quantity_source_and_date():
    variety_id = _add_variety()
    db.add_seed_lot(variety_id, quantity_on_hand=50, acquired_date="2026-01-15", seed_source="Baker Creek")
    lot = db.list_seed_lots_for_variety(variety_id)[0]
    assert (lot["quantity_on_hand"], lot["acquired_date"], lot["seed_source"]) == (50, "2026-01-15", "Baker Creek")


def test_add_seed_lot_defaults_optional_fields_to_none():
    variety_id = _add_variety()
    db.add_seed_lot(variety_id)
    lot = db.list_seed_lots_for_variety(variety_id)[0]
    assert (lot["quantity_on_hand"], lot["acquired_date"], lot["seed_source"], lot["notes"]) == (None, None, None, None)


def test_seed_lots_for_variety_ordered_most_recently_acquired_first():
    variety_id = _add_variety()
    db.add_seed_lot(variety_id, acquired_date="2025-01-01")
    db.add_seed_lot(variety_id, acquired_date="2026-01-01")
    assert [lot["acquired_date"] for lot in db.list_seed_lots_for_variety(variety_id)] == ["2026-01-01", "2025-01-01"]


def test_list_seed_lots_for_variety_excludes_other_varieties_lots():
    variety_a = _add_variety(common_name="Tomato", variety_name="Cherokee Purple")
    variety_b = _add_variety(common_name="Pepper", variety_name="Bell")
    db.add_seed_lot(variety_b)
    assert db.list_seed_lots_for_variety(variety_a) == []


def test_get_seed_lot_returns_matching_row():
    variety_id = _add_variety()
    db.add_seed_lot(variety_id, seed_source="Baker Creek")
    lot_id = db.list_seed_lots_for_variety(variety_id)[0]["id"]
    assert db.get_seed_lot(lot_id)["seed_source"] == "Baker Creek"


def test_get_seed_lot_returns_none_when_not_found():
    assert db.get_seed_lot(999999) is None


def test_update_seed_lot_changes_quantity_on_hand():
    variety_id = _add_variety()
    db.add_seed_lot(variety_id, quantity_on_hand=50)
    lot_id = db.list_seed_lots_for_variety(variety_id)[0]["id"]
    db.update_seed_lot(lot_id, quantity_on_hand=30)
    assert db.get_seed_lot(lot_id)["quantity_on_hand"] == 30


def test_delete_seed_lot_removes_it():
    variety_id = _add_variety()
    db.add_seed_lot(variety_id)
    lot_id = db.list_seed_lots_for_variety(variety_id)[0]["id"]
    db.delete_seed_lot(lot_id)
    assert db.list_seed_lots_for_variety(variety_id) == []


def test_delete_nonexistent_seed_lot_is_a_noop():
    db.delete_seed_lot(999999)


def test_list_companion_rules_returns_empty_list_when_none_exist():
    assert db.list_companion_rules() == []


def test_add_companion_rule_persists_plants_and_relation():
    db.add_companion_rule("Tomato", "Basil", "companion")
    rule = db.list_companion_rules()[0]
    assert (rule["plant_a_common_name"], rule["plant_b_common_name"], rule["relation"]) == ("Tomato", "Basil", "companion")


def test_add_companion_rule_persists_notes():
    db.add_companion_rule("Tomato", "Fennel", "antagonist", notes="Fennel stunts tomato growth")
    rule = db.list_companion_rules()[0]
    assert rule["notes"] == "Fennel stunts tomato growth"


def test_add_companion_rule_defaults_notes_to_none():
    db.add_companion_rule("Tomato", "Basil", "companion")
    assert db.list_companion_rules()[0]["notes"] is None


def test_get_companion_rule_returns_matching_row():
    db.add_companion_rule("Tomato", "Basil", "companion")
    rule_id = db.list_companion_rules()[0]["id"]
    assert db.get_companion_rule(rule_id)["plant_b_common_name"] == "Basil"


def test_get_companion_rule_returns_none_when_not_found():
    assert db.get_companion_rule(999999) is None


def test_delete_companion_rule_removes_it():
    db.add_companion_rule("Tomato", "Basil", "companion")
    rule_id = db.list_companion_rules()[0]["id"]
    db.delete_companion_rule(rule_id)
    assert db.list_companion_rules() == []


def test_delete_nonexistent_companion_rule_is_a_noop():
    db.delete_companion_rule(999999)


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


def test_add_planting_persists_seed_lot_id():
    variety_id = _add_variety()
    db.add_seed_lot(variety_id)
    seed_lot_id = db.list_seed_lots_for_variety(variety_id)[0]["id"]
    db.add_planting(variety_id, "2026-05-01", seed_lot_id=seed_lot_id)
    assert db.list_plantings()[0]["seed_lot_id"] == seed_lot_id


def test_add_planting_defaults_seed_lot_id_to_none():
    variety_id = _add_variety()
    db.add_planting(variety_id, "2026-05-01")
    assert db.list_plantings()[0]["seed_lot_id"] is None


def test_update_planting_changes_seed_lot_id():
    variety_id = _add_variety()
    db.add_seed_lot(variety_id)
    seed_lot_id = db.list_seed_lots_for_variety(variety_id)[0]["id"]
    planting_id = db.add_planting(variety_id, "2026-05-01")
    db.update_planting(planting_id, variety_id, "2026-05-01", seed_lot_id=seed_lot_id)
    assert db.get_planting(planting_id)["seed_lot_id"] == seed_lot_id


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


def _add_bed(plot_id=None, width_ft=4, length_ft=8, label="Bed 1"):
    plot_id = plot_id or _add_plot()
    db.add_bed(plot_id, label, width_ft, length_ft)
    return db.list_beds_for_plot(plot_id)[0]["id"]


def test_list_farm_events_in_range_returns_empty_list_when_none_exist():
    assert db.list_farm_events_in_range(*ALL_TIME) == []


def test_add_farm_event_persists_type_title_and_dates():
    db.add_farm_event("custom", "Check frost cloth", "2026-03-01", "2026-03-02")
    event = db.list_farm_events_in_range(*ALL_TIME)[0]
    assert (event["event_type"], event["title"], event["start_date"], event["end_date"]) == (
        "custom", "Check frost cloth", "2026-03-01", "2026-03-02",
    )


def test_list_farm_events_in_range_excludes_event_outside_range():
    db.add_farm_event("custom", "Out of range", "2026-01-01", "2026-01-01")
    assert db.list_farm_events_in_range("2026-06-01", "2026-06-30") == []


def test_farm_events_ordered_by_start_date():
    db.add_farm_event("custom", "Later", "2026-06-01", "2026-06-01")
    db.add_farm_event("custom", "Earlier", "2026-01-01", "2026-01-01")
    assert [e["title"] for e in db.list_farm_events_in_range(*ALL_TIME)] == ["Earlier", "Later"]


def test_get_farm_event_returns_matching_row():
    db.add_farm_event("custom", "Check frost cloth", "2026-03-01", "2026-03-01")
    event_id = db.list_farm_events_in_range(*ALL_TIME)[0]["id"]
    assert db.get_farm_event(event_id)["title"] == "Check frost cloth"


def test_get_farm_event_returns_none_when_not_found():
    assert db.get_farm_event(999999) is None


def test_delete_farm_event_removes_it():
    db.add_farm_event("custom", "To delete", "2026-03-01", "2026-03-01")
    event_id = db.list_farm_events_in_range(*ALL_TIME)[0]["id"]
    db.delete_farm_event(event_id)
    assert db.list_farm_events_in_range(*ALL_TIME) == []


def test_delete_nonexistent_farm_event_is_a_noop():
    db.delete_farm_event(999999)
    assert db.list_farm_events_in_range(*ALL_TIME) == []


def test_manual_farm_event_has_no_linked_variety_or_bed():
    db.add_farm_event("custom", "Check frost cloth", "2026-03-01", "2026-03-01")
    event = db.list_farm_events_in_range(*ALL_TIME)[0]
    assert (event["variety_name"], event["bed_label"]) == (None, None)


def test_add_planting_without_bed_generates_germination_and_harvest_events():
    variety_id = _add_variety(
        germination_days_min=5, germination_days_max=10, days_to_maturity_min=60, days_to_maturity_max=70
    )
    db.add_planting(variety_id, "2026-05-01")
    events = db.list_farm_events_in_range(*ALL_TIME)
    assert sorted(e["event_type"] for e in events) == ["germination-check", "harvest"]


def test_generated_germination_event_uses_variety_day_range():
    variety_id = _add_variety(germination_days_min=5, germination_days_max=10)
    db.add_planting(variety_id, "2026-05-01")
    germination = db.list_farm_events_in_range(*ALL_TIME)[0]
    planted = date(2026, 5, 1)
    assert (germination["start_date"], germination["end_date"]) == (
        (planted + timedelta(days=5)).isoformat(), (planted + timedelta(days=10)).isoformat(),
    )


def test_generated_harvest_event_uses_variety_day_range():
    variety_id = _add_variety(days_to_maturity_min=60, days_to_maturity_max=70)
    db.add_planting(variety_id, "2026-05-01")
    harvest = db.list_farm_events_in_range(*ALL_TIME)[0]
    planted = date(2026, 5, 1)
    assert (harvest["start_date"], harvest["end_date"]) == (
        (planted + timedelta(days=60)).isoformat(), (planted + timedelta(days=70)).isoformat(),
    )


def test_generated_farm_event_includes_variety_name_from_join():
    variety_id = _add_variety(
        common_name="Tomato", variety_name="Cherokee Purple", days_to_maturity_min=60, days_to_maturity_max=70
    )
    db.add_planting(variety_id, "2026-05-01")
    event = db.list_farm_events_in_range(*ALL_TIME)[0]
    assert event["variety_name"] == "Cherokee Purple"


def test_generated_farm_event_includes_bed_label_from_join():
    variety_id = _add_variety(days_to_maturity_min=60, days_to_maturity_max=70)
    bed_id = _add_bed(label="Tomato Bed")
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, cell_x=0, cell_y=0)
    event = db.list_farm_events_in_range(*ALL_TIME)[0]
    assert event["bed_label"] == "Tomato Bed"


def test_add_planting_skips_germination_event_when_variety_lacks_germination_days():
    variety_id = _add_variety(days_to_maturity_min=60, days_to_maturity_max=70)
    db.add_planting(variety_id, "2026-05-01")
    assert [e["event_type"] for e in db.list_farm_events_in_range(*ALL_TIME)] == ["harvest"]


def test_add_planting_skips_harvest_event_when_variety_lacks_maturity_days():
    variety_id = _add_variety(germination_days_min=5, germination_days_max=10)
    db.add_planting(variety_id, "2026-05-01")
    assert [e["event_type"] for e in db.list_farm_events_in_range(*ALL_TIME)] == ["germination-check"]


def test_update_planting_regenerates_events_instead_of_duplicating():
    variety_id = _add_variety(days_to_maturity_min=60, days_to_maturity_max=70)
    planting_id = db.add_planting(variety_id, "2026-05-01")
    db.update_planting(planting_id, variety_id, "2026-06-01")
    assert len(db.list_farm_events_in_range(*ALL_TIME)) == 1


def test_update_planting_shifts_generated_event_dates():
    variety_id = _add_variety(days_to_maturity_min=60, days_to_maturity_max=70)
    planting_id = db.add_planting(variety_id, "2026-05-01")
    db.update_planting(planting_id, variety_id, "2026-06-01")
    harvest = db.list_farm_events_in_range(*ALL_TIME)[0]
    planted = date(2026, 6, 1)
    assert (harvest["start_date"], harvest["end_date"]) == (
        (planted + timedelta(days=60)).isoformat(), (planted + timedelta(days=70)).isoformat(),
    )


def test_delete_planting_removes_its_generated_events():
    variety_id = _add_variety(days_to_maturity_min=60, days_to_maturity_max=70)
    planting_id = db.add_planting(variety_id, "2026-05-01")
    db.delete_planting(planting_id)
    assert db.list_farm_events_in_range(*ALL_TIME) == []


def test_two_adjacent_same_variety_same_date_cells_produce_one_event_pair():
    variety_id = _add_variety(
        germination_days_min=5, germination_days_max=10, days_to_maturity_min=60, days_to_maturity_max=70
    )
    bed_id = _add_bed()
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, cell_x=0, cell_y=0)
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, cell_x=1, cell_y=0)
    events = db.list_farm_events_in_range(*ALL_TIME)
    assert sorted(e["event_type"] for e in events) == ["germination-check", "harvest"]


def test_merged_group_event_links_to_lowest_planting_id_in_the_group():
    variety_id = _add_variety(days_to_maturity_min=60, days_to_maturity_max=70)
    bed_id = _add_bed()
    first_id = db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, cell_x=0, cell_y=0)
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, cell_x=1, cell_y=0)
    event = db.list_farm_events_in_range(*ALL_TIME)[0]
    assert event["linked_planting_id"] == first_id


def test_two_diagonal_cells_do_not_merge():
    variety_id = _add_variety(days_to_maturity_min=60, days_to_maturity_max=70)
    bed_id = _add_bed()
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, cell_x=0, cell_y=0)
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, cell_x=1, cell_y=1)
    assert len(db.list_farm_events_in_range(*ALL_TIME)) == 2


def test_two_adjacent_cells_with_different_planted_dates_do_not_merge():
    variety_id = _add_variety(days_to_maturity_min=60, days_to_maturity_max=70)
    bed_id = _add_bed()
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, cell_x=0, cell_y=0)
    db.add_planting(variety_id, "2026-05-15", bed_id=bed_id, cell_x=1, cell_y=0)
    assert len(db.list_farm_events_in_range(*ALL_TIME)) == 2


def test_two_adjacent_cells_with_different_varieties_do_not_merge():
    variety_a = _add_variety(
        common_name="Tomato", variety_name="Cherokee Purple", days_to_maturity_min=60, days_to_maturity_max=70
    )
    variety_b = _add_variety(
        common_name="Pepper", variety_name="Bell", days_to_maturity_min=60, days_to_maturity_max=70
    )
    bed_id = _add_bed()
    db.add_planting(variety_a, "2026-05-01", bed_id=bed_id, cell_x=0, cell_y=0)
    db.add_planting(variety_b, "2026-05-01", bed_id=bed_id, cell_x=1, cell_y=0)
    assert len(db.list_farm_events_in_range(*ALL_TIME)) == 2


def test_three_contiguous_cells_produce_one_event_before_clearing_middle():
    variety_id = _add_variety(days_to_maturity_min=60, days_to_maturity_max=70)
    bed_id = _add_bed()
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, cell_x=0, cell_y=0)
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, cell_x=1, cell_y=0)
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, cell_x=2, cell_y=0)
    assert len(db.list_farm_events_in_range(*ALL_TIME)) == 1


def test_clearing_middle_cell_splits_merged_group_into_two():
    variety_id = _add_variety(days_to_maturity_min=60, days_to_maturity_max=70)
    bed_id = _add_bed()
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, cell_x=0, cell_y=0)
    middle_id = db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, cell_x=1, cell_y=0)
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, cell_x=2, cell_y=0)
    db.delete_planting(middle_id)
    assert len(db.list_farm_events_in_range(*ALL_TIME)) == 2


def test_list_plantings_for_bed_returns_empty_list_when_none_exist():
    bed_id = _add_bed()
    assert db.list_plantings_for_bed(bed_id) == []


def test_list_plantings_for_bed_includes_cell_coordinates():
    variety_id = _add_variety()
    bed_id = _add_bed()
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, cell_x=2, cell_y=3)
    planting = db.list_plantings_for_bed(bed_id)[0]
    assert (planting["cell_x"], planting["cell_y"]) == (2, 3)


def test_list_plantings_for_bed_excludes_plantings_in_other_beds():
    variety_id = _add_variety()
    db.add_land_plot("Plot A", 40, 60)
    db.add_land_plot("Plot B", 40, 60)
    plots_by_name = {p["name"]: p["id"] for p in db.list_land_plots()}
    bed_id = _add_bed(plot_id=plots_by_name["Plot A"])
    other_bed_id = _add_bed(plot_id=plots_by_name["Plot B"], label="Bed 2")
    db.add_planting(variety_id, "2026-05-01", bed_id=other_bed_id, cell_x=0, cell_y=0)
    assert db.list_plantings_for_bed(bed_id) == []


def test_list_plantings_at_cell_returns_matching_planting():
    variety_id = _add_variety()
    bed_id = _add_bed()
    planting_id = db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, cell_x=1, cell_y=2)
    assert db.list_plantings_at_cell(bed_id, 1, 2)[0]["id"] == planting_id


def test_list_plantings_at_cell_returns_empty_list_when_empty():
    bed_id = _add_bed()
    assert db.list_plantings_at_cell(bed_id, 1, 2) == []


def test_list_plantings_at_cell_returns_multiple_interplanted_varieties():
    "A cell can hold more than one planting -- e.g. interplanting carrots and tomatoes in the same square."
    variety_a = _add_variety(common_name="Tomato", variety_name="Cherokee Purple")
    variety_b = _add_variety(common_name="Carrot", variety_name="Danvers")
    bed_id = _add_bed()
    db.add_planting(variety_a, "2026-05-01", bed_id=bed_id, cell_x=0, cell_y=0)
    db.add_planting(variety_b, "2026-05-01", bed_id=bed_id, cell_x=0, cell_y=0)
    assert len(db.list_plantings_at_cell(bed_id, 0, 0)) == 2


def test_interplanted_cell_generates_separate_events_per_variety():
    variety_a = _add_variety(
        common_name="Tomato", variety_name="Cherokee Purple", days_to_maturity_min=60, days_to_maturity_max=70
    )
    variety_b = _add_variety(
        common_name="Carrot", variety_name="Danvers", days_to_maturity_min=60, days_to_maturity_max=70
    )
    bed_id = _add_bed()
    db.add_planting(variety_a, "2026-05-01", bed_id=bed_id, cell_x=0, cell_y=0)
    db.add_planting(variety_b, "2026-05-01", bed_id=bed_id, cell_x=0, cell_y=0)
    assert len(db.list_farm_events_in_range(*ALL_TIME)) == 2
