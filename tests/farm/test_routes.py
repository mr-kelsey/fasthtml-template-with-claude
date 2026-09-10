import json
from datetime import date

import db


def test_seed_varieties_page_returns_200(client):
    response = client.get("/seed-varieties")
    assert response.status_code == 200


def test_seed_varieties_page_shows_empty_state_when_none_exist(client):
    response = client.get("/seed-varieties")
    assert "No seed varieties yet" in response.text


def test_add_seed_variety_redirects_with_303(client):
    response = client.post(
        "/seed-varieties",
        data={"common_name": "Tomato", "name": "Cherokee Purple", "plant_family": "Solanaceae"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_add_seed_variety_appears_in_list(client):
    client.post(
        "/seed-varieties", data={"common_name": "Tomato", "name": "Cherokee Purple", "plant_family": "Solanaceae"}
    )
    response = client.get("/seed-varieties")
    assert "Cherokee Purple" in response.text


def test_add_seed_variety_rejects_blank_name(client):
    response = client.post(
        "/seed-varieties", data={"common_name": "Tomato", "name": "", "plant_family": "Solanaceae"}
    )
    assert response.status_code == 422


def test_add_seed_variety_rejects_blank_common_name(client):
    response = client.post(
        "/seed-varieties", data={"common_name": "", "name": "Cherokee Purple", "plant_family": "Solanaceae"}
    )
    assert response.status_code == 422


def test_add_seed_variety_rejects_blank_plant_family(client):
    response = client.post(
        "/seed-varieties", data={"common_name": "Tomato", "name": "Cherokee Purple", "plant_family": ""}
    )
    assert response.status_code == 422


def test_add_seed_variety_rejects_non_numeric_agronomic_field(client):
    response = client.post(
        "/seed-varieties",
        data={
            "common_name": "Tomato", "name": "Cherokee Purple", "plant_family": "Solanaceae",
            "spacing_in": "not-a-number",
        },
    )
    assert response.status_code == 422


def test_add_seed_variety_persists_optional_genus_and_species(client):
    client.post(
        "/seed-varieties",
        data={
            "common_name": "Tomato", "name": "Cherokee Purple", "plant_family": "Solanaceae",
            "genus": "Solanum", "species": "lycopersicum",
        },
    )
    response = client.get("/seed-varieties")
    assert "Solanum" in response.text and "lycopersicum" in response.text


def test_add_seed_variety_persists_soil_and_feeding_fields(client):
    client.post(
        "/seed-varieties",
        data={
            "common_name": "Tomato", "name": "Cherokee Purple", "plant_family": "Solanaceae",
            "soil_type": "loam", "soil_ph_min": "6.0", "soil_ph_max": "6.8",
            "feeding_frequency_days": "14", "growth_npk": "10-5-5", "produce_npk": "5-10-10",
        },
    )
    response = client.get("/seed-varieties")
    assert "loam" in response.text and "10-5-5" in response.text and "5-10-10" in response.text


def test_add_seed_variety_rejects_non_numeric_soil_ph(client):
    response = client.post(
        "/seed-varieties",
        data={
            "common_name": "Tomato", "name": "Cherokee Purple", "plant_family": "Solanaceae",
            "soil_ph_min": "not-a-number",
        },
    )
    assert response.status_code == 422


def test_add_seed_variety_rejects_malformed_growth_npk(client):
    response = client.post(
        "/seed-varieties",
        data={
            "common_name": "Tomato", "name": "Cherokee Purple", "plant_family": "Solanaceae",
            "growth_npk": "10-5",
        },
    )
    assert response.status_code == 422


def test_add_seed_variety_rejects_non_numeric_produce_npk(client):
    response = client.post(
        "/seed-varieties",
        data={
            "common_name": "Tomato", "name": "Cherokee Purple", "plant_family": "Solanaceae",
            "produce_npk": "ten-5-5",
        },
    )
    assert response.status_code == 422


def test_add_seed_variety_accepts_valid_sun_needs(client):
    response = client.post(
        "/seed-varieties",
        data={"common_name": "Tomato", "name": "Cherokee Purple", "plant_family": "Solanaceae", "sun_needs": "full_sun"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_add_seed_variety_allows_blank_sun_needs(client):
    response = client.post(
        "/seed-varieties",
        data={"common_name": "Tomato", "name": "Cherokee Purple", "plant_family": "Solanaceae", "sun_needs": ""},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_add_seed_variety_rejects_invalid_sun_needs(client):
    response = client.post(
        "/seed-varieties",
        data={
            "common_name": "Tomato", "name": "Cherokee Purple", "plant_family": "Solanaceae",
            "sun_needs": "kinda-sunny",
        },
    )
    assert response.status_code == 422


def test_edit_seed_variety_page_preselects_current_sun_needs(client):
    client.post(
        "/seed-varieties",
        data={"common_name": "Tomato", "name": "Cherokee Purple", "plant_family": "Solanaceae", "sun_needs": "partial_shade"},
    )
    variety_id = db.list_seed_varieties()[0]["id"]
    response = client.get(f"/seed-varieties/{variety_id}/edit")
    assert '<option value="partial_shade" selected' in response.text


def test_edit_seed_variety_updates_name(client):
    client.post(
        "/seed-varieties", data={"common_name": "Tomato", "name": "Original", "plant_family": "Solanaceae"}
    )
    variety_id = db.list_seed_varieties()[0]["id"]
    client.post(
        f"/seed-varieties/{variety_id}/edit",
        data={"common_name": "Tomato", "name": "Updated", "plant_family": "Solanaceae"},
    )
    assert db.get_seed_variety(variety_id)["name"] == "Updated"


def test_delete_seed_variety_removes_it(client):
    client.post(
        "/seed-varieties", data={"common_name": "Tomato", "name": "To delete", "plant_family": "Solanaceae"}
    )
    variety_id = db.list_seed_varieties()[0]["id"]
    client.post(f"/seed-varieties/{variety_id}/delete")
    assert db.list_seed_varieties() == []


def test_duplicate_seed_variety_page_returns_200(client):
    client.post(
        "/seed-varieties",
        data={
            "common_name": "Tomato", "name": "Cherokee Purple", "plant_family": "Solanaceae",
            "days_to_maturity_min": "60", "days_to_maturity_max": "80",
        },
    )
    variety_id = db.list_seed_varieties()[0]["id"]
    response = client.get(f"/seed-varieties/{variety_id}/duplicate")
    assert response.status_code == 200


def test_duplicate_seed_variety_page_prefills_source_values(client):
    client.post(
        "/seed-varieties",
        data={
            "common_name": "Tomato", "name": "Cherokee Purple", "plant_family": "Solanaceae",
            "days_to_maturity_min": "60", "days_to_maturity_max": "80",
        },
    )
    variety_id = db.list_seed_varieties()[0]["id"]
    response = client.get(f"/seed-varieties/{variety_id}/duplicate")
    assert 'value="Solanaceae"' in response.text


def test_duplicate_seed_variety_page_posts_to_create_not_update(client):
    client.post(
        "/seed-varieties", data={"common_name": "Tomato", "name": "Cherokee Purple", "plant_family": "Solanaceae"}
    )
    variety_id = db.list_seed_varieties()[0]["id"]
    response = client.get(f"/seed-varieties/{variety_id}/duplicate")
    assert 'action="/seed-varieties"' in response.text


def test_duplicate_seed_variety_page_returns_404_when_source_not_found(client):
    response = client.get("/seed-varieties/999999/duplicate")
    assert response.status_code == 404


def test_submitting_duplicated_variety_creates_a_second_row(client):
    client.post(
        "/seed-varieties", data={"common_name": "Tomato", "name": "Cherokee Purple", "plant_family": "Solanaceae"}
    )
    client.post(
        "/seed-varieties", data={"common_name": "Tomato", "name": "Cherokee Purple", "plant_family": "Solanaceae"}
    )
    assert len(db.list_seed_varieties()) == 2


def test_seed_varieties_page_shows_no_companion_rules_yet_when_none_exist(client):
    response = client.get("/seed-varieties")
    assert "No companion/antagonist rules yet" in response.text


def test_add_companion_rule_redirects_with_303(client):
    response = client.post(
        "/companion-rules",
        data={"plant_a_common_name": "Tomato", "plant_b_common_name": "Basil", "relation": "companion"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_add_companion_rule_appears_in_list(client):
    client.post(
        "/companion-rules",
        data={"plant_a_common_name": "Tomato", "plant_b_common_name": "Basil", "relation": "companion"},
    )
    response = client.get("/seed-varieties")
    assert "Tomato" in response.text and "Basil" in response.text


def test_add_companion_rule_persists_notes(client):
    client.post(
        "/companion-rules",
        data={
            "plant_a_common_name": "Tomato", "plant_b_common_name": "Fennel", "relation": "antagonist",
            "notes": "Fennel stunts tomato growth",
        },
    )
    response = client.get("/seed-varieties")
    assert "Fennel stunts tomato growth" in response.text


def test_add_companion_rule_rejects_blank_plant_a_name(client):
    response = client.post(
        "/companion-rules",
        data={"plant_a_common_name": "", "plant_b_common_name": "Basil", "relation": "companion"},
    )
    assert response.status_code == 422


def test_add_companion_rule_rejects_blank_plant_b_name(client):
    response = client.post(
        "/companion-rules",
        data={"plant_a_common_name": "Tomato", "plant_b_common_name": "", "relation": "companion"},
    )
    assert response.status_code == 422


def test_add_companion_rule_rejects_blank_relation(client):
    response = client.post(
        "/companion-rules",
        data={"plant_a_common_name": "Tomato", "plant_b_common_name": "Basil", "relation": ""},
    )
    assert response.status_code == 422


def test_add_companion_rule_rejects_invalid_relation(client):
    response = client.post(
        "/companion-rules",
        data={"plant_a_common_name": "Tomato", "plant_b_common_name": "Basil", "relation": "frenemy"},
    )
    assert response.status_code == 422


def test_delete_companion_rule_removes_it(client):
    client.post(
        "/companion-rules",
        data={"plant_a_common_name": "Tomato", "plant_b_common_name": "Basil", "relation": "companion"},
    )
    rule_id = db.list_companion_rules()[0]["id"]
    client.post(f"/companion-rules/{rule_id}/delete")
    assert db.list_companion_rules() == []


def _create_variety(client, common_name="Tomato", variety_name="Cherokee Purple", plant_family="Solanaceae", **variety_fields):
    client.post(
        "/seed-varieties",
        data={"common_name": common_name, "name": variety_name, "plant_family": plant_family, **variety_fields},
    )
    return db.list_seed_varieties()[0]["id"]


def test_inventory_page_returns_200(client):
    response = client.get("/inventory")
    assert response.status_code == 200


def test_inventory_page_shows_empty_states_when_none_exist(client):
    response = client.get("/inventory")
    assert "No seed lots yet" in response.text
    assert "No transplant lots yet" in response.text


def test_add_seed_lot_redirects_with_303(client):
    variety_id = _create_variety(client)
    response = client.post(
        "/seed-lots", data={"variety_id": str(variety_id), "quantity_on_hand": "50"}, follow_redirects=False
    )
    assert response.status_code == 303


def test_add_seed_lot_appears_in_inventory(client):
    variety_id = _create_variety(client)
    client.post("/seed-lots", data={"variety_id": str(variety_id), "seed_source": "Baker Creek"})
    response = client.get("/inventory")
    assert "Baker Creek" in response.text


def test_add_seed_lot_rejects_invalid_variety(client):
    response = client.post("/seed-lots", data={"variety_id": "999999"})
    assert response.status_code == 422


def test_add_seed_lot_rejects_non_numeric_quantity(client):
    variety_id = _create_variety(client)
    response = client.post("/seed-lots", data={"variety_id": str(variety_id), "quantity_on_hand": "many"})
    assert response.status_code == 422


def test_add_seed_lot_rejects_invalid_acquired_date(client):
    variety_id = _create_variety(client)
    response = client.post("/seed-lots", data={"variety_id": str(variety_id), "acquired_date": "not-a-date"})
    assert response.status_code == 422


def test_edit_seed_lot_page_returns_200(client):
    variety_id = _create_variety(client)
    client.post("/seed-lots", data={"variety_id": str(variety_id)})
    lot_id = db.list_seed_lots()[0]["id"]
    response = client.get(f"/seed-lots/{lot_id}/edit")
    assert response.status_code == 200


def test_edit_seed_lot_page_returns_404_when_not_found(client):
    response = client.get("/seed-lots/999999/edit")
    assert response.status_code == 404


def test_edit_seed_lot_updates_quantity(client):
    variety_id = _create_variety(client)
    client.post("/seed-lots", data={"variety_id": str(variety_id), "quantity_on_hand": "50"})
    lot_id = db.list_seed_lots()[0]["id"]
    client.post(f"/seed-lots/{lot_id}/edit", data={"quantity_on_hand": "30"})
    assert db.get_seed_lot(lot_id)["quantity_on_hand"] == 30


def test_delete_seed_lot_removes_it(client):
    variety_id = _create_variety(client)
    client.post("/seed-lots", data={"variety_id": str(variety_id)})
    lot_id = db.list_seed_lots()[0]["id"]
    client.post(f"/seed-lots/{lot_id}/delete")
    assert db.list_seed_lots() == []


def test_add_transplant_lot_redirects_with_303(client):
    variety_id = _create_variety(client)
    response = client.post(
        "/transplant-lots", data={"variety_id": str(variety_id), "quantity_on_hand": "12"}, follow_redirects=False
    )
    assert response.status_code == 303


def test_add_transplant_lot_appears_in_inventory(client):
    variety_id = _create_variety(client)
    client.post("/transplant-lots", data={"variety_id": str(variety_id), "purchased_vendor": "Local Nursery"})
    response = client.get("/inventory")
    assert "Local Nursery" in response.text


def test_add_transplant_lot_with_origin_planting_persists_it(client):
    variety_id = _create_variety(client)
    client.post("/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-03-01"})
    origin_id = db.list_plantings()[0]["id"]
    client.post("/transplant-lots", data={"variety_id": str(variety_id), "origin_planting_id": str(origin_id)})
    lot = db.list_transplant_lots()[0]
    assert lot["origin_planting_id"] == origin_id


def test_add_transplant_lot_without_origin_planting_defaults_to_none(client):
    variety_id = _create_variety(client)
    client.post("/transplant-lots", data={"variety_id": str(variety_id)})
    assert db.list_transplant_lots()[0]["origin_planting_id"] is None


def test_add_transplant_lot_rejects_invalid_variety(client):
    response = client.post("/transplant-lots", data={"variety_id": "999999"})
    assert response.status_code == 422


def test_add_transplant_lot_rejects_invalid_origin_planting(client):
    variety_id = _create_variety(client)
    response = client.post(
        "/transplant-lots", data={"variety_id": str(variety_id), "origin_planting_id": "999999"}
    )
    assert response.status_code == 422


def test_add_transplant_lot_rejects_invalid_purchased_date(client):
    variety_id = _create_variety(client)
    response = client.post(
        "/transplant-lots", data={"variety_id": str(variety_id), "purchased_date": "not-a-date"}
    )
    assert response.status_code == 422


def test_edit_transplant_lot_page_returns_200(client):
    variety_id = _create_variety(client)
    client.post("/transplant-lots", data={"variety_id": str(variety_id)})
    lot_id = db.list_transplant_lots()[0]["id"]
    response = client.get(f"/transplant-lots/{lot_id}/edit")
    assert response.status_code == 200


def test_edit_transplant_lot_page_returns_404_when_not_found(client):
    response = client.get("/transplant-lots/999999/edit")
    assert response.status_code == 404


def test_edit_transplant_lot_updates_quantity(client):
    variety_id = _create_variety(client)
    client.post("/transplant-lots", data={"variety_id": str(variety_id), "quantity_on_hand": "12"})
    lot_id = db.list_transplant_lots()[0]["id"]
    client.post(f"/transplant-lots/{lot_id}/edit", data={"quantity_on_hand": "8"})
    assert db.get_transplant_lot(lot_id)["quantity_on_hand"] == 8


def test_delete_transplant_lot_removes_it(client):
    variety_id = _create_variety(client)
    client.post("/transplant-lots", data={"variety_id": str(variety_id)})
    lot_id = db.list_transplant_lots()[0]["id"]
    client.post(f"/transplant-lots/{lot_id}/delete")
    assert db.list_transplant_lots() == []


def test_plantings_page_returns_200(client):
    response = client.get("/plantings")
    assert response.status_code == 200


def test_plantings_page_prompts_to_add_a_seed_variety_when_none_exist(client):
    response = client.get("/plantings")
    assert "Add a seed variety" in response.text


def test_add_planting_redirects_with_303(client):
    variety_id = _create_variety(client)
    response = client.post(
        "/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"}, follow_redirects=False
    )
    assert response.status_code == 303


def test_add_planting_appears_in_list(client):
    variety_id = _create_variety(client)
    client.post("/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"})
    response = client.get("/plantings")
    assert "Cherokee Purple" in response.text


def test_add_planting_rejects_unknown_variety_id(client):
    response = client.post("/plantings", data={"variety_id": "999999", "planted_date": "2026-05-01"})
    assert response.status_code == 422


def test_add_planting_rejects_malformed_planted_date(client):
    variety_id = _create_variety(client)
    response = client.post("/plantings", data={"variety_id": str(variety_id), "planted_date": "not-a-date"})
    assert response.status_code == 422


def test_add_planting_rejects_non_numeric_quantity(client):
    variety_id = _create_variety(client)
    response = client.post(
        "/plantings",
        data={"variety_id": str(variety_id), "planted_date": "2026-05-01", "quantity": "not-a-number"},
    )
    assert response.status_code == 422


def test_edit_planting_updates_quantity(client):
    variety_id = _create_variety(client)
    client.post("/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-05-01", "quantity": "10"})
    planting_id = db.list_plantings()[0]["id"]
    client.post(
        f"/plantings/{planting_id}/edit",
        data={"variety_id": str(variety_id), "planted_date": "2026-05-01", "quantity": "20"},
    )
    assert db.get_planting(planting_id)["quantity"] == 20


def test_delete_planting_removes_it(client):
    variety_id = _create_variety(client)
    client.post("/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"})
    planting_id = db.list_plantings()[0]["id"]
    client.post(f"/plantings/{planting_id}/delete")
    assert db.list_plantings() == []


def test_update_planting_rejects_quantity_culled_exceeding_germinated(client):
    variety_id = _create_variety(client)
    client.post(
        "/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-05-01", "quantity_germinated": "5"}
    )
    planting_id = db.list_plantings()[0]["id"]
    response = client.post(
        f"/plantings/{planting_id}/edit",
        data={
            "variety_id": str(variety_id), "planted_date": "2026-05-01",
            "quantity_germinated": "5", "quantity_culled": "9",
        },
    )
    assert response.status_code == 422


def test_edit_planting_page_shows_no_yield_when_no_harvests_logged(client):
    variety_id = _create_variety(client)
    client.post("/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"})
    planting_id = db.list_plantings()[0]["id"]
    response = client.get(f"/plantings/{planting_id}/edit")
    assert "No harvests logged yet." in response.text


