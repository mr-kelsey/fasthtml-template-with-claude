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


def test_bed_detail_page_renders_one_cell_per_square_foot(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id, width_ft="2", length_ft="3")
    response = client.get(f"/beds/{bed_id}")
    assert response.text.count("bed-cell") == 6


def test_assign_cell_redirects_with_303(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_id = _create_variety(client)
    response = client.post(
        f"/beds/{bed_id}/cells/0/0",
        data={"variety_id": str(variety_id), "planted_date": "2026-05-01"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_assign_cell_persists_planting_at_that_cell(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_id = _create_variety(client)
    client.post(f"/beds/{bed_id}/cells/1/2", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"})
    assert db.list_plantings_at_cell(bed_id, 1, 2)[0]["variety_id"] == variety_id


def test_assign_cell_shows_variety_on_bed_detail_page(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_id = _create_variety(client)
    client.post(f"/beds/{bed_id}/cells/0/0", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"})
    response = client.get(f"/beds/{bed_id}")
    assert "Cherokee Purple" in response.text


def test_assign_cell_rejects_unknown_variety(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    response = client.post(f"/beds/{bed_id}/cells/0/0", data={"variety_id": "999999", "planted_date": "2026-05-01"})
    assert response.status_code == 422


def test_assign_cell_rejects_malformed_planted_date(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_id = _create_variety(client)
    response = client.post(
        f"/beds/{bed_id}/cells/0/0", data={"variety_id": str(variety_id), "planted_date": "not-a-date"}
    )
    assert response.status_code == 422


def test_assign_cell_rejects_coordinate_outside_bed(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id, width_ft="4", length_ft="8")
    variety_id = _create_variety(client)
    response = client.post(
        f"/beds/{bed_id}/cells/10/0", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"}
    )
    assert response.status_code == 422


def test_assign_cell_returns_404_when_bed_not_found(client):
    variety_id = _create_variety(client)
    response = client.post(
        "/beds/999999/cells/0/0", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"}
    )
    assert response.status_code == 404


def test_assigning_a_second_variety_to_an_occupied_cell_keeps_both(client):
    "Interplanting -- a cell can hold more than one type of plant."
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_a = _create_variety(client, common_name="Tomato", variety_name="Cherokee Purple")
    variety_b = _create_variety(client, common_name="Carrot", variety_name="Danvers")
    client.post(f"/beds/{bed_id}/cells/0/0", data={"variety_id": str(variety_a), "planted_date": "2026-05-01"})
    client.post(f"/beds/{bed_id}/cells/0/0", data={"variety_id": str(variety_b), "planted_date": "2026-05-01"})
    assert len(db.list_plantings_at_cell(bed_id, 0, 0)) == 2


def test_bed_detail_page_shows_both_interplanted_varieties(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_a = _create_variety(client, common_name="Tomato", variety_name="Cherokee Purple")
    variety_b = _create_variety(client, common_name="Carrot", variety_name="Danvers")
    client.post(f"/beds/{bed_id}/cells/0/0", data={"variety_id": str(variety_a), "planted_date": "2026-05-01"})
    client.post(f"/beds/{bed_id}/cells/0/0", data={"variety_id": str(variety_b), "planted_date": "2026-05-01"})
    response = client.get(f"/beds/{bed_id}")
    assert "Cherokee Purple" in response.text and "Danvers" in response.text


def test_clear_cell_removes_the_planting(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_id = _create_variety(client)
    client.post(f"/beds/{bed_id}/cells/0/0", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"})
    client.post(f"/beds/{bed_id}/cells/0/0/clear")
    assert db.list_plantings_at_cell(bed_id, 0, 0) == []


def test_clear_cell_removes_every_interplanted_variety(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_a = _create_variety(client, common_name="Tomato", variety_name="Cherokee Purple")
    variety_b = _create_variety(client, common_name="Carrot", variety_name="Danvers")
    client.post(f"/beds/{bed_id}/cells/0/0", data={"variety_id": str(variety_a), "planted_date": "2026-05-01"})
    client.post(f"/beds/{bed_id}/cells/0/0", data={"variety_id": str(variety_b), "planted_date": "2026-05-01"})
    client.post(f"/beds/{bed_id}/cells/0/0/clear")
    assert db.list_plantings_at_cell(bed_id, 0, 0) == []


def test_clear_empty_cell_is_a_noop(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    response = client.post(f"/beds/{bed_id}/cells/0/0/clear")
    assert response.status_code == 200


def test_cell_edit_fragment_lists_existing_planting_for_occupied_cell(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_id = _create_variety(client)
    client.post(f"/beds/{bed_id}/cells/0/0", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"})
    response = client.get(f"/beds/{bed_id}/cells/0/0/edit-fragment")
    assert "Cherokee Purple" in response.text


def test_cell_edit_fragment_returns_200_for_empty_cell(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    response = client.get(f"/beds/{bed_id}/cells/0/0/edit-fragment")
    assert response.status_code == 200


def test_editing_bed_scoped_planting_redirects_to_bed_detail(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_id = _create_variety(client)
    client.post(f"/beds/{bed_id}/cells/0/0", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"})
    planting_id = db.list_plantings_at_cell(bed_id, 0, 0)[0]["id"]
    response = client.post(
        f"/plantings/{planting_id}/edit",
        data={"variety_id": str(variety_id), "planted_date": "2026-05-01"},
        follow_redirects=False,
    )
    assert response.headers["location"] == f"/beds/{bed_id}"


def test_editing_bed_scoped_planting_keeps_its_cell(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_id = _create_variety(client)
    client.post(f"/beds/{bed_id}/cells/1/2", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"})
    planting_id = db.list_plantings_at_cell(bed_id, 1, 2)[0]["id"]
    client.post(f"/plantings/{planting_id}/edit", data={"variety_id": str(variety_id), "planted_date": "2026-06-01"})
    assert (db.get_planting(planting_id)["x_in"], db.get_planting(planting_id)["y_in"]) == (12, 24)


def test_deleting_bed_scoped_planting_redirects_to_bed_detail(client):
    plot_id = _create_plot(client)
    bed_id = _create_bed(client, plot_id)
    variety_id = _create_variety(client)
    client.post(f"/beds/{bed_id}/cells/0/0", data={"variety_id": str(variety_id), "planted_date": "2026-05-01"})
    planting_id = db.list_plantings_at_cell(bed_id, 0, 0)[0]["id"]
    response = client.post(f"/plantings/{planting_id}/delete", follow_redirects=False)
    assert response.headers["location"] == f"/beds/{bed_id}"


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
