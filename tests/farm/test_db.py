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


def test_list_seed_lots_returns_empty_list_when_none_exist():
    assert db.list_seed_lots() == []


def test_list_seed_lots_includes_variety_name_from_join():
    variety_id = _add_variety(common_name="Tomato", variety_name="Cherokee Purple")
    db.add_seed_lot(variety_id, seed_source="Baker Creek")
    lot = db.list_seed_lots()[0]
    assert (lot["common_name"], lot["variety_name"], lot["seed_source"]) == ("Tomato", "Cherokee Purple", "Baker Creek")


def test_list_seed_lots_spans_every_variety():
    variety_a = _add_variety(common_name="Tomato", variety_name="Cherokee Purple")
    variety_b = _add_variety(common_name="Pepper", variety_name="Bell")
    db.add_seed_lot(variety_a)
    db.add_seed_lot(variety_b)
    assert len(db.list_seed_lots()) == 2


def test_list_transplant_lots_for_variety_returns_empty_list_when_none_exist():
    variety_id = _add_variety()
    assert db.list_transplant_lots_for_variety(variety_id) == []


def test_add_transplant_lot_persists_quantity_and_purchase_fields():
    variety_id = _add_variety()
    db.add_transplant_lot(
        variety_id, quantity_on_hand=12, purchased_source="store", purchased_vendor="Local Nursery",
        purchased_date="2026-04-01",
    )
    lot = db.list_transplant_lots_for_variety(variety_id)[0]
    assert (lot["quantity_on_hand"], lot["purchased_source"], lot["purchased_vendor"], lot["purchased_date"]) == (
        12, "store", "Local Nursery", "2026-04-01",
    )


def test_add_transplant_lot_persists_origin_planting_id():
    variety_id = _add_variety()
    origin_id = db.add_planting(variety_id, "2026-03-01")
    db.add_transplant_lot(variety_id, origin_planting_id=origin_id)
    lot = db.list_transplant_lots_for_variety(variety_id)[0]
    assert lot["origin_planting_id"] == origin_id


def test_add_transplant_lot_defaults_optional_fields_to_none():
    variety_id = _add_variety()
    db.add_transplant_lot(variety_id)
    lot = db.list_transplant_lots_for_variety(variety_id)[0]
    assert (lot["quantity_on_hand"], lot["origin_planting_id"], lot["purchased_source"], lot["notes"]) == (
        None, None, None, None,
    )


def test_list_transplant_lots_for_variety_excludes_other_varieties_lots():
    variety_a = _add_variety(common_name="Tomato", variety_name="Cherokee Purple")
    variety_b = _add_variety(common_name="Pepper", variety_name="Bell")
    db.add_transplant_lot(variety_b)
    assert db.list_transplant_lots_for_variety(variety_a) == []


def test_get_transplant_lot_returns_matching_row():
    variety_id = _add_variety()
    db.add_transplant_lot(variety_id, purchased_vendor="Local Nursery")
    lot_id = db.list_transplant_lots_for_variety(variety_id)[0]["id"]
    assert db.get_transplant_lot(lot_id)["purchased_vendor"] == "Local Nursery"


def test_get_transplant_lot_returns_none_when_not_found():
    assert db.get_transplant_lot(999999) is None


def test_update_transplant_lot_changes_quantity_on_hand():
    variety_id = _add_variety()
    db.add_transplant_lot(variety_id, quantity_on_hand=12)
    lot_id = db.list_transplant_lots_for_variety(variety_id)[0]["id"]
    db.update_transplant_lot(lot_id, quantity_on_hand=8)
    assert db.get_transplant_lot(lot_id)["quantity_on_hand"] == 8


def test_delete_transplant_lot_removes_it():
    variety_id = _add_variety()
    db.add_transplant_lot(variety_id)
    lot_id = db.list_transplant_lots_for_variety(variety_id)[0]["id"]
    db.delete_transplant_lot(lot_id)
    assert db.list_transplant_lots_for_variety(variety_id) == []


def test_delete_nonexistent_transplant_lot_is_a_noop():
    db.delete_transplant_lot(999999)


def test_list_transplant_lots_returns_empty_list_when_none_exist():
    assert db.list_transplant_lots() == []


def test_list_transplant_lots_includes_variety_name_from_join():
    variety_id = _add_variety(common_name="Tomato", variety_name="Cherokee Purple")
    db.add_transplant_lot(variety_id, purchased_vendor="Local Nursery")
    lot = db.list_transplant_lots()[0]
    assert (lot["common_name"], lot["variety_name"], lot["purchased_vendor"]) == (
        "Tomato", "Cherokee Purple", "Local Nursery",
    )


def test_list_transplant_lots_spans_every_variety():
    variety_a = _add_variety(common_name="Tomato", variety_name="Cherokee Purple")
    variety_b = _add_variety(common_name="Pepper", variety_name="Bell")
    db.add_transplant_lot(variety_a)
    db.add_transplant_lot(variety_b)
    assert len(db.list_transplant_lots()) == 2


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


def test_add_planting_defaults_source_type_to_seed():
    variety_id = _add_variety()
    db.add_planting(variety_id, "2026-05-01")
    assert db.list_plantings()[0]["source_type"] == "seed"


def test_add_planting_persists_transplant_source_type_and_lot_id():
    variety_id = _add_variety()
    db.add_transplant_lot(variety_id)
    transplant_lot_id = db.list_transplant_lots_for_variety(variety_id)[0]["id"]
    db.add_planting(variety_id, "2026-05-01", source_type="transplant", transplant_lot_id=transplant_lot_id)
    planting = db.list_plantings()[0]
    assert (planting["source_type"], planting["transplant_lot_id"]) == ("transplant", transplant_lot_id)


def test_add_planting_defaults_transplant_lot_id_to_none():
    variety_id = _add_variety()
    db.add_planting(variety_id, "2026-05-01")
    assert db.list_plantings()[0]["transplant_lot_id"] is None


