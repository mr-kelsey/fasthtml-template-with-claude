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


def _circular_distance(a, b, period=365):
    diff = abs(a - b) % period
    return min(diff, period - diff)


def nearest_solstice(on_date):
    """Returns 'summer_solstice' or 'winter_solstice' -- whichever on_date's day-of-year is
    closer to by circular distance. Crosses over at the equinoxes automatically, since those
    are the equidistant points on the annual circle between the two solstices."""
    doy = _day_of_year(on_date)
    summer_doy = _day_of_year(on_date.replace(month=_SUMMER_SOLSTICE_MONTH_DAY[0], day=_SUMMER_SOLSTICE_MONTH_DAY[1]))
    winter_doy = _day_of_year(on_date.replace(month=_WINTER_SOLSTICE_MONTH_DAY[0], day=_WINTER_SOLSTICE_MONTH_DAY[1]))
    return "summer_solstice" if _circular_distance(doy, summer_doy) <= _circular_distance(doy, winter_doy) else "winter_solstice"


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


def classify_point_shade(plot_x, plot_y, season, shade_polygons):
    "shade_polygons: iterable of {season, shade_type, points}. Darkest matching polygon wins."
    matching = [p for p in shade_polygons if p["season"] == season]
    if any(p["shade_type"] == "full" and point_in_polygon(plot_x, plot_y, p["points"]) for p in matching):
        return "full_shade"
    if any(p["shade_type"] == "partial" and point_in_polygon(plot_x, plot_y, p["points"]) for p in matching):
        return "partial_shade"
    return "full_sun"


def classify_bed_cell_shade(bed, x_in, y_in, on_date, shade_polygons):
    "Returns 'full_sun'/'partial_shade'/'full_shade'. An unplaced bed has no plot position to classify."
    if bed["x"] is None or bed["y"] is None:
        return "full_sun"
    plot_x, plot_y = bed_local_to_plot(bed, x_in, y_in)
    season = nearest_solstice(on_date)
    return classify_point_shade(plot_x, plot_y, season, shade_polygons)


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
