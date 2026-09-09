import db


def _make_bed(width_ft=2, length_ft=2, label="Bed A"):
    db.add_land_plot("Test Plot", 20, 20)
    plot_id = db.list_land_plots()[0]["id"]
    db.add_bed(plot_id, label, width_ft, length_ft)
    return db.list_beds_for_plot(plot_id)[0]["id"]


def _make_variety(common_name="Tomato", name="Cherokee Purple", spacing_in=8, color_hex="#ff0000"):
    db.add_seed_variety(common_name, name, "Solanaceae", spacing_in=spacing_in, color_hex=color_hex)
    return db.list_seed_varieties()[0]["id"]


def _add_seed_lot(variety_id):
    db.add_seed_lot(variety_id, quantity_on_hand=100)


def _add_transplant_lot(variety_id, quantity_on_hand):
    db.add_transplant_lot(variety_id, quantity_on_hand=quantity_on_hand)
    return db.list_available_transplant_lots_for_variety(variety_id)[0]["id"]


def _arm_seed_variety(page, variety_id):
    page.locator(f'.variety-palette-item[data-variety-id="{variety_id}"][data-mode="seed"]').click()


def test_arming_a_variety_renders_a_lattice_at_its_spacing(page, live_server_url):
    bed_id = _make_bed(width_ft=2, length_ft=2)  # 24in x 24in
    variety_id = _make_variety(spacing_in=8)
    _add_seed_lot(variety_id)

    page.goto(f"{live_server_url}/beds/{bed_id}")
    _arm_seed_variety(page, variety_id)

    # Fenceposted 0/8/16/24 on each axis -- a 4x4 lattice. One assertion covers both the point
    # count and their exact positions.
    points = page.locator("#lattice-layer circle").evaluate_all(
        "els => els.map(el => el.getAttribute('cx') + ',' + el.getAttribute('cy')).sort()"
    )
    expected = sorted(f"{x},{y}" for x in ("0", "8", "16", "24") for y in ("0", "8", "16", "24"))
    assert points == expected


def _stage_one_point(page, live_server_url, spacing_in=8, color_hex="#00ff00"):
    bed_id = _make_bed(width_ft=2, length_ft=2)
    variety_id = _make_variety(spacing_in=spacing_in, color_hex=color_hex)
    _add_seed_lot(variety_id)

    page.goto(f"{live_server_url}/beds/{bed_id}")
    _arm_seed_variety(page, variety_id)
    page.locator('#lattice-layer circle[cx="8"][cy="8"]').click()
    return bed_id, variety_id


def test_clicking_a_lattice_point_adds_one_staged_dot(page, live_server_url):
    _stage_one_point(page, live_server_url)
    assert page.locator('#staged-layer circle[cx="8"][cy="8"]').count() == 1


def test_staged_dot_is_drawn_in_the_varietys_color(page, live_server_url):
    _stage_one_point(page, live_server_url, color_hex="#00ff00")
    staged = page.locator('#staged-layer circle[cx="8"][cy="8"]')
    assert staged.get_attribute("fill") == "#00ff00"


def test_staging_a_point_updates_the_staged_count_label(page, live_server_url):
    _stage_one_point(page, live_server_url)
    assert "1 point" in page.locator("#batch-staged-count").inner_text()


def test_clicking_a_staged_dot_unstages_it(page, live_server_url):
    "The staged dot sits on top of its own (self-blocked) lattice point, so unstaging is wired to the dot itself, not the point underneath -- see static/bed-detail.js's render_lattice."
    _stage_one_point(page, live_server_url)
    page.locator('#staged-layer circle[cx="8"][cy="8"]').click()
    assert page.locator("#staged-layer circle").count() == 0


def _arm_with_existing_planting(page, live_server_url, spacing_in=8):
    bed_id = _make_bed(width_ft=2, length_ft=2)  # 24in x 24in
    variety_id = _make_variety(spacing_in=spacing_in)
    _add_seed_lot(variety_id)
    # An existing planting at a non-grid-aligned position (phase 3's continuous x_in/y_in).
    db.add_planting(variety_id, "2026-05-01", bed_id=bed_id, x_in=10, y_in=10)

    page.goto(f"{live_server_url}/beds/{bed_id}")
    _arm_seed_variety(page, variety_id)
    return bed_id, variety_id