def test_update_planting_changes_transplant_lot_id_and_source_type():
    variety_id = _add_variety()
    db.add_transplant_lot(variety_id)
    transplant_lot_id = db.list_transplant_lots_for_variety(variety_id)[0]["id"]
    planting_id = db.add_planting(variety_id, "2026-05-01")
    db.update_planting(
        planting_id, variety_id, "2026-05-01", source_type="transplant", transplant_lot_id=transplant_lot_id
    )
    planting = db.get_planting(planting_id)
    assert (planting["source_type"], planting["transplant_lot_id"]) == ("transplant", transplant_lot_id)


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


def test_list_plantings_includes_bed_label_and_plot_name_when_bed_set():
    plot_id = _add_plot(name="Back Field")
    bed_id = _add_bed(plot_id=plot_id, label="Bed 2")
    variety_id = _add_variety()
    db.batch_add_plantings(variety_id, "2026-05-01", bed_id, "seed", [(0, 0)])
    planting = db.list_plantings()[0]
    assert (planting["plot_name"], planting["bed_label"]) == ("Back Field", "Bed 2")


def test_list_plantings_bed_label_and_plot_name_are_none_for_free_text_location():
    variety_id = _add_variety()
    db.add_planting(variety_id, "2026-05-01", location="North corner")
    planting = db.list_plantings()[0]
    assert (planting["plot_name"], planting["bed_label"]) == (None, None)


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


def test_add_bed_starts_with_zero_grid_offset():
    plot_id = _add_plot()
    db.add_bed(plot_id, "Bed 1", 4, 8)
    bed = db.list_beds_for_plot(plot_id)[0]
    assert (bed["grid_offset_x_in"], bed["grid_offset_y_in"]) == (0, 0)


def test_shift_bed_grid_offset_accumulates_across_calls():
    plot_id = _add_plot()
    db.add_bed(plot_id, "Bed 1", 4, 8)
    bed_id = db.list_beds_for_plot(plot_id)[0]["id"]
    db.shift_bed_grid_offset(bed_id, 1, 0)
    db.shift_bed_grid_offset(bed_id, 1, 0)
    db.shift_bed_grid_offset(bed_id, 0, -1)
    bed = db.get_bed(bed_id)
    assert (bed["grid_offset_x_in"], bed["grid_offset_y_in"]) == (2, -1)


def test_delete_bed_removes_it():
    plot_id = _add_plot()
    db.add_bed(plot_id, "To delete", 4, 8)
    bed_id = db.list_beds_for_plot(plot_id)[0]["id"]
    db.delete_bed(bed_id)
    assert db.list_beds_for_plot(plot_id) == []


def test_delete_nonexistent_bed_is_a_noop():
    db.delete_bed(999999)
    assert db.list_beds_for_plot(999999) == []


def test_delete_bed_also_deletes_its_plantings():
    bed_id = _add_bed()
    variety_id = _add_variety()
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id)
    db.delete_bed(bed_id)
    assert db.list_plantings() == []


def test_delete_bed_removes_generated_events_for_its_plantings():
    bed_id = _add_bed()
    variety_id = _add_variety(days_to_maturity_min=60, days_to_maturity_max=70)
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id)
    db.delete_bed(bed_id)
    assert db.list_farm_events_in_range(*ALL_TIME) == []


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
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, x_in=0, y_in=0)
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


def test_transplant_planting_skips_germination_check_event():
    "Phase 7: a transplant already germinated elsewhere (or was purchased) -- nothing to check on-site."
    variety_id = _add_variety(
        germination_days_min=5, germination_days_max=10, days_to_maturity_min=60, days_to_maturity_max=70
    )
    db.add_planting(variety_id, "2026-05-01", source_type="transplant")
    assert [e["event_type"] for e in db.list_farm_events_in_range(*ALL_TIME)] == ["harvest"]


def test_seed_planting_still_generates_germination_check_event():
    variety_id = _add_variety(germination_days_min=5, germination_days_max=10)
    db.add_planting(variety_id, "2026-05-01", source_type="seed")
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


def test_update_planting_changing_variety_clears_old_groups_now_empty_event():
    variety_a = _add_variety(
        common_name="Tomato", variety_name="Cherokee Purple", days_to_maturity_min=60, days_to_maturity_max=70
    )
    variety_b = _add_variety(
        common_name="Pepper", variety_name="Bell", days_to_maturity_min=60, days_to_maturity_max=70
    )
    planting_id = db.add_planting(variety_a, "2026-05-01")
    db.update_planting(planting_id, variety_b, "2026-05-01")
    events = db.list_farm_events_in_range(*ALL_TIME)
    assert [e["variety_name"] for e in events] == ["Bell"]


def test_update_planting_changing_variety_leaves_other_members_of_old_group_intact():
    variety_a = _add_variety(
        common_name="Tomato", variety_name="Cherokee Purple", days_to_maturity_min=60, days_to_maturity_max=70
    )
    variety_b = _add_variety(
        common_name="Pepper", variety_name="Bell", days_to_maturity_min=60, days_to_maturity_max=70
    )
    stays_id = db.add_planting(variety_a, "2026-05-01")
    moves_id = db.add_planting(variety_a, "2026-05-01")
    db.update_planting(moves_id, variety_b, "2026-05-01")
    events = db.list_farm_events_in_range(*ALL_TIME)
    assert sorted(e["variety_name"] for e in events) == ["Bell", "Cherokee Purple"]
    assert any(e["linked_planting_id"] == stays_id for e in events)


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
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, x_in=0, y_in=0)
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, x_in=12, y_in=0)
    events = db.list_farm_events_in_range(*ALL_TIME)
    assert sorted(e["event_type"] for e in events) == ["germination-check", "harvest"]


def test_merged_group_event_links_to_lowest_planting_id_in_the_group():
    variety_id = _add_variety(days_to_maturity_min=60, days_to_maturity_max=70)
    bed_id = _add_bed()
    first_id = db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, x_in=0, y_in=0)
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, x_in=12, y_in=0)
    event = db.list_farm_events_in_range(*ALL_TIME)[0]
    assert event["linked_planting_id"] == first_id


