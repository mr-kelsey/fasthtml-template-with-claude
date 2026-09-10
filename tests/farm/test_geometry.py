from datetime import date

import pytest

from farm.geometry import (
    _season_weight,
    bed_local_to_plot,
    classify_bed_cell_shade,
    point_in_polygon,
    shade_exceeds_tolerance,
    signed_distance_to_polygon,
)

SQUARE = [(-1, -1), (-1, 1), (1, 1), (1, -1)]
BIG_SQUARE = [(-3, -3), (-3, 3), (3, 3), (3, -3)]


def _bed(x=0, y=0, width_ft=4, length_ft=6, rotation_deg=0):
    return {"x": x, "y": y, "width_ft": width_ft, "length_ft": length_ft, "rotation_deg": rotation_deg}


def _polygon(shade_source_id, season, shade_type, points):
    return {"shade_source_id": shade_source_id, "season": season, "shade_type": shade_type, "points": points}


def test_season_weight_is_one_at_the_summer_solstice():
    assert _season_weight(date(2026, 6, 21)) == pytest.approx(1.0, abs=0.01)


def test_season_weight_is_zero_at_the_winter_solstice():
    assert _season_weight(date(2026, 12, 21)) == pytest.approx(0.0, abs=0.01)


def test_season_weight_is_roughly_half_at_the_autumn_equinox():
    assert _season_weight(date(2026, 9, 23)) == pytest.approx(0.5, abs=0.05)


def test_season_weight_is_roughly_half_at_the_spring_equinox():
    assert _season_weight(date(2026, 3, 20)) == pytest.approx(0.5, abs=0.05)


def test_point_in_polygon_true_for_a_point_inside_a_square():
    assert point_in_polygon(0, 0, SQUARE) is True


def test_point_in_polygon_false_for_a_point_outside_a_square():
    assert point_in_polygon(5, 5, SQUARE) is False


def test_signed_distance_is_positive_inside_a_polygon():
    assert signed_distance_to_polygon(0, 0, SQUARE) > 0


def test_signed_distance_is_negative_outside_a_polygon():
    assert signed_distance_to_polygon(5, 5, SQUARE) < 0


def test_bed_local_to_plot_with_no_rotation_maps_the_local_origin_to_the_bed_origin():
    assert bed_local_to_plot(_bed(x=10, y=20), 0, 0) == (10, 20)


def test_bed_local_to_plot_with_90_degree_rotation():
    result = bed_local_to_plot(_bed(x=0, y=0, width_ft=4, length_ft=6, rotation_deg=90), 0, 0)
    assert result == pytest.approx((5, 1))


def test_classify_bed_cell_shade_returns_full_sun_with_no_polygons():
    assert classify_bed_cell_shade(_bed(), 0, 0, date(2026, 6, 20), []) == "full_sun"


def test_classify_bed_cell_shade_returns_full_shade_inside_a_full_polygon():
    polygons = [_polygon(1, "summer_solstice", "full", SQUARE), _polygon(1, "winter_solstice", "full", SQUARE)]
    assert classify_bed_cell_shade(_bed(), 0, 0, date(2026, 6, 20), polygons) == "full_shade"


def test_classify_bed_cell_shade_returns_partial_shade_inside_a_partial_polygon():
    polygons = [_polygon(1, "summer_solstice", "partial", SQUARE), _polygon(1, "winter_solstice", "partial", SQUARE)]
    assert classify_bed_cell_shade(_bed(), 0, 0, date(2026, 6, 20), polygons) == "partial_shade"


def test_classify_bed_cell_shade_prefers_full_shade_when_full_and_partial_overlap():
    polygons = [
        _polygon(1, "summer_solstice", "partial", SQUARE),
        _polygon(1, "winter_solstice", "partial", SQUARE),
        _polygon(2, "summer_solstice", "full", SQUARE),
        _polygon(2, "winter_solstice", "full", SQUARE),
    ]
    assert classify_bed_cell_shade(_bed(), 0, 0, date(2026, 6, 20), polygons) == "full_shade"


def test_classify_bed_cell_shade_returns_full_sun_for_an_unplaced_bed():
    polygons = [_polygon(1, "summer_solstice", "full", SQUARE), _polygon(1, "winter_solstice", "full", SQUARE)]
    assert classify_bed_cell_shade(_bed(x=None, y=None), 0, 0, date(2026, 6, 20), polygons) == "full_sun"


def test_classify_bed_cell_shade_counts_a_point_exactly_on_the_polygon_corner_as_shaded():
    # A point sitting exactly on a clamped-to-the-plot-boundary polygon's corner has signed
    # distance 0 -- it must still classify as shaded, matching point_in_polygon's own
    # boundary-inclusive semantics, not fall through to full_sun.
    corner_square = [(0, 0), (0, 10), (10, 10), (10, 0)]
    polygons = [_polygon(1, "summer_solstice", "full", corner_square)]
    assert classify_bed_cell_shade(_bed(), 0, 0, date(2026, 6, 1), polygons) == "full_shade"


def test_classify_bed_cell_shade_uses_the_lone_polygon_when_only_one_season_is_drawn():
    polygons = [_polygon(1, "summer_solstice", "full", SQUARE)]
    assert classify_bed_cell_shade(_bed(), 0, 0, date(2026, 12, 21), polygons) == "full_shade"


def test_shade_grows_gradually_toward_the_season_with_the_larger_shadow():
    # Point maps to plot-space (2, 0): outside the small summer square, inside the big winter
    # square -- classification should track the blended weight rather than snapping at an
    # equinox part-way between the two solstices.
    polygons = [_polygon(1, "summer_solstice", "full", SQUARE), _polygon(1, "winter_solstice", "full", BIG_SQUARE)]
    assert classify_bed_cell_shade(_bed(), 24, 0, date(2026, 6, 21), polygons) == "full_sun"
    assert classify_bed_cell_shade(_bed(), 24, 0, date(2026, 12, 21), polygons) == "full_shade"
    assert classify_bed_cell_shade(_bed(), 24, 0, date(2026, 11, 1), polygons) == "full_shade"


def test_shade_exceeds_tolerance_true_when_a_weekly_sample_is_darker_than_sun_needs():
    polygons = [_polygon(1, "summer_solstice", "full", SQUARE), _polygon(1, "winter_solstice", "full", SQUARE)]
    assert shade_exceeds_tolerance(
        _bed(), 0, 0, date(2026, 6, 1), date(2026, 6, 30), "full_sun", polygons
    ) is True


def test_shade_exceeds_tolerance_false_when_sun_needs_is_unset():
    polygons = [_polygon(1, "summer_solstice", "full", SQUARE), _polygon(1, "winter_solstice", "full", SQUARE)]
    assert shade_exceeds_tolerance(
        _bed(), 0, 0, date(2026, 6, 1), date(2026, 6, 30), None, polygons
    ) is False
