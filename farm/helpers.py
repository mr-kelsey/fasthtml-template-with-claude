"""Shared helpers for the farm-planning pages (seed_varieties.py, plantings.py)."""

from datetime import date, timedelta

AGRONOMIC_FIELD_LABELS = {
    "germination_days_min": "Germination days (min)",
    "germination_days_max": "Germination days (max)",
    "days_to_maturity_min": "Days to maturity (min)",
    "days_to_maturity_max": "Days to maturity (max)",
    "spacing_in": "Spacing (in)",
}

SOIL_FEEDING_FIELD_LABELS = {
    "soil_ph_min": "Soil pH (min)",
    "soil_ph_max": "Soil pH (max)",
    "feeding_frequency_days": "Feeding frequency (days)",
}

NPK_FIELD_LABELS = {
    "growth_npk": "Growth cycle food requirements: N-P-K",
    "produce_npk": "Produce cycle food requirements: N-P-K",
}

SUN_NEEDS_OPTIONS = ["full_sun", "partial_shade", "full_shade"]

RELATION_OPTIONS = ["companion", "antagonist"]

SEASON_OPTIONS = ["summer_solstice", "winter_solstice"]

SHADE_TYPE_OPTIONS = ["full", "partial"]

# Fixed rotation for auto-assigning seed_varieties.color_hex at creation (round-robin by existing
# count); user can still override before submit. Distinct enough to tell staged/planted dots apart.
COLOR_PALETTE = [
    "#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
    "#911eb4", "#46f0f0", "#f032e6", "#bcf60c", "#fabebe",
    "#008080", "#9a6324",
]


def next_palette_color(existing_varieties):
    "Round-robins COLOR_PALETTE by how many varieties already exist -- used to prefill the add-variety form."
    return COLOR_PALETTE[len(existing_varieties) % len(COLOR_PALETTE)]


def parse_optional_int(value: str):
    "Returns (ok, int_or_none). ok is False when value is non-blank but not a valid integer."
    if value is None or value.strip() == "":
        return True, None
    try:
        return True, int(value)
    except ValueError:
        return False, None


def parse_optional_float(value: str):
    "Returns (ok, float_or_none). ok is False when value is non-blank but not a valid float."
    if value is None or value.strip() == "":
        return True, None
    try:
        return True, float(value)
    except ValueError:
        return False, None


def parse_optional_date(value: str):
    "Returns (ok, date_string_or_none). ok is False when value is non-blank but not a valid ISO date."
    if value is None or value.strip() == "":
        return True, None
    try:
        date.fromisoformat(value.strip())
        return True, value.strip()
    except ValueError:
        return False, None


def default_acquired_date():
    """ISO date string for a year prior to today. Undated seed lots default here rather than to
    NULL or today -- an unlabeled jar of seeds is more likely to be from last year's harvest/purchase
    than freshly acquired, and a real date keeps farm/db.py's _decrement_seed_stock oldest-lot-first
    draw-down ordering meaningful instead of falling back to NULL-last/id order."""
    today = date.today()
    try:
        return today.replace(year=today.year - 1).isoformat()
    except ValueError:
        # today is Feb 29 and year - 1 isn't a leap year -- nearest equivalent is Feb 28.
        return today.replace(month=2, day=28, year=today.year - 1).isoformat()


def parse_required_int(value: str, field_label: str):
    "Returns (int, None) or (None, error_message) if value is blank or not a valid integer."
    if value is None or value.strip() == "":
        return None, f"{field_label} is required."
    try:
        return int(value), None
    except ValueError:
        return None, f"{field_label} must be a number."


def parse_required_float(value: str, field_label: str):
    "Returns (float, None) or (None, error_message) if value is blank or not a valid number."
    if value is None or value.strip() == "":
        return None, f"{field_label} is required."
    try:
        return float(value), None
    except ValueError:
        return None, f"{field_label} must be a number."