def test_two_diagonal_cells_of_same_variety_and_date_still_merge():
    "Phase 7: grouping is flat by (variety, planted_date), not spatial adjacency -- position no longer matters."
    variety_id = _add_variety(days_to_maturity_min=60, days_to_maturity_max=70)
    bed_id = _add_bed()
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, x_in=0, y_in=0)
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, x_in=12, y_in=12)
    assert len(db.list_farm_events_in_range(*ALL_TIME)) == 1


def test_same_variety_and_date_plantings_in_different_beds_merge_into_one_event():
    variety_id = _add_variety(days_to_maturity_min=60, days_to_maturity_max=70)
    bed_a = _add_bed(label="Bed A")
    bed_b = _add_bed(label="Bed B")
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_a, x_in=0, y_in=0)
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_b, x_in=0, y_in=0)
    assert len(db.list_farm_events_in_range(*ALL_TIME)) == 1


def test_same_variety_and_date_bed_and_location_plantings_merge_into_one_event():
    "Grouping is bed-placed or not -- a free-text location planting merges with a bed planting sharing the key."
    variety_id = _add_variety(days_to_maturity_min=60, days_to_maturity_max=70)
    bed_id = _add_bed()
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, x_in=0, y_in=0)
    db.add_planting(variety_id, "2026-05-01", location="Back row")
    assert len(db.list_farm_events_in_range(*ALL_TIME)) == 1


def test_two_adjacent_cells_with_different_planted_dates_do_not_merge():
    variety_id = _add_variety(days_to_maturity_min=60, days_to_maturity_max=70)
    bed_id = _add_bed()
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, x_in=0, y_in=0)
    db.add_planting(variety_id, "2026-05-15", bed_id=bed_id, x_in=12, y_in=0)
    assert len(db.list_farm_events_in_range(*ALL_TIME)) == 2


def test_two_adjacent_cells_with_different_varieties_do_not_merge():
    variety_a = _add_variety(
        common_name="Tomato", variety_name="Cherokee Purple", days_to_maturity_min=60, days_to_maturity_max=70
    )
    variety_b = _add_variety(
        common_name="Pepper", variety_name="Bell", days_to_maturity_min=60, days_to_maturity_max=70
    )
    bed_id = _add_bed()
    db.add_planting(variety_a, "2026-05-01", bed_id=bed_id, x_in=0, y_in=0)
    db.add_planting(variety_b, "2026-05-01", bed_id=bed_id, x_in=12, y_in=0)
    assert len(db.list_farm_events_in_range(*ALL_TIME)) == 2


def test_three_contiguous_cells_produce_one_event_before_clearing_middle():
    variety_id = _add_variety(days_to_maturity_min=60, days_to_maturity_max=70)
    bed_id = _add_bed()
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, x_in=0, y_in=0)
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, x_in=12, y_in=0)
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, x_in=24, y_in=0)
    assert len(db.list_farm_events_in_range(*ALL_TIME)) == 1


def test_deleting_one_planting_does_not_split_the_remaining_shared_group():
    "Phase 7: no spatial adjacency to split on -- the survivors still share (variety, planted_date), still one event."
    variety_id = _add_variety(days_to_maturity_min=60, days_to_maturity_max=70)
    bed_id = _add_bed()
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, x_in=0, y_in=0)
    middle_id = db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, x_in=12, y_in=0)
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, x_in=24, y_in=0)
    db.delete_planting(middle_id)
    assert len(db.list_farm_events_in_range(*ALL_TIME)) == 1


def test_list_plantings_for_bed_returns_empty_list_when_none_exist():
    bed_id = _add_bed()
    assert db.list_plantings_for_bed(bed_id) == []


def test_list_plantings_for_bed_includes_inch_position():
    variety_id = _add_variety()
    bed_id = _add_bed()
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, x_in=24, y_in=36)
    planting = db.list_plantings_for_bed(bed_id)[0]
    assert (planting["x_in"], planting["y_in"]) == (24, 36)


def test_list_plantings_for_bed_excludes_plantings_in_other_beds():
    variety_id = _add_variety()
    db.add_land_plot("Plot A", 40, 60)
    db.add_land_plot("Plot B", 40, 60)
    plots_by_name = {p["name"]: p["id"] for p in db.list_land_plots()}
    bed_id = _add_bed(plot_id=plots_by_name["Plot A"])
    other_bed_id = _add_bed(plot_id=plots_by_name["Plot B"], label="Bed 2")
    db.add_planting(variety_id, "2026-05-01", bed_id=other_bed_id, x_in=0, y_in=0)
    assert db.list_plantings_for_bed(bed_id) == []


def test_interplanted_cell_generates_separate_events_per_variety():
    variety_a = _add_variety(
        common_name="Tomato", variety_name="Cherokee Purple", days_to_maturity_min=60, days_to_maturity_max=70
    )
    variety_b = _add_variety(
        common_name="Carrot", variety_name="Danvers", days_to_maturity_min=60, days_to_maturity_max=70
    )
    bed_id = _add_bed()
    db.add_planting(variety_a, "2026-05-01", bed_id=bed_id, x_in=0, y_in=0)
    db.add_planting(variety_b, "2026-05-01", bed_id=bed_id, x_in=0, y_in=0)
    assert len(db.list_farm_events_in_range(*ALL_TIME)) == 2


def test_add_seed_variety_persists_color_hex():
    db.add_seed_variety("Tomato", "Cherokee Purple", "Solanaceae", color_hex="#e6194b")
    assert db.list_seed_varieties()[0]["color_hex"] == "#e6194b"


def test_update_seed_variety_changes_color_hex():
    variety_id = _add_variety()
    db.update_seed_variety(variety_id, "Tomato", "Cherokee Purple", "Solanaceae", color_hex="#3cb44b")
    assert db.get_seed_variety(variety_id)["color_hex"] == "#3cb44b"


def test_add_planting_persists_soil_temp_f():
    variety_id = _add_variety()
    db.add_planting(variety_id, "2026-05-01", soil_temp_f=65.5)
    assert db.get_planting(db.list_plantings()[0]["id"])["soil_temp_f"] == 65.5


def test_update_planting_changes_soil_temp_f():
    variety_id = _add_variety()
    planting_id = db.add_planting(variety_id, "2026-05-01")
    db.update_planting(planting_id, variety_id, "2026-05-01", soil_temp_f=70.0)
    assert db.get_planting(planting_id)["soil_temp_f"] == 70.0


