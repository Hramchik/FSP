"""The CAT stop rule decides a grade, so it is tested against grade boundaries."""
from app.domain.irt import (
    EXTENDED_MAX_ITEMS,
    MAX_ITEMS,
    MIN_ITEMS,
    boundary_margin,
    grade_for_theta,
    grade_is_decided,
    should_stop,
)


def test_never_stops_before_the_minimum():
    assert should_stop(MIN_ITEMS - 1, theta=0.0, se=0.01) is False


def test_stops_when_precise_and_far_from_a_boundary():
    # θ = 1.2 sits in the middle of the senior band.
    assert should_stop(MIN_ITEMS, theta=1.2, se=0.25) is True


def test_keeps_asking_while_theta_sits_on_a_boundary():
    # θ = 0.7 is exactly the middle/senior boundary: SE alone would stop here.
    assert should_stop(MIN_ITEMS, theta=0.7, se=0.25) is False
    assert grade_is_decided(0.7, 0.25) is False


def test_relaxes_the_margin_after_the_standard_cap():
    assert should_stop(MAX_ITEMS, theta=0.88, se=0.3) is True


def test_hard_cap_always_stops():
    assert should_stop(EXTENDED_MAX_ITEMS, theta=0.7, se=0.9) is True


def test_boundary_margin_matches_the_grade_thresholds():
    assert boundary_margin(0.7) == 0.0
    assert boundary_margin(1.25) == 0.55
    assert grade_for_theta(1.25) == "senior"


def test_saturated_measurement_runs_to_the_standard_cap_not_past_it():
    """θ, упёршееся в край шкалы, не должно тянуть попытку до жёсткого предела."""
    from app.domain.irt import THETA_MAX, measurement_saturated

    assert measurement_saturated(THETA_MAX) is True
    assert measurement_saturated(1.2) is False
    # SE у предельного паттерна остаётся высоким, поэтому обычные правила молчат.
    assert should_stop(MIN_ITEMS, theta=THETA_MAX, se=0.6) is False
    assert should_stop(MAX_ITEMS, theta=THETA_MAX, se=0.6) is True


def test_theta_never_leaves_the_measurable_range():
    from app.domain.irt import THETA_MAX, THETA_MIN, estimate_theta

    all_correct = [(1, 2.5, 2.6)] * 20
    all_wrong = [(0, 2.5, -1.5)] * 20
    assert estimate_theta(all_correct).theta <= THETA_MAX
    assert estimate_theta(all_wrong).theta >= THETA_MIN


def test_extreme_patterns_are_recognised():
    from app.domain.irt import extreme_pattern

    assert extreme_pattern([(1, 2.0, 0.0)] * 8) == "all_correct"
    assert extreme_pattern([(0, 2.0, 0.0)] * 8) == "all_wrong"
    assert extreme_pattern([(1, 2.0, 0.0), (0, 2.0, 0.0)]) is None
    assert extreme_pattern([]) is None


# --- вердикт одной попытки -------------------------------------------------

def verdict(requested, theta, se, pattern=None, answered=12):
    from app.api.testing import _verdict
    return _verdict(requested, theta, se, pattern, answered)


def test_theta_inside_the_requested_band_confirms_it():
    assert verdict("middle", theta=0.3, se=0.25) == ("middle", None)


def test_theta_above_the_band_recommends_the_next_grade_without_confirming():
    assert verdict("middle", theta=1.5, se=0.22) == (None, "senior")


def test_theta_below_the_band_confirms_nothing_and_recommends_nothing():
    # Грейд не понижается принудительно: кандидату предлагается тест уровнем ниже.
    assert verdict("middle", theta=-1.6, se=0.25) == (None, None)


def test_imprecise_measurement_never_confirms():
    assert verdict("middle", theta=0.3, se=0.6) == (None, None)


def test_perfect_run_confirms_and_recommends_higher():
    assert verdict("middle", theta=3.5, se=0.9, pattern="all_correct") == ("middle", "senior")


def test_perfect_run_at_the_top_grade_has_nothing_to_recommend():
    assert verdict("lead", theta=3.5, se=0.9, pattern="all_correct") == ("lead", None)


def test_failed_run_confirms_nothing_even_though_se_is_uninterpretable():
    assert verdict("middle", theta=-3.0, se=0.76, pattern="all_wrong") == (None, None)


def test_extreme_pattern_below_the_minimum_falls_back_to_the_normal_rule():
    # Четыре верных ответа — ещё не доказательство, работает обычная проверка по SE.
    assert verdict("middle", theta=3.5, se=0.9, pattern="all_correct", answered=4) == (None, None)
