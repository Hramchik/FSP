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