def test_list_seed_varieties_with_seed_stock_includes_variety_with_any_lot():
    variety_id = _add_variety()
    db.add_seed_lot(variety_id, quantity_on_hand=0)
    assert [v["id"] for v in db.list_seed_varieties_with_seed_stock()] == [variety_id]


def test_list_seed_varieties_with_seed_stock_excludes_variety_without_a_lot():
    _add_variety()
    assert db.list_seed_varieties_with_seed_stock() == []


def test_list_seed_varieties_with_transplant_stock_includes_variety_with_positive_quantity():
    variety_id = _add_variety()
    db.add_transplant_lot(variety_id, quantity_on_hand=5)
    assert [v["id"] for v in db.list_seed_varieties_with_transplant_stock()] == [variety_id]


def test_list_seed_varieties_with_transplant_stock_excludes_zero_quantity_lot():
    variety_id = _add_variety()
    db.add_transplant_lot(variety_id, quantity_on_hand=0)
    assert db.list_seed_varieties_with_transplant_stock() == []


def test_list_available_transplant_lots_for_variety_excludes_zero_quantity_lot():
    variety_id = _add_variety()
    db.add_transplant_lot(variety_id, quantity_on_hand=0)
    assert db.list_available_transplant_lots_for_variety(variety_id) == []


def test_list_available_transplant_lots_for_variety_includes_positive_quantity_lot():
    variety_id = _add_variety()
    db.add_transplant_lot(variety_id, quantity_on_hand=3)
    lot_id = db.list_transplant_lots_for_variety(variety_id)[0]["id"]
    assert [lot["id"] for lot in db.list_available_transplant_lots_for_variety(variety_id)] == [lot_id]


def test_update_transplant_lot_quantity_changes_only_quantity():
    variety_id = _add_variety()
    db.add_transplant_lot(variety_id, quantity_on_hand=10, purchased_vendor="Local Nursery")
    lot_id = db.list_transplant_lots_for_variety(variety_id)[0]["id"]
    db.update_transplant_lot_quantity(lot_id, 6)
    lot = db.get_transplant_lot(lot_id)
    assert (lot["quantity_on_hand"], lot["purchased_vendor"]) == (6, "Local Nursery")


def test_list_plantings_by_transplant_lot_returns_matching_plantings():
    variety_id = _add_variety()
    bed_id = _add_bed()
    db.add_transplant_lot(variety_id, quantity_on_hand=5)
    lot_id = db.list_transplant_lots_for_variety(variety_id)[0]["id"]
    planting_ids = db.batch_add_plantings(
        variety_id, "2026-05-01", bed_id, "transplant", [(0, 0), (16, 0)], transplant_lot_id=lot_id
    )
    assert sorted(p["id"] for p in db.list_plantings_by_transplant_lot(lot_id)) == sorted(planting_ids)


def test_list_plantings_by_transplant_lot_excludes_other_lots():
    variety_id = _add_variety()
    db.add_transplant_lot(variety_id, quantity_on_hand=5)
    lot_id = db.list_transplant_lots_for_variety(variety_id)[0]["id"]
    assert db.list_plantings_by_transplant_lot(lot_id) == []


def test_batch_add_plantings_creates_one_row_per_point():
    variety_id = _add_variety()
    bed_id = _add_bed()
    db.batch_add_plantings(variety_id, "2026-05-01", bed_id, "seed", [(0, 0), (16, 0), (32, 0)])
    assert len(db.list_plantings_for_bed(bed_id)) == 3


def test_batch_add_plantings_sets_quantity_one_per_point():
    variety_id = _add_variety()
    bed_id = _add_bed()
    db.batch_add_plantings(variety_id, "2026-05-01", bed_id, "seed", [(0, 0)])
    assert db.list_plantings_for_bed(bed_id)[0]["quantity"] == 1


def test_batch_add_plantings_sets_quantity_to_quantity_per_point():
    variety_id = _add_variety()
    bed_id = _add_bed()
    db.batch_add_plantings(variety_id, "2026-05-01", bed_id, "seed", [(0, 0), (16, 0)], quantity_per_point=5)
    assert [p["quantity"] for p in db.list_plantings_for_bed(bed_id)] == [5, 5]


def test_batch_add_plantings_returns_new_planting_ids():
    variety_id = _add_variety()
    bed_id = _add_bed()
    ids = db.batch_add_plantings(variety_id, "2026-05-01", bed_id, "seed", [(0, 0), (16, 0)])
    assert len(ids) == 2


def test_batch_add_plantings_decrements_transplant_lot_by_batch_count():
    variety_id = _add_variety()
    bed_id = _add_bed()
    db.add_transplant_lot(variety_id, quantity_on_hand=10)
    lot_id = db.list_transplant_lots_for_variety(variety_id)[0]["id"]
    db.batch_add_plantings(
        variety_id, "2026-05-01", bed_id, "transplant", [(0, 0), (16, 0)], transplant_lot_id=lot_id
    )
    assert db.get_transplant_lot(lot_id)["quantity_on_hand"] == 8


def test_batch_add_plantings_decrements_seed_lot_by_points_times_quantity_per_point():
    variety_id = _add_variety()
    bed_id = _add_bed()
    db.add_seed_lot(variety_id, quantity_on_hand=50)
    lot_id = db.list_seed_lots_for_variety(variety_id)[0]["id"]
    db.batch_add_plantings(variety_id, "2026-05-01", bed_id, "seed", [(0, 0), (16, 0), (32, 0)], quantity_per_point=5)
    assert db.get_seed_lot(lot_id)["quantity_on_hand"] == 35


def test_batch_add_plantings_leaves_seed_lot_untouched_in_transplant_mode():
    variety_id = _add_variety()
    bed_id = _add_bed()
    db.add_seed_lot(variety_id, quantity_on_hand=50)
    lot_id = db.list_seed_lots_for_variety(variety_id)[0]["id"]
    db.add_transplant_lot(variety_id, quantity_on_hand=5)
    transplant_lot_id = db.list_transplant_lots_for_variety(variety_id)[0]["id"]
    db.batch_add_plantings(variety_id, "2026-05-01", bed_id, "transplant", [(0, 0)], transplant_lot_id=transplant_lot_id)
    assert db.get_seed_lot(lot_id)["quantity_on_hand"] == 50


