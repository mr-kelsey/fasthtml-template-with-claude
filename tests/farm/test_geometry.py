from datetime import date

import pytest

from farm.geometry import (
    bed_local_to_plot,
    classify_bed_cell_shade,
    nearest_solstice,
    point_in_polygon,
    shade_exceeds_tolerance,
)

SQUARE = [(-1, -1), (-1, 1), (1, 1), (1, -1)]


def _bed(x=0, y=0, width_ft=4, length_ft=6, rotation_deg=0):
    return {"x": x, "y": y, "width_ft": width_ft, "length_ft": length_ft, "rotation_deg": rotation_deg}


def test_nearest_solstice_near_summer_returns_summer_solstice():
    assert nearest_solstice(date(2026, 6, 20)) == "summer_solstice"


def test_nearest_solstice_near_winter_returns_winter_solstice():
    assert nearest_solstice(date(2026, 12, 20)) == "winter_solstice"


def test_nearest_solstice_crosses_to_summer_just_before_the_equinox():
    assert nearest_solstice(date(2026, 9, 20)) == "summer_solstice"


def test_nearest_solstice_crosses_to_winter_just_after_the_equinox():
    assert nearest_solstice(date(2026, 9, 21)) == "winter_solstice"


def test_point_in_polygon_true_for_a_point_inside_a_square():
    assert point_in_polygon(0, 0, SQUARE) is True


def test_point_in_polygon_false_for_a_point_outside_a_square():
    assert point_in_polygon(5, 5, SQUARE) is False


def test_bed_local_to_plot_with_no_rotation_maps_the_local_origin_to_the_bed_origin():
    assert bed_local_to_plot(_bed(x=10, y=20), 0, 0) == (10, 20)


def test_bed_local_to_plot_with_90_degree_rotation():
    result = bed_local_to_plot(_bed(x=0, y=0, width_ft=4, length_ft=6, rotation_deg=90), 0, 0)
    assert result == pytest.approx((5, 1))


def test_classify_bed_cell_shade_returns_full_sun_with_no_polygons():
    assert classify_bed_cell_shade(_bed(), 0, 0, date(2026, 6, 20), []) == "full_sun"


def test_classify_bed_cell_shade_returns_full_shade_inside_a_full_polygon():
    polygons = [{"season": "summer_solstice", "shade_type": "full", "points": SQUARE}]
    assert classify_bed_cell_shade(_bed(), 0, 0, date(2026, 6, 20), polygons) == "full_shade"


def test_classify_bed_cell_shade_returns_partial_shade_inside_a_partial_polygon():
    polygons = [{"season": "summer_solstice", "shade_type": "partial", "points": SQUARE}]
    assert classify_bed_cell_shade(_bed(), 0, 0, date(2026, 6, 20), polygons) == "partial_shade"


def test_classify_bed_cell_shade_prefers_full_shade_when_full_and_partial_overlap():
    polygons = [
        {"season": "summer_solstice", "shade_type": "partial", "points": SQUARE},
        {"season": "summer_solstice", "shade_type": "full", "points": SQUARE},
    ]
    assert classify_bed_cell_shade(_bed(), 0, 0, date(2026, 6, 20), polygons) == "full_shade"


def test_classify_bed_cell_shade_returns_full_sun_for_an_unplaced_bed():
    polygons = [{"season": "summer_solstice", "shade_type": "full", "points": SQUARE}]
    assert classify_bed_cell_shade(_bed(x=None, y=None), 0, 0, date(2026, 6, 20), polygons) == "full_sun"


def test_shade_exceeds_tolerance_true_when_a_weekly_sample_is_darker_than_sun_needs():
    polygons = [{"season": "summer_solstice", "shade_type": "full", "points": SQUARE}]
    assert shade_exceeds_tolerance(
        _bed(), 0, 0, date(2026, 6, 1), date(2026, 6, 30), "full_sun", polygons
    ) is True


def test_shade_exceeds_tolerance_false_when_sun_needs_is_unset():
    polygons = [{"season": "summer_solstice", "shade_type": "full", "points": SQUARE}]
    assert shade_exceeds_tolerance(
        _bed(), 0, 0, date(2026, 6, 1), date(2026, 6, 30), None, polygons
    ) is False
