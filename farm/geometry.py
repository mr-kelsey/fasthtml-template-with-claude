"""Shade geometry for phase 9: point-in-polygon classification of a bed position's sun/shade
exposure against freehand-drawn shade_polygons, plus the weekly-sampled planting-time warning.
No db access -- pure functions over plain dicts, so they're testable standalone.
"""

import math
from datetime import timedelta

from farm.helpers import SUN_NEEDS_OPTIONS

_SUMMER_SOLSTICE_MONTH_DAY = (6, 21)
_WINTER_SOLSTICE_MONTH_DAY = (12, 21)

# Darkest last -- also the ordinal a variety's sun_needs is tolerance-checked against
# (SUN_NEEDS_OPTIONS is "the minimum light the plant tolerates", same domain).
_SHADE_ORDER = SUN_NEEDS_OPTIONS


def _day_of_year(on_date):
    return on_date.timetuple().tm_yday


def _season_weight(on_date):
    """Continuous summer<->winter blend weight in [0, 1]: 1.0 at the summer solstice, 0.0 at the
    winter solstice, smoothly crossing ~0.5 near both equinoxes via a cosine curve. Replaces a
    hard nearest-solstice cutover so shade grows/shrinks gradually across the year instead of
    jumping instantly at the equinox."""
    doy = _day_of_year(on_date)
    summer_doy = _day_of_year(on_date.replace(month=_SUMMER_SOLSTICE_MONTH_DAY[0], day=_SUMMER_SOLSTICE_MONTH_DAY[1]))
    angle = 2 * math.pi * (doy - summer_doy) / 365
    return (math.cos(angle) + 1) / 2


def point_in_polygon(x, y, points):
    "Standard ray-casting point-in-polygon test. points is a list of (x, y) tuples."
    inside = False
    n = len(points)
    j = n - 1
    for i in range(n):
        xi, yi = points[i]
        xj, yj = points[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _point_segment_distance(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def signed_distance_to_polygon(x, y, points):
    "Positive inside, negative outside. Magnitude is the distance to the nearest edge."
    n = len(points)
    distance = min(
        _point_segment_distance(x, y, points[i][0], points[i][1], points[(i + 1) % n][0], points[(i + 1) % n][1])
        for i in range(n)
    )
    return distance if point_in_polygon(x, y, points) else -distance


def bed_local_to_plot(bed, x_in, y_in):
    """Converts a bed-local inch position to plot-space feet, mirroring the SVG bed-group
    transform translate(x,y) rotate(rotation_deg,cx,cy) used by pages/land_plots.py's
    _bed_group: rotate about the bed's center, then translate by the bed's plot position."""
    x_ft, y_ft = x_in / 12, y_in / 12
    cx, cy = bed["width_ft"] / 2, bed["length_ft"] / 2
    angle = math.radians(bed["rotation_deg"] or 0)
    dx, dy = x_ft - cx, y_ft - cy
    rx = dx * math.cos(angle) - dy * math.sin(angle)
    ry = dx * math.sin(angle) + dy * math.cos(angle)
    return bed["x"] + cx + rx, bed["y"] + cy + ry


def _blended_signed_distance(x, y, season_points, t):
    "season_points: {'summer_solstice': points_or_None, 'winter_solstice': points_or_None}."
    summer_points = season_points.get("summer_solstice")
    winter_points = season_points.get("winter_solstice")
    if summer_points and winter_points:
        return t * signed_distance_to_polygon(x, y, summer_points) + (1 - t) * signed_distance_to_polygon(
            x, y, winter_points
        )
    if summer_points:
        return signed_distance_to_polygon(x, y, summer_points)
    if winter_points:
        return signed_distance_to_polygon(x, y, winter_points)
    return -math.inf


def classify_point_shade(plot_x, plot_y, on_date, shade_polygons):
    """shade_polygons: iterable of {shade_source_id, season, shade_type, points}. Groups each
    source's summer/winter pair per shade_type and blends between them by the date's seasonal
    weight (a source with only one season drawn falls back to that polygon, unblended). Darkest
    matching group wins."""
    t = _season_weight(on_date)
    by_group = {}
    for p in shade_polygons:
        group = by_group.setdefault((p["shade_source_id"], p["shade_type"]), {})
        group[p["season"]] = p["points"]

    def any_group_contains(shade_type):
        # >= 0, not > 0: a point exactly on a polygon's edge has signed distance 0 and still
        # counts as inside, matching point_in_polygon's own boundary-inclusive semantics.
        return any(
            _blended_signed_distance(plot_x, plot_y, seasons, t) >= 0
            for (source_id, group_type), seasons in by_group.items()
            if group_type == shade_type
        )

    if any_group_contains("full"):
        return "full_shade"
    if any_group_contains("partial"):
        return "partial_shade"
    return "full_sun"


def classify_bed_cell_shade(bed, x_in, y_in, on_date, shade_polygons):
    "Returns 'full_sun'/'partial_shade'/'full_shade'. An unplaced bed has no plot position to classify."
    if bed["x"] is None or bed["y"] is None:
        return "full_sun"
    plot_x, plot_y = bed_local_to_plot(bed, x_in, y_in)
    return classify_point_shade(plot_x, plot_y, on_date, shade_polygons)


def shade_exceeds_tolerance(bed, x_in, y_in, planted_date, maturity_end_date, sun_needs, shade_polygons):
    """Weekly-sampled from planted_date to maturity_end_date inclusive. True if any sample's
    shade classification is darker than sun_needs tolerates. Unset sun_needs never warns."""
    if sun_needs not in _SHADE_ORDER:
        return False
    tolerance_index = _SHADE_ORDER.index(sun_needs)
    current = planted_date
    while current <= maturity_end_date:
        classification = classify_bed_cell_shade(bed, x_in, y_in, current, shade_polygons)
        if _SHADE_ORDER.index(classification) > tolerance_index:
            return True
        current += timedelta(days=7)
    return False