def test_batch_add_plantings_decrements_oldest_seed_lot_first():
    variety_id = _add_variety()
    bed_id = _add_bed()
    db.add_seed_lot(variety_id, quantity_on_hand=3, acquired_date="2025-01-01")
    db.add_seed_lot(variety_id, quantity_on_hand=10, acquired_date="2026-01-01")
    lots = {lot["acquired_date"]: lot["id"] for lot in db.list_seed_lots_for_variety(variety_id)}
    db.batch_add_plantings(variety_id, "2026-05-01", bed_id, "seed", [(0, 0)], quantity_per_point=5)
    old_lot = db.get_seed_lot(lots["2025-01-01"])
    new_lot = db.get_seed_lot(lots["2026-01-01"])
    assert (old_lot["quantity_on_hand"], new_lot["quantity_on_hand"]) == (0, 8)


def test_batch_add_plantings_clamps_seed_lot_at_zero_when_insufficient():
    variety_id = _add_variety()
    bed_id = _add_bed()
    db.add_seed_lot(variety_id, quantity_on_hand=2)
    lot_id = db.list_seed_lots_for_variety(variety_id)[0]["id"]
    db.batch_add_plantings(variety_id, "2026-05-01", bed_id, "seed", [(0, 0)], quantity_per_point=5)
    assert db.get_seed_lot(lot_id)["quantity_on_hand"] == 0


def test_batch_add_plantings_skips_seed_lot_with_untracked_quantity():
    variety_id = _add_variety()
    bed_id = _add_bed()
    db.add_seed_lot(variety_id, quantity_on_hand=None)
    lot_id = db.list_seed_lots_for_variety(variety_id)[0]["id"]
    db.batch_add_plantings(variety_id, "2026-05-01", bed_id, "seed", [(0, 0)], quantity_per_point=5)
    assert db.get_seed_lot(lot_id)["quantity_on_hand"] is None


def test_batch_add_plantings_regenerates_bed_farm_events_once():
    variety_id = _add_variety(days_to_maturity_min=60, days_to_maturity_max=70)
    bed_id = _add_bed()
    db.batch_add_plantings(variety_id, "2026-05-01", bed_id, "seed", [(0, 0), (12, 0), (24, 0)])
    assert len(db.list_farm_events_in_range(*ALL_TIME)) == 1


def test_batch_add_plantings_persists_source_type():
    variety_id = _add_variety()
    bed_id = _add_bed()
    db.add_transplant_lot(variety_id, quantity_on_hand=5)
    lot_id = db.list_transplant_lots_for_variety(variety_id)[0]["id"]
    db.batch_add_plantings(variety_id, "2026-05-01", bed_id, "transplant", [(0, 0)], transplant_lot_id=lot_id)
    assert db.list_plantings_for_bed(bed_id)[0]["source_type"] == "transplant"


def test_batch_add_plantings_persists_shade_warning_flag_per_point():
    variety_id = _add_variety()
    bed_id = _add_bed()
    ids = db.batch_add_plantings(
        variety_id, "2026-05-01", bed_id, "seed", [(0, 0), (16, 0)], shade_warnings=[True, False]
    )
    assert [bool(db.get_planting(pid)["shade_warning"]) for pid in ids] == [True, False]


def test_batch_add_plantings_leaves_shade_warning_null_when_not_given():
    variety_id = _add_variety()
    bed_id = _add_bed()
    ids = db.batch_add_plantings(variety_id, "2026-05-01", bed_id, "seed", [(0, 0)])
    assert db.get_planting(ids[0])["shade_warning"] is None


def test_batch_add_plantings_second_batch_of_same_variety_and_date_merges_into_shared_event():
    "Batching by submission is a UI convenience only -- separate batches share the (variety, date) grouping."
    variety_id = _add_variety(days_to_maturity_min=60, days_to_maturity_max=70)
    bed_id = _add_bed()
    db.batch_add_plantings(variety_id, "2026-05-01", bed_id, "seed", [(0, 0), (12, 0)])
    db.batch_add_plantings(variety_id, "2026-05-01", bed_id, "seed", [(24, 0)])
    assert len(db.list_farm_events_in_range(*ALL_TIME)) == 1


def _add_garden_product(name="Fish Emulsion", product_type="fertilizer", **kwargs):
    db.add_garden_product(name, product_type=product_type, **kwargs)
    return db.list_garden_products()[0]["id"]


def test_list_garden_products_returns_empty_list_when_none_exist():
    assert db.list_garden_products() == []


def test_add_garden_product_persists_name_and_type():
    db.add_garden_product("Fish Emulsion", product_type="fertilizer")
    product = db.list_garden_products()[0]
    assert (product["name"], product["product_type"]) == ("Fish Emulsion", "fertilizer")


def test_add_garden_product_persists_npk_and_benefit_notes():
    db.add_garden_product(
        "Fish Emulsion", product_type="fertilizer", npk_n=5.0, npk_p=1.0, npk_k=1.0, benefit_notes="General feeding"
    )
    product = db.list_garden_products()[0]
    assert (product["npk_n"], product["npk_p"], product["npk_k"], product["benefit_notes"]) == (5.0, 1.0, 1.0, "General feeding")


def test_add_garden_product_persists_application_frequency_days():
    db.add_garden_product("Fish Emulsion", application_frequency_days=14)
    assert db.list_garden_products()[0]["application_frequency_days"] == 14


def test_add_garden_product_defaults_optional_fields_to_none():
    db.add_garden_product("Fish Emulsion")
    product = db.list_garden_products()[0]
    assert (product["product_type"], product["npk_n"], product["benefit_notes"], product["application_frequency_days"]) == (
        None, None, None, None,
    )


def test_get_garden_product_returns_matching_row():
    db.add_garden_product("Fish Emulsion")
    product_id = db.list_garden_products()[0]["id"]
    assert db.get_garden_product(product_id)["name"] == "Fish Emulsion"