def test_post_planting_harvest_route_adds_row(client):
    variety_id = _create_variety(client)
    client.post("/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"})
    planting_id = db.list_plantings()[0]["id"]
    client.post(f"/plantings/{planting_id}/harvests", data={"harvest_date": "2026-08-01", "weight_lb": "3.5"})
    assert len(db.list_harvests_for_planting(planting_id)) == 1


def test_edit_planting_page_shows_yield_per_plant(client):
    variety_id = _create_variety(client)
    client.post(
        "/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-05-01", "quantity_germinated": "10"}
    )
    planting_id = db.list_plantings()[0]["id"]
    client.post(
        f"/plantings/{planting_id}/edit",
        data={
            "variety_id": str(variety_id), "planted_date": "2026-05-01",
            "quantity_germinated": "10", "quantity_culled": "4",
        },
    )
    client.post(f"/plantings/{planting_id}/harvests", data={"harvest_date": "2026-08-01", "weight_lb": "6"})
    response = client.get(f"/plantings/{planting_id}/edit")
    assert "1.00 lb/plant" in response.text


def test_harvest_edit_page_returns_404_when_not_found(client):
    response = client.get("/harvests/999999/edit")
    assert response.status_code == 404


def test_harvest_edit_route_updates_row(client):
    variety_id = _create_variety(client)
    client.post("/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"})
    planting_id = db.list_plantings()[0]["id"]
    client.post(f"/plantings/{planting_id}/harvests", data={"harvest_date": "2026-08-01", "weight_lb": "3.5"})
    harvest_id = db.list_harvests_for_planting(planting_id)[0]["id"]
    client.post(f"/harvests/{harvest_id}/edit", data={"harvest_date": "2026-08-02", "weight_lb": "4.5"})
    assert db.get_harvest(harvest_id)["weight_lb"] == 4.5