def test_spacing_guard_blocks_a_lattice_point_within_true_distance(page, live_server_url):
    _arm_with_existing_planting(page, live_server_url)
    near_point = page.locator('#lattice-layer circle[cx="8"][cy="8"]')  # distance ~2.83in < 8in spacing
    assert "blocked" in near_point.get_attribute("class")


def test_spacing_guard_does_not_block_a_lattice_point_beyond_true_distance(page, live_server_url):
    _arm_with_existing_planting(page, live_server_url)
    far_point = page.locator('#lattice-layer circle[cx="24"][cy="24"]')  # distance ~19.8in > 8in spacing
    assert "blocked" not in far_point.get_attribute("class")


def test_clicking_a_blocked_lattice_point_does_not_stage_it(page, live_server_url):
    _arm_with_existing_planting(page, live_server_url)
    page.locator('#lattice-layer circle[cx="8"][cy="8"]').click()
    assert page.locator("#staged-layer circle").count() == 0


def test_clicking_an_unblocked_lattice_point_beyond_spacing_stages_it(page, live_server_url):
    _arm_with_existing_planting(page, live_server_url)
    page.locator('#lattice-layer circle[cx="24"][cy="24"]').click()
    assert page.locator('#staged-layer circle[cx="24"][cy="24"]').count() == 1


def test_companion_relation_tints_an_occupied_point_green(page, live_server_url):
    bed_id = _make_bed(width_ft=2, length_ft=2)
    tomato_id = _make_variety(common_name="Tomato", name="Cherokee Purple", spacing_in=8)
    basil_id = _make_variety(common_name="Basil", name="Genovese", spacing_in=8)
    _add_seed_lot(tomato_id)
    _add_seed_lot(basil_id)
    db.add_companion_rule("Tomato", "Basil", "companion")
    db.add_planting(tomato_id, "2026-05-01", bed_id=bed_id, x_in=0, y_in=0)

    page.goto(f"{live_server_url}/beds/{bed_id}")
    _arm_seed_variety(page, basil_id)

    tomato_dot = page.locator(f'#planted-layer .planting-dot[data-variety-id="{tomato_id}"]')
    assert "companion" in tomato_dot.get_attribute("class")


def test_antagonist_relation_tints_an_occupied_point_red(page, live_server_url):
    bed_id = _make_bed(width_ft=2, length_ft=2)
    tomato_id = _make_variety(common_name="Tomato", name="Cherokee Purple", spacing_in=8)
    fennel_id = _make_variety(common_name="Fennel", name="Florence", spacing_in=8)
    _add_seed_lot(tomato_id)
    _add_seed_lot(fennel_id)
    db.add_companion_rule("Tomato", "Fennel", "antagonist")
    db.add_planting(tomato_id, "2026-05-01", bed_id=bed_id, x_in=0, y_in=0)

    page.goto(f"{live_server_url}/beds/{bed_id}")
    _arm_seed_variety(page, fennel_id)

    tomato_dot = page.locator(f'#planted-layer .planting-dot[data-variety-id="{tomato_id}"]')
    assert "antagonist" in tomato_dot.get_attribute("class")


def _arm_transplant_with_lot(page, live_server_url, quantity_on_hand):
    bed_id = _make_bed(width_ft=2, length_ft=2)
    variety_id = _make_variety(spacing_in=8)
    lot_id = _add_transplant_lot(variety_id, quantity_on_hand=quantity_on_hand)

    page.goto(f"{live_server_url}/beds/{bed_id}")
    page.locator("#mode-transplant").check()
    page.locator(f'.variety-palette-item[data-variety-id="{variety_id}"][data-mode="transplant"]').click()
    return bed_id, variety_id, lot_id


def test_transplant_staging_stages_up_to_the_lot_quantity(page, live_server_url):
    _arm_transplant_with_lot(page, live_server_url, quantity_on_hand=1)
    page.locator('#lattice-layer circle[cx="0"][cy="0"]').click()
    assert page.locator("#staged-layer circle").count() == 1