def parse_agronomic_fields(
    germination_days_min: str,
    germination_days_max: str,
    days_to_maturity_min: str,
    days_to_maturity_max: str,
    spacing_in: str,
):
    "Returns (fields_dict, None) or (None, error_message) if a field is non-blank but not a valid integer."
    raw = {
        "germination_days_min": germination_days_min,
        "germination_days_max": germination_days_max,
        "days_to_maturity_min": days_to_maturity_min,
        "days_to_maturity_max": days_to_maturity_max,
        "spacing_in": spacing_in,
    }
    parsed = {}
    for field_name, value in raw.items():
        ok, parsed_value = parse_optional_int(value)
        if not ok:
            return None, f"{AGRONOMIC_FIELD_LABELS[field_name]} must be a number."
        parsed[field_name] = parsed_value
    return parsed, None


def parse_npk_formula(value: str):
    "Parses an 'N-P-K' formula string (e.g. '10-5-5') into (n, p, k) floats. (True, (None, None, None)) when blank."
    if value is None or value.strip() == "":
        return True, (None, None, None)
    parts = value.strip().split("-")
    if len(parts) != 3:
        return False, (None, None, None)
    try:
        return True, tuple(float(part) for part in parts)
    except ValueError:
        return False, (None, None, None)


def _format_npk_component(value: float):
    return str(int(value)) if value == int(value) else str(value)


def format_npk(n: float, p: float, k: float):
    "Renders a growth/produce N-P-K triad back into the 'N-P-K' formula string, or '' when all unset."
    if n is None and p is None and k is None:
        return ""
    return "-".join(_format_npk_component(v) if v is not None else "" for v in (n, p, k))


def parse_soil_feeding_fields(
    soil_type: str,
    soil_ph_min: str,
    soil_ph_max: str,
    feeding_frequency_days: str,
    growth_npk: str,
    produce_npk: str,
):
    "Returns (fields_dict, None) or (None, error_message) if a numeric field or N-P-K formula is invalid."
    parsed = {"soil_type": soil_type.strip() or None if soil_type is not None else None}
    ok, parsed["feeding_frequency_days"] = parse_optional_int(feeding_frequency_days)
    if not ok:
        return None, f"{SOIL_FEEDING_FIELD_LABELS['feeding_frequency_days']} must be a number."
    for field_name, value in (("soil_ph_min", soil_ph_min), ("soil_ph_max", soil_ph_max)):
        ok, parsed_value = parse_optional_float(value)
        if not ok:
            return None, f"{SOIL_FEEDING_FIELD_LABELS[field_name]} must be a number."
        parsed[field_name] = parsed_value
    for prefix, value in (("growth", growth_npk), ("produce", produce_npk)):
        ok, (n, p, k) = parse_npk_formula(value)
        if not ok:
            return None, f"{NPK_FIELD_LABELS[f'{prefix}_npk']} must be in N-P-K format (e.g. 10-5-5)."
        parsed[f"{prefix}_npk_n"], parsed[f"{prefix}_npk_p"], parsed[f"{prefix}_npk_k"] = n, p, k
    return parsed, None


def validate_sun_needs(value: str):
    "Returns (value_or_none, None) or (None, error_message) if value is non-blank but not in SUN_NEEDS_OPTIONS."
    if value is None or value.strip() == "":
        return None, None
    if value not in SUN_NEEDS_OPTIONS:
        return None, f"Sun needs must be one of: {', '.join(SUN_NEEDS_OPTIONS)}."
    return value, None


def validate_relation(value: str):
    "Returns (value, None) or (None, error_message). Unlike sun_needs, relation is required -- blank is an error."
    if value is None or value.strip() == "":
        return None, "Relation is required."
    if value not in RELATION_OPTIONS:
        return None, f"Relation must be one of: {', '.join(RELATION_OPTIONS)}."
    return value, None


def compute_window(planted_date: str, days_min: int, days_max: int):
    "The (start, end) date range a milestone is expected to land in, or None when the days aren't known."
    if days_min is None or days_max is None:
        return None
    planted = date.fromisoformat(planted_date)
    return planted + timedelta(days=days_min), planted + timedelta(days=days_max)


def format_day_range(days_min: int, days_max: int):
    "Renders an optional min/max day range for display, e.g. '60-80', '60+', or '' when both are unset."
    if days_min is None and days_max is None:
        return ""
    if days_min == days_max:
        return str(days_min)
    if days_min is None:
        return f"up to {days_max}"
    if days_max is None:
        return f"{days_min}+"
    return f"{days_min}-{days_max}"
