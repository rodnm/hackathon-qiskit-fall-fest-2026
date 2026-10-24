import math

import pytest

from qap import stats


def test_wilson_interval_known_value():
    low, high = stats.wilson_interval(5, 10)
    assert low == pytest.approx(0.2366, abs=1e-4)
    assert high == pytest.approx(0.7634, abs=1e-4)


def test_wilson_interval_edges():
    low, high = stats.wilson_interval(0, 10)
    assert low == 0.0 and 0 < high < 0.35
    assert all(math.isnan(v) for v in stats.wilson_interval(0, 0))


def test_random_floor_counts_one_hot_states():
    feasible, optimal = stats.random_floor(4, 2)
    assert feasible == pytest.approx(24 / 2**16)
    assert optimal == pytest.approx(2 / 2**16)


def test_shots_for_power_matches_the_planning_numbers():
    floor = 24 / 2**16  # planning used rounded z values (1.645, 0.842), hence the small tolerance
    assert stats.shots_for_power(floor, 2) == pytest.approx(21_948, rel=2e-3)
    assert stats.shots_for_power(floor, 3) == pytest.approx(6_571, rel=2e-3)


def test_binomial_vs_floor_is_one_sided():
    assert stats.binomial_vs_floor(0, 1000, 0.01) == pytest.approx(1.0)
    assert stats.binomial_vs_floor(30, 1000, 0.01) < 1e-6


def test_gap_follows_the_challenge_definition():
    assert stats.gap_pct(340, 10) == 0
    assert stats.gap_pct(346, 10) == pytest.approx(1.7647, abs=1e-4)
    assert stats.gap_pct(32, 4) is None  # the challenge gap is defined for the full instance only
    assert stats.gap_pct(None, 10) is None
    assert stats.gap_pct(math.nan, 10) is None


def test_gap_vs_control_is_a_separate_extension():
    assert stats.gap_vs_control_pct(42, 32) == pytest.approx(31.25)
    assert stats.gap_vs_control_pct(None, 32) is None