def test_get_garden_product_returns_none_when_not_found():
    assert db.get_garden_product(999999) is None


def test_update_garden_product_changes_application_frequency_days():
    product_id = _add_garden_product()
    db.update_garden_product(product_id, "Fish Emulsion", product_type="fertilizer", application_frequency_days=21)
    assert db.get_garden_product(product_id)["application_frequency_days"] == 21


def test_delete_garden_product_removes_it():
    product_id = _add_garden_product()
    db.delete_garden_product(product_id)
    assert db.list_garden_products() == []


def test_delete_nonexistent_garden_product_is_a_noop():
    db.delete_garden_product(999999)


def test_delete_garden_product_cascades_to_its_applications():
    product_id = _add_garden_product()
    db.add_product_application(product_id, "2026-05-01", location="North fence row")
    db.delete_garden_product(product_id)
    assert db.list_product_applications() == []


def test_delete_garden_product_cascades_to_its_applications_farm_events():
    product_id = _add_garden_product(application_frequency_days=14)
    db.add_product_application(product_id, "2026-05-01", location="North fence row")
    db.delete_garden_product(product_id)
    assert db.list_farm_events_in_range(*ALL_TIME) == []


def test_list_product_applications_returns_empty_list_when_none_exist():
    assert db.list_product_applications() == []


def test_add_product_application_persists_date_amount_and_unit():
    product_id = _add_garden_product()
    db.add_product_application(product_id, "2026-05-01", location="North fence row", amount=2.5, unit="cups")
    application = db.list_product_applications()[0]
    assert (application["applied_date"], application["amount"], application["unit"]) == ("2026-05-01", 2.5, "cups")


def test_add_product_application_persists_bed_id():
    product_id = _add_garden_product()
    bed_id = _add_bed()
    db.add_product_application(product_id, "2026-05-01", bed_id=bed_id)
    assert db.list_product_applications()[0]["bed_id"] == bed_id


def test_add_product_application_defaults_optional_fields_to_none():
    product_id = _add_garden_product()
    db.add_product_application(product_id, "2026-05-01")
    application = db.list_product_applications()[0]
    assert (application["bed_id"], application["location"], application["amount"], application["notes"]) == (
        None, None, None, None,
    )


def test_list_product_applications_includes_product_name_from_join():
    product_id = _add_garden_product(name="Fish Emulsion")
    db.add_product_application(product_id, "2026-05-01")
    assert db.list_product_applications()[0]["product_name"] == "Fish Emulsion"


def test_get_product_application_returns_matching_row():
    product_id = _add_garden_product()
    db.add_product_application(product_id, "2026-05-01", unit="cups")
    application_id = db.list_product_applications()[0]["id"]
    assert db.get_product_application(application_id)["unit"] == "cups"


def test_get_product_application_returns_none_when_not_found():
    assert db.get_product_application(999999) is None


def test_update_product_application_changes_amount():
    product_id = _add_garden_product()
    db.add_product_application(product_id, "2026-05-01", amount=1.0)
    application_id = db.list_product_applications()[0]["id"]
    db.update_product_application(application_id, product_id, "2026-05-01", amount=2.0)
    assert db.get_product_application(application_id)["amount"] == 2.0


def test_delete_product_application_removes_it():
    product_id = _add_garden_product()
    db.add_product_application(product_id, "2026-05-01")
    application_id = db.list_product_applications()[0]["id"]
    db.delete_product_application(application_id)
    assert db.list_product_applications() == []


def test_delete_nonexistent_product_application_is_a_noop():
    db.delete_product_application(999999)
    assert db.list_product_applications() == []


def test_add_product_application_with_frequency_creates_reminder_event():
    product_id = _add_garden_product(application_frequency_days=14)
    db.add_product_application(product_id, "2026-05-01", location="North fence row")
    events = db.list_farm_events_in_range(*ALL_TIME)
    assert [e["event_type"] for e in events] == ["product-reminder"]


def test_reminder_event_falls_on_applied_date_plus_frequency():
    product_id = _add_garden_product(application_frequency_days=14)
    db.add_product_application(product_id, "2026-05-01", location="North fence row")
    reminder = db.list_farm_events_in_range(*ALL_TIME)[0]
    assert (reminder["start_date"], reminder["end_date"]) == ("2026-05-15", "2026-05-15")


def test_add_product_application_without_frequency_creates_no_reminder():
    product_id = _add_garden_product()
    db.add_product_application(product_id, "2026-05-01", location="North fence row")
    assert db.list_farm_events_in_range(*ALL_TIME) == []


def test_second_application_for_same_target_supersedes_prior_reminder():
    product_id = _add_garden_product(application_frequency_days=14)
    db.add_product_application(product_id, "2026-05-01", location="North fence row")
    db.add_product_application(product_id, "2026-05-15", location="North fence row")
    events = db.list_farm_events_in_range(*ALL_TIME)
    assert len(events) == 1


def test_second_application_reminder_uses_latest_applied_date():
    product_id = _add_garden_product(application_frequency_days=14)
    db.add_product_application(product_id, "2026-05-01", location="North fence row")
    db.add_product_application(product_id, "2026-05-15", location="North fence row")
    reminder = db.list_farm_events_in_range(*ALL_TIME)[0]
    assert reminder["start_date"] == "2026-05-29"


def test_application_for_different_location_does_not_supersede_reminder():
    product_id = _add_garden_product(application_frequency_days=14)
    db.add_product_application(product_id, "2026-05-01", location="North fence row")
    db.add_product_application(product_id, "2026-05-01", location="South fence row")
    assert len(db.list_farm_events_in_range(*ALL_TIME)) == 2


def test_application_for_different_bed_does_not_supersede_reminder():
    product_id = _add_garden_product(application_frequency_days=14)
    db.add_land_plot("Plot A", 40, 60)
    db.add_land_plot("Plot B", 40, 60)
    plots_by_name = {p["name"]: p["id"] for p in db.list_land_plots()}
    bed_a = _add_bed(plot_id=plots_by_name["Plot A"], label="Bed A")
    bed_b = _add_bed(plot_id=plots_by_name["Plot B"], label="Bed B")
    db.add_product_application(product_id, "2026-05-01", bed_id=bed_a)
    db.add_product_application(product_id, "2026-05-01", bed_id=bed_b)
    assert len(db.list_farm_events_in_range(*ALL_TIME)) == 2


