import json

import pytest

import db


def _make_plot(width_ft=20, length_ft=20, name="Test Plot"):
    db.add_land_plot(name, width_ft, length_ft)
    return db.list_land_plots()[0]["id"]


def _make_bed(plot_id, width_ft=4, length_ft=4, label="Bed A", x=2, y=2):
    db.add_bed(plot_id, label, width_ft, length_ft)
    bed_id = db.list_beds_for_plot(plot_id)[0]["id"]
    db.update_bed_position(bed_id, x, y)
    return bed_id


def _svg_click_point(page, viewbox_w, viewbox_h, feet_x, feet_y):
    """On-screen pixel coordinates for a (feet_x, feet_y) point in #land-map-svg's viewBox.

    The svg has no preserveAspectRatio override, so the browser applies the default
    xMidYMid-meet letterboxing: content is scaled uniformly (by the smaller of the
    width/height ratios) and centered, not stretched to fill the CSS box. Used to make sure
    a synthetic click actually lands on the target element.
    """
    box = page.locator("#land-map-svg").bounding_box()
    scale = min(box["width"] / viewbox_w, box["height"] / viewbox_h)
    offset_x = box["x"] + (box["width"] - viewbox_w * scale) / 2
    offset_y = box["y"] + (box["height"] - viewbox_h * scale) / 2
    return offset_x + feet_x * scale, offset_y + feet_y * scale


def _js_naive_scale(page, viewbox_w, viewbox_h):
    "Matches land-map.js's own toFeet(): (clientX - rect.left) / rect.width * viewBox.width -- a per-axis stretch, not the true letterboxed scale. Movement deltas during a drag are interpreted through this, regardless of the true rendering."
    box = page.locator("#land-map-svg").bounding_box()
    return box["width"] / viewbox_w, box["height"] / viewbox_h


def test_dragging_a_bed_persists_its_new_position(page, live_server_url):
    plot_id = _make_plot()
    bed_id = _make_bed(plot_id, x=2, y=2)
    page.goto(f"{live_server_url}/land-plots/{plot_id}/map")

    cx, cy = _svg_click_point(page, 20, 20, 4, 4)  # bed center: x=2+4/2, y=2+4/2
    px_per_ft_x, px_per_ft_y = _js_naive_scale(page, 20, 20)
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.move(cx + 5 * px_per_ft_x, cy + 3 * px_per_ft_y, steps=5)
    with page.expect_response(lambda r: f"/beds/{bed_id}/position" in r.url):
        page.mouse.up()

    bed = db.get_bed(bed_id)
    assert (bed["x"], bed["y"]) == (7, 5)


def test_dragging_past_the_plot_edge_clamps_to_the_max_legal_position(page, live_server_url):
    plot_id = _make_plot(width_ft=10, length_ft=10)
    bed_id = _make_bed(plot_id, width_ft=4, length_ft=4, x=0, y=0)
    page.goto(f"{live_server_url}/land-plots/{plot_id}/map")

    cx, cy = _svg_click_point(page, 10, 10, 2, 2)  # bed center: x=0+4/2, y=0+4/2
    px_per_ft_x, px_per_ft_y = _js_naive_scale(page, 10, 10)
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.move(cx + 15 * px_per_ft_x, cy + 15 * px_per_ft_y, steps=5)
    with page.expect_response(lambda r: f"/beds/{bed_id}/position" in r.url):
        page.mouse.up()

    bed = db.get_bed(bed_id)
    assert (bed["x"], bed["y"]) == (6, 6)


def test_a_plain_click_navigates_without_moving_the_bed(page, live_server_url):
    plot_id = _make_plot()
    bed_id = _make_bed(plot_id, x=2, y=2)
    page.goto(f"{live_server_url}/land-plots/{plot_id}/map")

    cx, cy = _svg_click_point(page, 20, 20, 4, 4)
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.up()
    page.wait_for_url(f"**/beds/{bed_id}")

    bed = db.get_bed(bed_id)
    assert (bed["x"], bed["y"]) == (2, 2)


def test_resizing_a_bed_persists_its_new_dimensions(page, live_server_url):
    plot_id = _make_plot()
    bed_id = _make_bed(plot_id, width_ft=4, length_ft=4, x=2, y=2)
    page.goto(f"{live_server_url}/land-plots/{plot_id}/map")

    # Resize handle center, in absolute feet: bed origin (2,2) + local (width-0.5, length-0.5).
    handle_x, handle_y = _svg_click_point(page, 20, 20, 2 + 3.5, 2 + 3.5)
    px_per_ft_x, px_per_ft_y = _js_naive_scale(page, 20, 20)
    page.mouse.move(handle_x, handle_y)
    page.mouse.down()
    page.mouse.move(handle_x + 2 * px_per_ft_x, handle_y + 1 * px_per_ft_y, steps=5)
    with page.expect_response(lambda r: f"/beds/{bed_id}/size" in r.url):
        page.mouse.up()

    bed = db.get_bed(bed_id)
    assert (bed["width_ft"], bed["length_ft"]) == (6, 5)


def _drag_with_stubbed_position_failure(page, live_server_url):
    plot_id = _make_plot()
    bed_id = _make_bed(plot_id, x=2, y=2)
    page.goto(f"{live_server_url}/land-plots/{plot_id}/map")
    page.route(f"**/beds/{bed_id}/position", lambda route: route.fulfill(status=500, body="error"))

    cx, cy = _svg_click_point(page, 20, 20, 4, 4)
    px_per_ft_x, px_per_ft_y = _js_naive_scale(page, 20, 20)
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.move(cx + 5 * px_per_ft_x, cy + 3 * px_per_ft_y, steps=5)
    with page.expect_response(lambda r: f"/beds/{bed_id}/position" in r.url):
        page.mouse.up()
    return bed_id


