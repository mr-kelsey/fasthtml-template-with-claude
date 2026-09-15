from farm.helpers import rotation_conflict


def _planting(plant_family, planted_date, common_name="Tomato", name="Cherokee Purple"):
    return {"plant_family": plant_family, "planted_date": planted_date, "common_name": common_name, "name": name}


def test_rotation_conflict_is_none_when_no_planting_shares_the_family():
    history = [_planting("Fabaceae", "2025-05-01")]
    assert rotation_conflict(history, "Solanaceae", "2026-05-01") is None


def test_rotation_conflict_is_none_when_matching_family_is_outside_the_lookback_window():
    history = [_planting("Solanaceae", "2023-05-01")]
    assert rotation_conflict(history, "Solanaceae", "2026-05-01", lookback_years=2) is None


def test_rotation_conflict_is_the_planting_when_matching_family_is_within_the_lookback_window():
    conflicting = _planting("Solanaceae", "2025-05-01")
    history = [conflicting]
    assert rotation_conflict(history, "Solanaceae", "2026-05-01", lookback_years=2) == conflicting


def test_rotation_conflict_holds_at_exactly_the_lookback_boundary():
    conflicting = _planting("Solanaceae", "2024-05-01")
    history = [conflicting]
    assert rotation_conflict(history, "Solanaceae", "2026-05-01", lookback_years=2) == conflicting


def test_rotation_conflict_is_none_one_year_past_the_lookback_boundary():
    history = [_planting("Solanaceae", "2023-05-01")]
    assert rotation_conflict(history, "Solanaceae", "2026-05-01", lookback_years=2) is None


def test_rotation_conflict_picks_the_most_recent_match_when_several_exist():
    older = _planting("Solanaceae", "2024-05-01", name="Roma")
    newer = _planting("Solanaceae", "2025-06-01", name="Cherokee Purple")
    history = [older, newer]
    assert rotation_conflict(history, "Solanaceae", "2026-05-01", lookback_years=2) == newer


def test_rotation_conflict_ignores_a_planting_later_than_the_new_planted_date():
    history = [_planting("Solanaceae", "2027-05-01")]
    assert rotation_conflict(history, "Solanaceae", "2026-05-01", lookback_years=2) is None