def test_delete_product_application_removes_its_reminder():
    product_id = _add_garden_product(application_frequency_days=14)
    db.add_product_application(product_id, "2026-05-01", location="North fence row")
    application_id = db.list_product_applications()[0]["id"]
    db.delete_product_application(application_id)
    assert db.list_farm_events_in_range(*ALL_TIME) == []


def test_list_beds_returns_empty_list_when_none_exist():
    assert db.list_beds() == []


def test_list_beds_spans_every_plot():
    plot_a_id = _add_plot(name="Plot A")
    plot_b_id = _add_plot(name="Plot B")
    _add_bed(plot_id=plot_a_id, label="Bed 1")
    _add_bed(plot_id=plot_b_id, label="Bed 2")
    assert len(db.list_beds()) == 2


def test_list_beds_includes_plot_name_from_join():
    plot_id = _add_plot(name="Back Field")
    _add_bed(plot_id=plot_id, label="Bed 1")
    assert db.list_beds()[0]["plot_name"] == "Back Field"


def test_update_planting_persists_quantity_culled():
    variety_id = _add_variety()
    planting_id = db.add_planting(variety_id, "2026-05-01", quantity_germinated=10)
    db.update_planting(planting_id, variety_id, "2026-05-01", quantity_germinated=10, quantity_culled=4)
    assert db.get_planting(planting_id)["quantity_culled"] == 4


def test_add_planting_defaults_quantity_culled_to_none():
    variety_id = _add_variety()
    planting_id = db.add_planting(variety_id, "2026-05-01")
    assert db.get_planting(planting_id)["quantity_culled"] is None


def test_list_shade_sources_for_plot_returns_empty_list_when_none_exist():
    plot_id = _add_plot()
    assert db.list_shade_sources_for_plot(plot_id) == []


def test_add_shade_source_persists_label():
    plot_id = _add_plot()
    db.add_shade_source(plot_id, "Oak tree")
    assert db.list_shade_sources_for_plot(plot_id)[0]["label"] == "Oak tree"


def test_get_shade_source_returns_matching_row():
    plot_id = _add_plot()
    db.add_shade_source(plot_id, "Oak tree")
    source_id = db.list_shade_sources_for_plot(plot_id)[0]["id"]
    assert db.get_shade_source(source_id)["label"] == "Oak tree"


def test_get_shade_source_returns_none_when_not_found():
    assert db.get_shade_source(999999) is None


def test_delete_shade_source_removes_it():
    plot_id = _add_plot()
    db.add_shade_source(plot_id, "To delete")
    source_id = db.list_shade_sources_for_plot(plot_id)[0]["id"]
    db.delete_shade_source(source_id)
    assert db.list_shade_sources_for_plot(plot_id) == []


def test_delete_shade_source_cascades_to_its_polygons():
    plot_id = _add_plot()
    db.add_shade_source(plot_id, "Oak tree")
    source_id = db.list_shade_sources_for_plot(plot_id)[0]["id"]
    db.save_shade_polygon(source_id, "summer_solstice", "full", '[[0,0],[0,1],[1,1]]')
    db.delete_shade_source(source_id)
    assert db.list_shade_polygons_for_source(source_id) == []


def test_save_shade_polygon_persists_points():
    plot_id = _add_plot()
    db.add_shade_source(plot_id, "Oak tree")
    source_id = db.list_shade_sources_for_plot(plot_id)[0]["id"]
    db.save_shade_polygon(source_id, "summer_solstice", "full", '[[0,0],[0,1],[1,1]]')
    polygon = db.list_shade_polygons_for_source(source_id)[0]
    assert polygon["points"] == '[[0,0],[0,1],[1,1]]'


def test_save_shade_polygon_upserts_in_place_for_the_same_season_and_type():
    plot_id = _add_plot()
    db.add_shade_source(plot_id, "Oak tree")
    source_id = db.list_shade_sources_for_plot(plot_id)[0]["id"]
    db.save_shade_polygon(source_id, "summer_solstice", "full", '[[0,0],[0,1],[1,1]]')
    db.save_shade_polygon(source_id, "summer_solstice", "full", '[[0,0],[0,2],[2,2]]')
    assert len(db.list_shade_polygons_for_source(source_id)) == 1


def test_save_shade_polygon_returns_the_same_id_on_update():
    plot_id = _add_plot()
    db.add_shade_source(plot_id, "Oak tree")
    source_id = db.list_shade_sources_for_plot(plot_id)[0]["id"]
    first_id = db.save_shade_polygon(source_id, "summer_solstice", "full", '[[0,0],[0,1],[1,1]]')
    second_id = db.save_shade_polygon(source_id, "summer_solstice", "full", '[[0,0],[0,2],[2,2]]')
    assert first_id == second_id


def test_save_shade_polygon_keeps_different_season_type_combos_separate():
    plot_id = _add_plot()
    db.add_shade_source(plot_id, "Oak tree")
    source_id = db.list_shade_sources_for_plot(plot_id)[0]["id"]
    db.save_shade_polygon(source_id, "summer_solstice", "full", '[[0,0],[0,1],[1,1]]')
    db.save_shade_polygon(source_id, "winter_solstice", "partial", '[[0,0],[0,2],[2,2]]')
    assert len(db.list_shade_polygons_for_source(source_id)) == 2


def test_get_shade_polygon_returns_matching_row():
    plot_id = _add_plot()
    db.add_shade_source(plot_id, "Oak tree")
    source_id = db.list_shade_sources_for_plot(plot_id)[0]["id"]
    polygon_id = db.save_shade_polygon(source_id, "summer_solstice", "full", '[[0,0],[0,1],[1,1]]')
    assert db.get_shade_polygon(polygon_id)["shade_type"] == "full"