def test_harvest_delete_route_removes_row(client):
    variety_id = _create_variety(client)
    client.post("/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"})
    planting_id = db.list_plantings()[0]["id"]
    client.post(f"/plantings/{planting_id}/harvests", data={"harvest_date": "2026-08-01", "weight_lb": "3.5"})
    harvest_id = db.list_harvests_for_planting(planting_id)[0]["id"]
    client.post(f"/harvests/{harvest_id}/delete")
    assert db.list_harvests_for_planting(planting_id) == []


def test_overlapping_plantings_at_same_location_show_warning(client):
    variety_id = _create_variety(client, days_to_maturity_min="60", days_to_maturity_max="70")
    client.post(
        "/plantings",
        data={"variety_id": str(variety_id), "planted_date": "2026-05-01", "location": "Bed 3 row 2"},
    )
    client.post(
        "/plantings",
        data={"variety_id": str(variety_id), "planted_date": "2026-05-05", "location": "Bed 3 row 2"},
    )
    response = client.get("/plantings")
    assert "Overlaps with" in response.text


def test_non_overlapping_plantings_at_same_location_show_no_warning(client):
    variety_id = _create_variety(client, days_to_maturity_min="60", days_to_maturity_max="70")
    client.post(
        "/plantings",
        data={"variety_id": str(variety_id), "planted_date": "2026-05-01", "location": "Bed 3 row 2"},
    )
    client.post(
        "/plantings",
        data={"variety_id": str(variety_id), "planted_date": "2026-09-01", "location": "Bed 3 row 2"},
    )
    response = client.get("/plantings")
    assert "Overlaps with" not in response.text