def test_a_failed_position_update_reverts_the_visible_bed_transform(page, live_server_url):
    bed_id = _drag_with_stubbed_position_failure(page, live_server_url)
    transform = page.locator(f"#bed-{bed_id}").get_attribute("transform")
    assert transform.startswith("translate(2,2)")


def test_a_failed_position_update_does_not_persist_the_new_position(page, live_server_url):
    bed_id = _drag_with_stubbed_position_failure(page, live_server_url)
    bed = db.get_bed(bed_id)
    assert (bed["x"], bed["y"]) == (2, 2)


def _add_shade_source(plot_id, label="Oak tree"):
    db.add_shade_source(plot_id, label)
    return db.list_shade_sources_for_plot(plot_id)[0]["id"]


def _draw_button(page, source_id, season="summer_solstice", shade_type="full"):
    return page.locator(
        f'.shade-draw-button[data-source-id="{source_id}"][data-season="{season}"][data-shade-type="{shade_type}"]'
    )


def test_drawing_a_shade_polygon_persists_its_points(page, live_server_url):
    plot_id = _make_plot(width_ft=20, length_ft=20)
    source_id = _add_shade_source(plot_id)
    page.goto(f"{live_server_url}/land-plots/{plot_id}/map")

    _draw_button(page, source_id).click()
    page.mouse.click(*_svg_click_point(page, 20, 20, 2, 2))
    page.mouse.click(*_svg_click_point(page, 20, 20, 6, 2))
    page.mouse.click(*_svg_click_point(page, 20, 20, 6, 6))
    with page.expect_response(lambda r: "/polygons" in r.url):
        page.mouse.click(*_svg_click_point(page, 20, 20, 2.1, 2.1))  # close, near the first vertex

    assert len(db.list_shade_polygons_for_source(source_id)) == 1


def test_dragging_an_existing_polygon_vertex_persists_the_update(page, live_server_url):
    plot_id = _make_plot(width_ft=20, length_ft=20)
    source_id = _add_shade_source(plot_id)
    db.save_shade_polygon(source_id, "summer_solstice", "full", json.dumps([[2, 2], [6, 2], [6, 6]]))
    page.goto(f"{live_server_url}/land-plots/{plot_id}/map")

    _draw_button(page, source_id).click()  # already drawn -- enters editing mode with draggable vertices

    # Freehand polygon points use the true (letterboxed) render scale -- unlike bed drag/resize,
    # which only ever consumes toFeet() deltas -- so both endpoints here use _svg_click_point
    # directly rather than a naive-scale pixel delta (see land-map.js's toFeetTrue).
    start = _svg_click_point(page, 20, 20, 2, 2)  # first vertex
    end = _svg_click_point(page, 20, 20, 3, 2)
    page.mouse.move(*start)
    page.mouse.down()
    page.mouse.move(*end, steps=5)
    with page.expect_response(lambda r: "/polygons" in r.url):
        page.mouse.up()

    points = json.loads(db.list_shade_polygons_for_source(source_id)[0]["points"])
    assert points[0] == pytest.approx([3, 2], abs=0.05)


def test_exit_button_reads_cancel_while_drawing_a_fresh_shape(page, live_server_url):
    plot_id = _make_plot(width_ft=20, length_ft=20)
    source_id = _add_shade_source(plot_id)
    page.goto(f"{live_server_url}/land-plots/{plot_id}/map")

    _draw_button(page, source_id).click()
    assert page.locator("#shade-draw-status button").inner_text() == "Cancel"


def test_exit_button_reads_done_once_editing_an_existing_polygon(page, live_server_url):
    plot_id = _make_plot(width_ft=20, length_ft=20)
    source_id = _add_shade_source(plot_id)
    db.save_shade_polygon(source_id, "summer_solstice", "full", json.dumps([[2, 2], [6, 2], [6, 6]]))
    page.goto(f"{live_server_url}/land-plots/{plot_id}/map")

    _draw_button(page, source_id).click()
    assert page.locator("#shade-draw-status button").inner_text() == "Done"


def test_clicking_done_restores_bed_click_navigation(page, live_server_url):
    "Bed clicks are suppressed while drawing/editing (a click could be placing a point over a bed); Done restores them."
    plot_id = _make_plot(width_ft=20, length_ft=20)
    bed_id = _make_bed(plot_id, x=2, y=2)
    source_id = _add_shade_source(plot_id)
    db.save_shade_polygon(source_id, "summer_solstice", "full", json.dumps([[10, 10], [10, 12], [12, 12]]))
    page.goto(f"{live_server_url}/land-plots/{plot_id}/map")

    _draw_button(page, source_id).click()
    page.locator("#shade-draw-status button").click()  # "Done"

    cx, cy = _svg_click_point(page, 20, 20, 4, 4)  # bed center
    page.mouse.click(cx, cy)
    page.wait_for_url(f"**/beds/{bed_id}")


def test_deleting_a_shade_polygon_via_its_sidebar_button_removes_it(page, live_server_url):
    plot_id = _make_plot(width_ft=20, length_ft=20)
    source_id = _add_shade_source(plot_id)
    db.save_shade_polygon(source_id, "summer_solstice", "full", json.dumps([[2, 2], [6, 2], [6, 6]]))
    page.goto(f"{live_server_url}/land-plots/{plot_id}/map")

    delete_button = page.locator(
        '.shade-combo-row[data-season="summer_solstice"][data-shade-type="full"] .shade-delete-polygon-button'
    )
    with page.expect_response(lambda r: "/shade-polygons/" in r.url and "/delete" in r.url):
        delete_button.click()

    assert db.list_shade_polygons_for_source(source_id) == []
