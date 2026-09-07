"""Shared helpers for the farm-planning pages (plants.py, seed_varieties.py, plantings.py)."""

AGRONOMIC_FIELD_LABELS = {
    "germination_days_min": "Germination days (min)",
    "germination_days_max": "Germination days (max)",
    "days_to_maturity_min": "Days to maturity (min)",
    "days_to_maturity_max": "Days to maturity (max)",
    "spacing_in": "Spacing (in)",
}


def parse_optional_int(value: str):
    "Returns (ok, int_or_none). ok is False when value is non-blank but not a valid integer."
    if value is None or value.strip() == "":
        return True, None
    try:
        return True, int(value)
    except ValueError:
        return False, None


def parse_required_int(value: str, field_label: str):
    "Returns (int, None) or (None, error_message) if value is blank or not a valid integer."
    if value is None or value.strip() == "":
        return None, f"{field_label} is required."
    try:
        return int(value), None
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