def test_delete_shade_polygon_removes_it():
    plot_id = _add_plot()
    db.add_shade_source(plot_id, "Oak tree")
    source_id = db.list_shade_sources_for_plot(plot_id)[0]["id"]
    polygon_id = db.save_shade_polygon(source_id, "summer_solstice", "full", '[[0,0],[0,1],[1,1]]')
    db.delete_shade_polygon(polygon_id)
    assert db.list_shade_polygons_for_source(source_id) == []


def test_list_shade_polygons_for_plot_spans_every_source_on_the_plot():
    plot_id = _add_plot()
    db.add_shade_source(plot_id, "Oak tree")
    db.add_shade_source(plot_id, "Barn")
    source_ids = [s["id"] for s in db.list_shade_sources_for_plot(plot_id)]
    for source_id in source_ids:
        db.save_shade_polygon(source_id, "summer_solstice", "full", '[[0,0],[0,1],[1,1]]')
    assert len(db.list_shade_polygons_for_plot(plot_id)) == 2


def test_list_shade_polygons_for_plot_excludes_other_plots_sources():
    db.add_land_plot("Plot A", 40, 60)
    db.add_land_plot("Plot B", 40, 60)
    plots_by_name = {p["name"]: p["id"] for p in db.list_land_plots()}
    plot_a_id, plot_b_id = plots_by_name["Plot A"], plots_by_name["Plot B"]
    db.add_shade_source(plot_a_id, "Oak tree")
    db.add_shade_source(plot_b_id, "Barn")
    source_a_id = db.list_shade_sources_for_plot(plot_a_id)[0]["id"]
    db.save_shade_polygon(source_a_id, "summer_solstice", "full", '[[0,0],[0,1],[1,1]]')
    assert len(db.list_shade_polygons_for_plot(plot_b_id)) == 0


def test_set_quantity_germinated_updates_only_target_planting():
    variety_id = _add_variety()
    planting_id = db.add_planting(variety_id, "2026-05-01")
    other_id = db.add_planting(variety_id, "2026-05-01")
    db.set_quantity_germinated(planting_id, 8)
    assert (db.get_planting(planting_id)["quantity_germinated"], db.get_planting(other_id)["quantity_germinated"]) == (8, None)


def test_set_quantity_germinated_does_not_regenerate_farm_events():
    variety_id = _add_variety(germination_days_min=5, germination_days_max=10)
    planting_id = db.add_planting(variety_id, "2026-05-01")
    event_id_before = db.list_farm_events_in_range(*ALL_TIME)[0]["id"]
    db.set_quantity_germinated(planting_id, 8)
    events_after = db.list_farm_events_in_range(*ALL_TIME)
    assert (len(events_after), events_after[0]["id"]) == (1, event_id_before)


def test_list_plantings_in_group_returns_all_plantings_sharing_variety_and_date():
    variety_id = _add_variety()
    first_id = db.add_planting(variety_id, "2026-05-01")
    second_id = db.add_planting(variety_id, "2026-05-01")
    assert sorted(p["id"] for p in db.list_plantings_in_group(variety_id, "2026-05-01")) == sorted([first_id, second_id])


def test_list_plantings_in_group_excludes_different_planted_date():
    variety_id = _add_variety()
    db.add_planting(variety_id, "2026-05-01")
    db.add_planting(variety_id, "2026-06-01")
    assert len(db.list_plantings_in_group(variety_id, "2026-05-01")) == 1


def _add_planting_for_harvest(**kwargs):
    variety_id = _add_variety()
    return db.add_planting(variety_id, "2026-05-01", **kwargs)


def test_add_harvest_persists_weight_and_date():
    planting_id = _add_planting_for_harvest()
    db.add_harvest(planting_id, "2026-08-01", 3.5)
    harvest = db.list_harvests_for_planting(planting_id)[0]
    assert (harvest["harvest_date"], harvest["weight_lb"]) == ("2026-08-01", 3.5)


def test_add_harvest_persists_notes():
    planting_id = _add_planting_for_harvest()
    db.add_harvest(planting_id, "2026-08-01", 3.5, notes="First picking")
    assert db.list_harvests_for_planting(planting_id)[0]["notes"] == "First picking"


def test_list_harvests_for_planting_orders_by_date_descending():
    planting_id = _add_planting_for_harvest()
    db.add_harvest(planting_id, "2026-08-01", 1.0)
    db.add_harvest(planting_id, "2026-08-15", 2.0)
    assert [h["harvest_date"] for h in db.list_harvests_for_planting(planting_id)] == ["2026-08-15", "2026-08-01"]


def test_list_harvests_for_planting_excludes_other_plantings():
    planting_id = _add_planting_for_harvest()
    other_id = _add_planting_for_harvest()
    db.add_harvest(other_id, "2026-08-01", 1.0)
    assert db.list_harvests_for_planting(planting_id) == []


def test_get_harvest_returns_matching_row():
    planting_id = _add_planting_for_harvest()
    db.add_harvest(planting_id, "2026-08-01", 3.5)
    harvest_id = db.list_harvests_for_planting(planting_id)[0]["id"]
    assert db.get_harvest(harvest_id)["weight_lb"] == 3.5


def test_get_harvest_returns_none_when_not_found():
    assert db.get_harvest(999999) is None


def test_update_harvest_persists_changes():
    planting_id = _add_planting_for_harvest()
    db.add_harvest(planting_id, "2026-08-01", 3.5)
    harvest_id = db.list_harvests_for_planting(planting_id)[0]["id"]
    db.update_harvest(harvest_id, "2026-08-02", 4.5, notes="Corrected")
    harvest = db.get_harvest(harvest_id)
    assert (harvest["harvest_date"], harvest["weight_lb"], harvest["notes"]) == ("2026-08-02", 4.5, "Corrected")


def test_delete_harvest_removes_row():
    planting_id = _add_planting_for_harvest()
    db.add_harvest(planting_id, "2026-08-01", 3.5)
    harvest_id = db.list_harvests_for_planting(planting_id)[0]["id"]
    db.delete_harvest(harvest_id)
    assert db.list_harvests_for_planting(planting_id) == []


def test_delete_nonexistent_harvest_is_a_noop():
    db.delete_harvest(999999)