def test_transplant_staging_is_hard_capped_at_lot_quantity_on_hand(page, live_server_url):
    _arm_transplant_with_lot(page, live_server_url, quantity_on_hand=1)
    page.locator('#lattice-layer circle[cx="0"][cy="0"]').click()
    page.locator('#lattice-layer circle[cx="8"][cy="0"]').click()  # no-op, cap already reached
    assert page.locator("#staged-layer circle").count() == 1


def _edit_lot_quantity_inline(page, live_server_url, new_quantity):
    bed_id, variety_id, lot_id = _arm_transplant_with_lot(page, live_server_url, quantity_on_hand=1)
    page.locator('#lattice-layer circle[cx="0"][cy="0"]').click()

    quantity_input = page.locator("#armed-lot-quantity-input")
    quantity_input.fill(str(new_quantity))
    with page.expect_response(lambda r: f"/transplant-lots/{lot_id}/quantity" in r.url):
        quantity_input.press("Tab")  # blur, not Enter -- this input lives inside the batch-plant form
    return bed_id, variety_id, lot_id


def test_editing_lot_quantity_inline_persists_it(page, live_server_url):
    _, _, lot_id = _edit_lot_quantity_inline(page, live_server_url, new_quantity=3)
    assert db.get_transplant_lot(lot_id)["quantity_on_hand"] == 3


def test_editing_lot_quantity_inline_raises_the_staging_cap(page, live_server_url):
    _edit_lot_quantity_inline(page, live_server_url, new_quantity=3)
    page.locator('#lattice-layer circle[cx="8"][cy="0"]').click()
    assert page.locator("#staged-layer circle").count() == 2


def _submit_confirmed_batch(page, live_server_url, lot_quantity_on_hand):
    bed_id, variety_id, lot_id = _arm_transplant_with_lot(page, live_server_url, lot_quantity_on_hand)
    page.locator('#lattice-layer circle[cx="0"][cy="0"]').click()

    page.once("dialog", lambda dialog: dialog.accept())
    page.locator("#batch-plant-form input[name='planted_date']").fill("2026-05-01")
    with page.expect_navigation():
        page.locator("#batch-plant-form button[type='submit']").click()
    return bed_id, lot_id


def test_confirming_an_undercount_batch_plants_the_staged_points(page, live_server_url):
    bed_id, _ = _submit_confirmed_batch(page, live_server_url, lot_quantity_on_hand=3)
    assert len(db.list_plantings_for_bed(bed_id)) == 1


def test_confirming_an_undercount_batch_records_the_transplant_lot(page, live_server_url):
    bed_id, lot_id = _submit_confirmed_batch(page, live_server_url, lot_quantity_on_hand=3)
    assert db.list_plantings_for_bed(bed_id)[0]["transplant_lot_id"] == lot_id


def test_confirming_an_undercount_batch_decrements_the_lot(page, live_server_url):
    _, lot_id = _submit_confirmed_batch(page, live_server_url, lot_quantity_on_hand=3)
    assert db.get_transplant_lot(lot_id)["quantity_on_hand"] == 2


def _dismiss_undercount_batch(page, live_server_url):
    bed_id, variety_id, lot_id = _arm_transplant_with_lot(page, live_server_url, quantity_on_hand=3)
    page.locator('#lattice-layer circle[cx="0"][cy="0"]').click()

    page.once("dialog", lambda dialog: dialog.dismiss())
    page.locator("#batch-plant-form input[name='planted_date']").fill("2026-05-01")
    page.locator("#batch-plant-form button[type='submit']").click()
    page.wait_for_timeout(200)
    return bed_id


def test_dismissing_the_undercount_confirm_plants_nothing(page, live_server_url):
    bed_id = _dismiss_undercount_batch(page, live_server_url)
    assert db.list_plantings_for_bed(bed_id) == []


def test_dismissing_the_undercount_confirm_leaves_the_page_unsubmitted(page, live_server_url):
    bed_id = _dismiss_undercount_batch(page, live_server_url)
    assert page.url.rstrip("/").endswith(f"/beds/{bed_id}")