def test_land_plots_page_returns_200(client):
    response = client.get("/land-plots")
    assert response.status_code == 200


def test_land_plots_page_shows_empty_state_when_none_exist(client):
    response = client.get("/land-plots")
    assert "No land plots yet" in response.text


def test_add_land_plot_redirects_with_303(client):
    response = client.post(
        "/land-plots", data={"name": "Back Field", "width_ft": "40", "length_ft": "60"}, follow_redirects=False
    )
    assert response.status_code == 303


def test_add_land_plot_appears_in_list(client):
    client.post("/land-plots", data={"name": "Back Field", "width_ft": "40", "length_ft": "60"})
    response = client.get("/land-plots")
    assert "Back Field" in response.text


def test_add_land_plot_rejects_blank_name(client):
    response = client.post("/land-plots", data={"name": "", "width_ft": "40", "length_ft": "60"})
    assert response.status_code == 422


def test_add_land_plot_rejects_blank_width(client):
    response = client.post("/land-plots", data={"name": "Back Field", "width_ft": "", "length_ft": "60"})
    assert response.status_code == 422


def test_add_land_plot_rejects_non_numeric_length(client):
    response = client.post(
        "/land-plots", data={"name": "Back Field", "width_ft": "40", "length_ft": "not-a-number"}
    )
    assert response.status_code == 422


def test_add_land_plot_rejects_zero_width(client):
    response = client.post("/land-plots", data={"name": "Back Field", "width_ft": "0", "length_ft": "60"})
    assert response.status_code == 422


def test_add_land_plot_rejects_negative_length(client):
    response = client.post("/land-plots", data={"name": "Back Field", "width_ft": "40", "length_ft": "-1"})
    assert response.status_code == 422


def _create_plot(client, name="Back Field", width_ft="40", length_ft="60"):
    client.post("/land-plots", data={"name": name, "width_ft": width_ft, "length_ft": length_ft})
    return db.list_land_plots()[0]["id"]


def test_edit_land_plot_page_shows_prefilled_name(client):
    plot_id = _create_plot(client)
    response = client.get(f"/land-plots/{plot_id}/edit")
    assert 'value="Back Field"' in response.text


def test_edit_land_plot_updates_dimensions(client):
    plot_id = _create_plot(client)
    client.post(f"/land-plots/{plot_id}/edit", data={"name": "Back Field", "width_ft": "50", "length_ft": "70"})
    plot = db.get_land_plot(plot_id)
    assert (plot["width_ft"], plot["length_ft"]) == (50, 70)


def test_delete_land_plot_removes_it(client):
    plot_id = _create_plot(client)
    client.post(f"/land-plots/{plot_id}/delete")
    assert db.list_land_plots() == []


def test_delete_land_plot_removes_its_beds(client):
    plot_id = _create_plot(client)
    client.post(f"/land-plots/{plot_id}/beds", data={"label": "Bed 1", "width_ft": "4", "length_ft": "8"})
    client.post(f"/land-plots/{plot_id}/delete")
    assert db.list_beds_for_plot(plot_id) == []


def test_land_plot_map_page_returns_200(client):
    plot_id = _create_plot(client)
    response = client.get(f"/land-plots/{plot_id}/map")
    assert response.status_code == 200


def test_land_plot_map_page_shows_plot_name(client):
    plot_id = _create_plot(client)
    response = client.get(f"/land-plots/{plot_id}/map")
    assert "Back Field" in response.text


def test_land_plot_map_page_includes_foot_grid_pattern(client):
    plot_id = _create_plot(client)
    response = client.get(f"/land-plots/{plot_id}/map")
    assert "foot-grid" in response.text


def test_land_plot_map_page_includes_plot_boundary(client):
    plot_id = _create_plot(client)
    response = client.get(f"/land-plots/{plot_id}/map")
    assert "plot-boundary" in response.text


def test_land_plot_map_page_includes_north_compass(client):
    plot_id = _create_plot(client)
    response = client.get(f"/land-plots/{plot_id}/map")
    assert "compass" in response.text


