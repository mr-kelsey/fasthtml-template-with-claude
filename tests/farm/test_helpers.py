from datetime import date

from farm.helpers import frost_exceeds_tolerance, frost_risk_windows, rotation_conflict

LAST_FROST = "2000-04-15"  # year is a placeholder -- only month/day are read
FIRST_FROST = "2000-10-15"


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


def test_frost_risk_windows_is_empty_when_tolerance_is_unset():
    windows = frost_risk_windows(date(2026, 4, 1), date(2026, 6, 1), None, LAST_FROST, FIRST_FROST)
    assert windows == []


def test_frost_risk_windows_is_empty_when_tolerance_is_hardy():
    windows = frost_risk_windows(date(2026, 4, 1), date(2026, 6, 1), "hardy", LAST_FROST, FIRST_FROST)
    assert windows == []


def test_frost_risk_windows_is_empty_when_last_frost_date_is_unset():
    windows = frost_risk_windows(date(2026, 4, 1), date(2026, 6, 1), "tender", None, FIRST_FROST)
    assert windows == []


def test_frost_risk_windows_is_empty_when_first_frost_date_is_unset():
    windows = frost_risk_windows(date(2026, 4, 1), date(2026, 6, 1), "tender", LAST_FROST, None)
    assert windows == []


def test_frost_risk_windows_is_empty_for_tender_planting_entirely_within_frost_free_window():
    windows = frost_risk_windows(date(2026, 5, 1), date(2026, 6, 1), "tender", LAST_FROST, FIRST_FROST)
    assert windows == []


def test_frost_risk_windows_returns_spring_window_for_tender_planted_before_last_frost():
    windows = frost_risk_windows(date(2026, 4, 1), date(2026, 6, 1), "tender", LAST_FROST, FIRST_FROST)
    assert windows == [(date(2026, 4, 1), date(2026, 4, 15))]


def test_frost_risk_windows_returns_fall_window_for_tender_maturing_after_first_frost():
    windows = frost_risk_windows(date(2026, 8, 1), date(2026, 11, 1), "tender", LAST_FROST, FIRST_FROST)
    assert windows == [(date(2026, 10, 15), date(2026, 11, 1))]


def test_frost_risk_windows_returns_both_windows_for_a_long_season_tender_planting():
    windows = frost_risk_windows(date(2026, 4, 1), date(2026, 11, 1), "tender", LAST_FROST, FIRST_FROST)
    assert windows == [(date(2026, 4, 1), date(2026, 4, 15)), (date(2026, 10, 15), date(2026, 11, 1))]


def test_frost_risk_windows_half_hardy_tolerates_within_buffer_of_last_frost():
    windows = frost_risk_windows(date(2026, 4, 5), date(2026, 6, 1), "half_hardy", LAST_FROST, FIRST_FROST)
    assert windows == []


def test_frost_risk_windows_half_hardy_still_warns_beyond_buffer_of_last_frost():
    windows = frost_risk_windows(date(2026, 3, 25), date(2026, 6, 1), "half_hardy", LAST_FROST, FIRST_FROST)
    assert windows == [(date(2026, 3, 25), date(2026, 4, 1))]


def test_frost_exceeds_tolerance_is_false_when_no_windows():
    assert frost_exceeds_tolerance(date(2026, 5, 1), date(2026, 6, 1), "tender", LAST_FROST, FIRST_FROST) is False


def test_frost_exceeds_tolerance_is_true_when_a_window_exists():
    assert frost_exceeds_tolerance(date(2026, 4, 1), date(2026, 6, 1), "tender", LAST_FROST, FIRST_FROST) is True