def test_add_bed_redirects_with_303(client):
    plot_id = _create_plot(client)
    response = client.post(
        f"/land-plots/{plot_id}/beds",
        data={"label": "Bed 1", "width_ft": "4", "length_ft": "8"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_add_bed_starts_unplaced_on_map_page(client):
    plot_id = _create_plot(client)
    client.post(f"/land-plots/{plot_id}/beds", data={"label": "Bed 1", "width_ft": "4", "length_ft": "8"})
    response = client.get(f"/land-plots/{plot_id}/map")
    assert "Bed 1" in response.text


def test_unplaced_bed_links_to_its_detail_page(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    response = client.get(f"/land-plots/{plot_id}/map")
    assert f'href="/beds/{bed_id}"' in response.text


def test_placed_bed_on_map_links_to_its_detail_page(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    client.post(f"/beds/{bed_id}/position", data={"x": "0", "y": "0"})
    response = client.get(f"/land-plots/{plot_id}/map")
    assert f"/beds/{bed_id}" in response.text


def test_add_bed_rejects_blank_label(client):
    plot_id = _create_plot(client)
    response = client.post(f"/land-plots/{plot_id}/beds", data={"label": "", "width_ft": "4", "length_ft": "8"})
    assert response.status_code == 422


def test_add_bed_rejects_non_numeric_width(client):
    plot_id = _create_plot(client)
    response = client.post(
        f"/land-plots/{plot_id}/beds", data={"label": "Bed 1", "width_ft": "not-a-number", "length_ft": "8"}
    )
    assert response.status_code == 422


def test_add_bed_rejects_zero_width(client):
    plot_id = _create_plot(client)
    response = client.post(
        f"/land-plots/{plot_id}/beds", data={"label": "Bed 1", "width_ft": "0", "length_ft": "8"}
    )
    assert response.status_code == 422


def _create_bed(client, plot_id, label="Bed 1", width_ft="4", length_ft="8"):
    client.post(f"/land-plots/{plot_id}/beds", data={"label": label, "width_ft": width_ft, "length_ft": length_ft})
    return db.list_beds_for_plot(plot_id)[0]["id"]


def test_bed_label_shows_at_readable_size_for_a_normal_bed(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id, label="Bed 1", width_ft="8", length_ft="8")
    client.post(f"/beds/{bed_id}/position", data={"x": "0", "y": "0"})
    response = client.get(f"/land-plots/{plot_id}/map")
    assert 'font-size="0.5"' in response.text


def test_bed_label_hides_when_label_too_long_to_fit(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id, label="A Very Long Bed Label Indeed", width_ft="1", length_ft="1")
    client.post(f"/beds/{bed_id}/position", data={"x": "0", "y": "0"})
    response = client.get(f"/land-plots/{plot_id}/map")
    assert "display:none" in response.text


def test_place_bed_route_places_unplaced_bed_at_origin(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    client.post(f"/beds/{bed_id}/place")
    bed = db.get_bed(bed_id)
    assert (bed["x"], bed["y"]) == (0, 0)


def test_place_bed_route_offsets_second_bed_from_the_first(client):
    plot_id = _create_plot(client)
    bed_a_id = _create_bed(client, plot_id, label="Bed A")
    bed_b_id = _create_bed(client, plot_id, label="Bed B")
    client.post(f"/beds/{bed_a_id}/place")
    client.post(f"/beds/{bed_b_id}/place")
    bed_b = db.get_bed(bed_b_id)
    assert (bed_b["x"], bed_b["y"]) != (0, 0)


def test_place_bed_route_returns_404_when_bed_not_found(client):
    response = client.post("/beds/999/place")
    assert response.status_code == 404


def test_update_bed_position_returns_204(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    response = client.post(f"/beds/{bed_id}/position", data={"x": "5", "y": "6"})
    assert response.status_code == 204


def test_update_bed_position_persists(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    client.post(f"/beds/{bed_id}/position", data={"x": "5", "y": "6"})
    bed = db.get_bed(bed_id)
    assert (bed["x"], bed["y"]) == (5, 6)


def test_update_bed_position_rejects_non_numeric_x(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    response = client.post(f"/beds/{bed_id}/position", data={"x": "not-a-number", "y": "6"})
    assert response.status_code == 422


def test_update_bed_size_returns_204(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    response = client.post(f"/beds/{bed_id}/size", data={"width_ft": "6", "length_ft": "10"})
    assert response.status_code == 204


def test_update_bed_size_persists(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    client.post(f"/beds/{bed_id}/size", data={"width_ft": "6", "length_ft": "10"})
    bed = db.get_bed(bed_id)
    assert (bed["width_ft"], bed["length_ft"]) == (6, 10)


def test_update_bed_position_returns_404_when_bed_not_found(client):
    response = client.post("/beds/999/position", data={"x": "5", "y": "6"})
    assert response.status_code == 404


def test_update_bed_position_clamps_x_to_plot_width(client):
    plot_id = _create_plot(client, width_ft="40", length_ft="60")
    bed_id = _create_bed(client, plot_id, width_ft="4", length_ft="8")
    client.post(f"/beds/{bed_id}/position", data={"x": "1000", "y": "6"})
    bed = db.get_bed(bed_id)
    assert bed["x"] == 36


def test_update_bed_position_clamps_negative_y_to_zero(client):
    plot_id = _create_plot(client, width_ft="40", length_ft="60")
    bed_id = _create_bed(client, plot_id, width_ft="4", length_ft="8")
    client.post(f"/beds/{bed_id}/position", data={"x": "5", "y": "-1000"})
    bed = db.get_bed(bed_id)
    assert bed["y"] == 0


def test_update_bed_size_returns_404_when_bed_not_found(client):
    response = client.post("/beds/999/size", data={"width_ft": "6", "length_ft": "10"})
    assert response.status_code == 404


def test_update_bed_size_clamps_width_to_remaining_plot_space(client):
    plot_id = _create_plot(client, width_ft="40", length_ft="60")
    bed_id = _create_bed(client, plot_id, width_ft="4", length_ft="8")
    client.post(f"/beds/{bed_id}/position", data={"x": "30", "y": "0"})
    client.post(f"/beds/{bed_id}/size", data={"width_ft": "1000", "length_ft": "10"})
    bed = db.get_bed(bed_id)
    assert bed["width_ft"] == 10


def test_bed_edit_fragment_shows_prefilled_label(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    response = client.get(f"/beds/{bed_id}/edit-fragment")
    assert 'value="Bed 1"' in response.text


def test_edit_bed_updates_label(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    client.post(
        f"/beds/{bed_id}/edit",
        data={"label": "Updated Bed", "width_ft": "4", "length_ft": "8", "rotation_deg": "0"},
    )
    assert db.get_bed(bed_id)["label"] == "Updated Bed"


def test_edit_bed_redirects_to_bed_detail(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    response = client.post(
        f"/beds/{bed_id}/edit",
        data={"label": "Bed 1", "width_ft": "4", "length_ft": "8", "rotation_deg": "0"},
        follow_redirects=False,
    )
    assert response.headers["location"] == f"/beds/{bed_id}"


def test_edit_bed_rejects_rotation_above_359(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    response = client.post(
        f"/beds/{bed_id}/edit",
        data={"label": "Bed 1", "width_ft": "4", "length_ft": "8", "rotation_deg": "360"},
    )
    assert response.status_code == 422


def test_edit_bed_rejects_negative_rotation(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    response = client.post(
        f"/beds/{bed_id}/edit",
        data={"label": "Bed 1", "width_ft": "4", "length_ft": "8", "rotation_deg": "-1"},
    )
    assert response.status_code == 422


def test_delete_bed_removes_it(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    client.post(f"/beds/{bed_id}/delete")
    assert db.list_beds_for_plot(plot_id) == []


def test_delete_bed_redirects_to_plot_map(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    response = client.post(f"/beds/{bed_id}/delete", follow_redirects=False)
    assert response.headers["location"] == f"/land-plots/{plot_id}/map"


def test_bed_detail_page_returns_200(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    response = client.get(f"/beds/{bed_id}")
    assert response.status_code == 200


def test_bed_detail_page_returns_404_when_not_found(client):
    response = client.get("/beds/999999")
    assert response.status_code == 404


def test_bed_detail_page_shows_bed_label(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id, label="Tomato Bed")
    response = client.get(f"/beds/{bed_id}")
    assert "Tomato Bed" in response.text


def _stage_batch(client, bed_id, variety_id, points, source_type="seed", planted_date="2026-05-01", follow_redirects=True, **extra):
    return client.post(
        f"/beds/{bed_id}/cells/batch",
        data={
            "variety_id": str(variety_id),
            "source_type": source_type,
            "planted_date": planted_date,
            "points": json.dumps([{"x_in": x, "y_in": y} for x, y in points]),
            **extra,
        },
        follow_redirects=follow_redirects,
    )


def test_bed_detail_page_shows_seed_stock_variety_in_seed_palette(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_id = _create_variety(client)
    client.post("/seed-lots", data={"variety_id": str(variety_id)})
    response = client.get(f"/beds/{bed_id}")
    assert "Cherokee Purple" in response.text


def test_bed_detail_page_omits_variety_with_no_stock(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    _create_variety(client)
    response = client.get(f"/beds/{bed_id}")
    assert "No varieties with seed stock on hand" in response.text


def test_bed_detail_page_omits_transplant_variety_with_zero_quantity(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_id = _create_variety(client)
    client.post("/transplant-lots", data={"variety_id": str(variety_id), "quantity_on_hand": "0"})
    response = client.get(f"/beds/{bed_id}")
    assert "No varieties with transplant stock on hand" in response.text


def test_batch_plant_redirects_with_303(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_id = _create_variety(client)
    client.post("/seed-lots", data={"variety_id": str(variety_id)})
    response = _stage_batch(client, bed_id, variety_id, [(0, 0), (16, 0)], follow_redirects=False)
    assert response.status_code == 303


def test_batch_plant_persists_one_planting_per_point(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_id = _create_variety(client)
    client.post("/seed-lots", data={"variety_id": str(variety_id)})
    _stage_batch(client, bed_id, variety_id, [(0, 0), (16, 0), (32, 0)])
    assert len(db.list_plantings_for_bed(bed_id)) == 3


def test_batch_plant_persists_submitted_positions(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_id = _create_variety(client)
    client.post("/seed-lots", data={"variety_id": str(variety_id)})
    _stage_batch(client, bed_id, variety_id, [(16, 24)])
    planting = db.list_plantings_for_bed(bed_id)[0]
    assert (planting["x_in"], planting["y_in"]) == (16, 24)


def test_batch_plant_rejects_point_outside_bed(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id, width_ft="4", length_ft="8")
    variety_id = _create_variety(client)
    client.post("/seed-lots", data={"variety_id": str(variety_id)})
    response = _stage_batch(client, bed_id, variety_id, [(1000, 0)])
    assert response.status_code == 422


def test_batch_plant_rejects_unknown_variety(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    response = _stage_batch(client, bed_id, 999999, [(0, 0)])
    assert response.status_code == 422


def test_batch_plant_rejects_seed_mode_variety_with_no_seed_lot(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_id = _create_variety(client)
    response = _stage_batch(client, bed_id, variety_id, [(0, 0)])
    assert response.status_code == 422


def test_batch_plant_returns_404_when_bed_not_found(client):
    variety_id = _create_variety(client)
    response = _stage_batch(client, 999999, variety_id, [(0, 0)])
    assert response.status_code == 404


def test_batch_plant_transplant_mode_rejects_count_exceeding_lot_quantity(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_id = _create_variety(client)
    client.post("/transplant-lots", data={"variety_id": str(variety_id), "quantity_on_hand": "1"})
    lot_id = db.list_transplant_lots()[0]["id"]
    response = _stage_batch(
        client, bed_id, variety_id, [(0, 0), (16, 0)], source_type="transplant", transplant_lot_id=str(lot_id)
    )
    assert response.status_code == 422


def test_batch_plant_transplant_mode_decrements_lot(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_id = _create_variety(client)
    client.post("/transplant-lots", data={"variety_id": str(variety_id), "quantity_on_hand": "5"})
    lot_id = db.list_transplant_lots()[0]["id"]
    _stage_batch(
        client, bed_id, variety_id, [(0, 0), (16, 0)], source_type="transplant", transplant_lot_id=str(lot_id)
    )
    assert db.get_transplant_lot(lot_id)["quantity_on_hand"] == 3


def test_batch_plant_transplant_mode_records_source_type(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_id = _create_variety(client)
    client.post("/transplant-lots", data={"variety_id": str(variety_id), "quantity_on_hand": "5"})
    lot_id = db.list_transplant_lots()[0]["id"]
    _stage_batch(client, bed_id, variety_id, [(0, 0)], source_type="transplant", transplant_lot_id=str(lot_id))
    assert db.list_plantings_for_bed(bed_id)[0]["source_type"] == "transplant"


def test_batch_plant_transplant_mode_rejects_missing_lot(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_id = _create_variety(client)
    response = _stage_batch(client, bed_id, variety_id, [(0, 0)], source_type="transplant")
    assert response.status_code == 422


def test_update_transplant_lot_quantity_route_returns_204(client):
    variety_id = _create_variety(client)
    client.post("/transplant-lots", data={"variety_id": str(variety_id), "quantity_on_hand": "5"})
    lot_id = db.list_transplant_lots()[0]["id"]
    response = client.post(f"/transplant-lots/{lot_id}/quantity", data={"quantity_on_hand": "2"})
    assert response.status_code == 204


def test_update_transplant_lot_quantity_route_persists_new_quantity(client):
    variety_id = _create_variety(client)
    client.post("/transplant-lots", data={"variety_id": str(variety_id), "quantity_on_hand": "5"})
    lot_id = db.list_transplant_lots()[0]["id"]
    client.post(f"/transplant-lots/{lot_id}/quantity", data={"quantity_on_hand": "2"})
    assert db.get_transplant_lot(lot_id)["quantity_on_hand"] == 2


def test_update_transplant_lot_quantity_route_returns_404_when_not_found(client):
    response = client.post("/transplant-lots/999999/quantity", data={"quantity_on_hand": "2"})
    assert response.status_code == 404


def test_update_transplant_lot_quantity_route_rejects_negative_quantity(client):
    variety_id = _create_variety(client)
    client.post("/transplant-lots", data={"variety_id": str(variety_id), "quantity_on_hand": "5"})
    lot_id = db.list_transplant_lots()[0]["id"]
    response = client.post(f"/transplant-lots/{lot_id}/quantity", data={"quantity_on_hand": "-1"})
    assert response.status_code == 422


def test_transplant_lot_plantings_page_returns_200(client):
    variety_id = _create_variety(client)
    client.post("/transplant-lots", data={"variety_id": str(variety_id)})
    lot_id = db.list_transplant_lots()[0]["id"]
    response = client.get(f"/transplant-lots/{lot_id}/plantings")
    assert response.status_code == 200


def test_transplant_lot_plantings_page_returns_404_when_not_found(client):
    response = client.get("/transplant-lots/999999/plantings")
    assert response.status_code == 404


def test_transplant_lot_plantings_page_lists_plantings_drawn_from_it(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_id = _create_variety(client)
    client.post("/transplant-lots", data={"variety_id": str(variety_id), "quantity_on_hand": "5"})
    lot_id = db.list_transplant_lots()[0]["id"]
    _stage_batch(client, bed_id, variety_id, [(0, 0)], source_type="transplant", transplant_lot_id=str(lot_id))
    response = client.get(f"/transplant-lots/{lot_id}/plantings")
    assert "2026-05-01" in response.text


def test_planting_lineage_page_returns_404_when_not_found(client):
    response = client.get("/plantings/999999/lineage")
    assert response.status_code == 404


def test_planting_lineage_page_shows_no_lineage_for_seed_grown_planting(client):
    variety_id = _create_variety(client)
    client.post("/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"})
    planting_id = db.list_plantings()[0]["id"]
    response = client.get(f"/plantings/{planting_id}/lineage")
    assert "no transplant lineage" in response.text


def test_planting_lineage_page_shows_self_grown_origin(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_id = _create_variety(client)
    client.post("/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-03-01"})
    origin_id = db.list_plantings()[0]["id"]
    client.post(
        "/transplant-lots",
        data={"variety_id": str(variety_id), "quantity_on_hand": "5", "origin_planting_id": str(origin_id)},
    )
    lot_id = db.list_transplant_lots()[0]["id"]
    _stage_batch(client, bed_id, variety_id, [(0, 0)], source_type="transplant", transplant_lot_id=str(lot_id))
    planting_id = db.list_plantings_for_bed(bed_id)[0]["id"]
    response = client.get(f"/plantings/{planting_id}/lineage")
    assert "Self-grown from" in response.text


def test_planting_lineage_page_shows_purchased_source(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_id = _create_variety(client)
    client.post(
        "/transplant-lots",
        data={"variety_id": str(variety_id), "quantity_on_hand": "5", "purchased_vendor": "Local Nursery"},
    )
    lot_id = db.list_transplant_lots()[0]["id"]
    _stage_batch(client, bed_id, variety_id, [(0, 0)], source_type="transplant", transplant_lot_id=str(lot_id))
    planting_id = db.list_plantings_for_bed(bed_id)[0]["id"]
    response = client.get(f"/plantings/{planting_id}/lineage")
    assert "Local Nursery" in response.text


def _farm_calendar_url(year, month):
    return f"/farm-calendar?year={year}&month={month}"


def test_farm_calendar_page_returns_200(client):
    response = client.get("/farm-calendar")
    assert response.status_code == 200


def test_farm_calendar_page_shows_weekday_headers(client):
    response = client.get("/farm-calendar")
    assert "Sun" in response.text


def test_add_custom_farm_event_appears_on_calendar_grid(client):
    client.post("/farm-calendar", data={"title": "Check frost cloth", "event_type": "custom", "start_date": "2026-09-10"})
    response = client.get(_farm_calendar_url(2026, 9))
    assert "Check frost cloth" in response.text


def test_farm_calendar_day_fragment_lists_events_for_that_day(client):
    client.post("/farm-calendar", data={"title": "Check frost cloth", "event_type": "custom", "start_date": "2026-09-10"})
    response = client.get("/farm-calendar/day/2026-09-10")
    assert "Check frost cloth" in response.text


def test_generated_farm_event_appears_on_calendar_grid(client):
    variety_id = _create_variety(client, days_to_maturity_min="60", days_to_maturity_max="70")
    client.post("/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"})
    event = db.list_farm_events_in_range("2000-01-01", "2100-01-01")[0]
    event_date = date.fromisoformat(event["start_date"])
    response = client.get(_farm_calendar_url(event_date.year, event_date.month))
    assert "Cherokee Purple" in response.text


def test_delete_custom_farm_event_removes_it(client):
    client.post("/farm-calendar", data={"title": "To delete", "event_type": "custom", "start_date": "2026-09-10"})
    event_id = db.list_farm_events_in_range("2000-01-01", "2100-01-01")[0]["id"]
    client.post(f"/farm-calendar/{event_id}/delete")
    assert db.list_farm_events_in_range("2000-01-01", "2100-01-01") == []


def test_delete_linked_farm_event_is_forbidden(client):
    variety_id = _create_variety(client, days_to_maturity_min="60", days_to_maturity_max="70")
    client.post("/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"})
    event_id = db.list_farm_events_in_range("2000-01-01", "2100-01-01")[0]["id"]
    response = client.post(f"/farm-calendar/{event_id}/delete")
    assert response.status_code == 403


def test_delete_linked_farm_event_does_not_remove_it(client):
    variety_id = _create_variety(client, days_to_maturity_min="60", days_to_maturity_max="70")
    client.post("/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"})
    event_id = db.list_farm_events_in_range("2000-01-01", "2100-01-01")[0]["id"]
    client.post(f"/farm-calendar/{event_id}/delete")
    assert db.get_farm_event(event_id) is not None


def test_add_custom_farm_event_rejects_blank_title(client):
    response = client.post("/farm-calendar", data={"title": "", "event_type": "custom", "start_date": "2026-09-10"})
    assert response.status_code == 422


def test_farm_calendar_day_fragment_shows_record_link_for_germination_check_event(client):
    variety_id = _create_variety(client, germination_days_min="5", germination_days_max="10")
    client.post("/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"})
    event = db.list_farm_events_in_range("2000-01-01", "2100-01-01")[0]
    response = client.get(f"/farm-calendar/day/{event['start_date']}")
    assert "Record" in response.text


def test_farm_calendar_day_fragment_shows_record_link_for_harvest_event(client):
    variety_id = _create_variety(client, days_to_maturity_min="60", days_to_maturity_max="70")
    client.post("/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"})
    event = db.list_farm_events_in_range("2000-01-01", "2100-01-01")[0]
    response = client.get(f"/farm-calendar/day/{event['start_date']}")
    assert "Record" in response.text


def test_farm_calendar_day_fragment_shows_no_record_link_for_custom_event(client):
    client.post("/farm-calendar", data={"title": "Check frost cloth", "event_type": "custom", "start_date": "2026-09-10"})
    response = client.get("/farm-calendar/day/2026-09-10")
    assert "Record" not in response.text


def test_record_route_404s_for_custom_event_type(client):
    client.post("/farm-calendar", data={"title": "Check frost cloth", "event_type": "custom", "start_date": "2026-09-10"})
    event_id = db.list_farm_events_in_range("2000-01-01", "2100-01-01")[0]["id"]
    response = client.get(f"/farm-calendar/{event_id}/record")
    assert response.status_code == 404


def test_record_germination_page_lists_every_planting_in_group(client):
    variety_id = _create_variety(client, germination_days_min="5", germination_days_max="10")
    client.post("/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-05-01", "location": "Row A"})
    client.post("/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-05-01", "location": "Row B"})
    event = db.list_farm_events_in_range("2000-01-01", "2100-01-01")[0]
    response = client.get(f"/farm-calendar/{event['id']}/record")
    assert "Row A" in response.text and "Row B" in response.text


def test_post_record_germination_updates_target_planting_quantity(client):
    variety_id = _create_variety(client, germination_days_min="5", germination_days_max="10")
    client.post("/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"})
    planting_id = db.list_plantings()[0]["id"]
    event_id = db.list_farm_events_in_range("2000-01-01", "2100-01-01")[0]["id"]
    client.post(f"/farm-calendar/{event_id}/record/germination/{planting_id}", data={"quantity_germinated": "8"})
    assert db.get_planting(planting_id)["quantity_germinated"] == 8


def test_post_record_germination_leaves_calendar_event_count_unchanged(client):
    variety_id = _create_variety(client, germination_days_min="5", germination_days_max="10")
    client.post("/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"})
    planting_id = db.list_plantings()[0]["id"]
    event_id = db.list_farm_events_in_range("2000-01-01", "2100-01-01")[0]["id"]
    client.post(f"/farm-calendar/{event_id}/record/germination/{planting_id}", data={"quantity_germinated": "8"})
    assert len(db.list_farm_events_in_range("2000-01-01", "2100-01-01")) == 1


def test_record_harvest_page_shows_existing_harvest_history(client):
    variety_id = _create_variety(client, days_to_maturity_min="60", days_to_maturity_max="70")
    client.post("/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"})
    planting_id = db.list_plantings()[0]["id"]
    db.add_harvest(planting_id, "2026-08-01", 3.5)
    event = db.list_farm_events_in_range("2000-01-01", "2100-01-01")[0]
    response = client.get(f"/farm-calendar/{event['id']}/record")
    assert "3.5 lb" in response.text


def test_post_record_harvest_route_appends_new_row_on_repeat_submit(client):
    variety_id = _create_variety(client, days_to_maturity_min="60", days_to_maturity_max="70")
    client.post("/plantings", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"})
    planting_id = db.list_plantings()[0]["id"]
    event_id = db.list_farm_events_in_range("2000-01-01", "2100-01-01")[0]["id"]
    client.post(f"/farm-calendar/{event_id}/record/harvest", data={"harvest_date": "2026-08-01", "weight_lb": "2.0"})
    client.post(f"/farm-calendar/{event_id}/record/harvest", data={"harvest_date": "2026-08-15", "weight_lb": "3.0"})
    assert len(db.list_harvests_for_planting(planting_id)) == 2


def _create_garden_product(client, name="Fish Emulsion", **fields):
    client.post("/garden-products", data={"name": name, **fields})
    return db.list_garden_products()[0]["id"]


def test_products_page_returns_200(client):
    response = client.get("/products")
    assert response.status_code == 200


def test_products_page_shows_empty_states_when_none_exist(client):
    response = client.get("/products")
    assert "No garden products yet" in response.text
    assert "No product applications yet" in response.text


def test_add_garden_product_redirects_with_303(client):
    response = client.post("/garden-products", data={"name": "Fish Emulsion"}, follow_redirects=False)
    assert response.status_code == 303


def test_add_garden_product_appears_in_list(client):
    client.post("/garden-products", data={"name": "Fish Emulsion", "product_type": "fertilizer"})
    response = client.get("/products")
    assert "Fish Emulsion" in response.text


def test_add_garden_product_rejects_blank_name(client):
    response = client.post("/garden-products", data={"name": ""})
    assert response.status_code == 422


def test_add_garden_product_rejects_malformed_npk(client):
    response = client.post("/garden-products", data={"name": "Fish Emulsion", "npk": "not-a-formula"})
    assert response.status_code == 422


def test_add_garden_product_rejects_non_numeric_application_frequency(client):
    response = client.post(
        "/garden-products", data={"name": "Fish Emulsion", "application_frequency_days": "often"}
    )
    assert response.status_code == 422


def test_edit_garden_product_page_returns_200(client):
    product_id = _create_garden_product(client)
    response = client.get(f"/garden-products/{product_id}/edit")
    assert response.status_code == 200


def test_edit_garden_product_page_returns_404_when_not_found(client):
    response = client.get("/garden-products/999999/edit")
    assert response.status_code == 404


def test_edit_garden_product_updates_application_frequency(client):
    product_id = _create_garden_product(client)
    client.post(f"/garden-products/{product_id}/edit", data={"name": "Fish Emulsion", "application_frequency_days": "21"})
    assert db.get_garden_product(product_id)["application_frequency_days"] == 21


def test_delete_garden_product_removes_it(client):
    product_id = _create_garden_product(client)
    client.post(f"/garden-products/{product_id}/delete")
    assert db.list_garden_products() == []


def test_add_product_application_redirects_with_303(client):
    product_id = _create_garden_product(client)
    response = client.post(
        "/product-applications",
        data={"product_id": str(product_id), "applied_date": "2026-05-01", "location": "North fence row"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_add_product_application_appears_in_list(client):
    product_id = _create_garden_product(client)
    client.post(
        "/product-applications",
        data={"product_id": str(product_id), "applied_date": "2026-05-01", "location": "North fence row"},
    )
    response = client.get("/products")
    assert "North fence row" in response.text


def test_add_product_application_with_bed_id_ignores_location_text(client):
    product_id = _create_garden_product(client)
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id, label="Tomato Bed")
    client.post(
        "/product-applications",
        data={
            "product_id": str(product_id), "applied_date": "2026-05-01", "bed_id": str(bed_id),
            "location": "Should be ignored",
        },
    )
    application = db.list_product_applications()[0]
    assert (application["bed_id"], application["location"]) == (bed_id, None)


def test_add_product_application_rejects_invalid_product(client):
    response = client.post(
        "/product-applications", data={"product_id": "999999", "applied_date": "2026-05-01"}
    )
    assert response.status_code == 422


def test_add_product_application_rejects_blank_applied_date(client):
    product_id = _create_garden_product(client)
    response = client.post("/product-applications", data={"product_id": str(product_id), "applied_date": ""})
    assert response.status_code == 422


def test_delete_product_application_removes_it(client):
    product_id = _create_garden_product(client)
    client.post(
        "/product-applications", data={"product_id": str(product_id), "applied_date": "2026-05-01"}
    )
    application_id = db.list_product_applications()[0]["id"]
    client.post(f"/product-applications/{application_id}/delete")
    assert db.list_product_applications() == []


def test_product_reminder_event_appears_on_calendar_grid(client):
    product_id = _create_garden_product(client, application_frequency_days="14")
    client.post(
        "/product-applications",
        data={"product_id": str(product_id), "applied_date": "2026-05-01", "location": "North fence row"},
    )
    reminder = db.list_farm_events_in_range("2000-01-01", "2100-01-01")[0]
    reminder_date = date.fromisoformat(reminder["start_date"])
    response = client.get(_farm_calendar_url(reminder_date.year, reminder_date.month))
    assert "Fish Emulsion" in response.text


def test_delete_product_reminder_event_is_forbidden(client):
    product_id = _create_garden_product(client, application_frequency_days="14")
    client.post(
        "/product-applications",
        data={"product_id": str(product_id), "applied_date": "2026-05-01", "location": "North fence row"},
    )
    event_id = db.list_farm_events_in_range("2000-01-01", "2100-01-01")[0]["id"]
    response = client.post(f"/farm-calendar/{event_id}/delete")
    assert response.status_code == 403
