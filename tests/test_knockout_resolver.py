import numpy as np
import pytest

from src.engine.knockout_resolver import simulate_extra_time, simulate_penalties, resolve_knockout
from src.config import DEFAULT_CONFIG


class TestSimulatePenalties:
    def test_probability_clamped_extreme_elo(self):
        """Shootout p must stay within [0.35, 0.65] even for huge Elo gaps."""
        rng = np.random.default_rng(0)
        results = simulate_penalties(3000.0, 1000.0, 100_000, DEFAULT_CONFIG, rng)
        p_a_wins = float(results.mean())
        assert 0.35 <= p_a_wins <= 0.65 + 0.02  # generous tolerance for finite N

    def test_symmetric_near_50_50(self):
        rng = np.random.default_rng(1)
        results = simulate_penalties(2000.0, 2000.0, 100_000, DEFAULT_CONFIG, rng)
        p = float(results.mean())
        assert abs(p - 0.5) < 0.01


class TestSimulateExtraTime:
    def test_output_lengths(self):
        rng = np.random.default_rng(0)
        et_h, et_a = simulate_extra_time(1.5, 1.0, 100, DEFAULT_CONFIG, rng)
        assert len(et_h) == 100
        assert len(et_a) == 100

    def test_non_negative(self):
        rng = np.random.default_rng(2)
        et_h, et_a = simulate_extra_time(1.5, 1.0, 1000, DEFAULT_CONFIG, rng)
        assert (et_h >= 0).all()
        assert (et_a >= 0).all()

    def test_goals_lower_than_regulation(self):
        rng = np.random.default_rng(3)
        et_h, et_a = simulate_extra_time(1.5, 1.5, 10_000, DEFAULT_CONFIG, rng)
        assert et_h.mean() < 1.5


class TestResolveKnockout:
    def test_probabilities_sum_to_one(self):
        home_g = np.array([1, 1, 0, 2, 1])
        away_g = np.array([1, 0, 1, 1, 2])
        result = resolve_knockout(home_g, away_g, 2000.0, 1950.0, 1.5, 1.2, DEFAULT_CONFIG, seed=0)
        total = result["home_advances_probability"] + result["away_advances_probability"]
        assert total == pytest.approx(1.0, abs=1e-9)

    def test_drawn_after_90_only_for_equal_scores(self):
        home_g = np.array([1, 1, 1, 1])
        away_g = np.array([1, 1, 1, 1])
        result = resolve_knockout(home_g, away_g, 2000.0, 2000.0, 1.0, 1.0, DEFAULT_CONFIG, seed=5)
        assert result["drawn_after_90min_probability"] == pytest.approx(1.0, abs=1e-9)

    def test_no_draw_after_90_when_all_decided(self):
        home_g = np.array([2, 3, 1, 4])
        away_g = np.array([1, 1, 0, 2])
        result = resolve_knockout(home_g, away_g, 2000.0, 1900.0, 2.0, 1.0, DEFAULT_CONFIG, seed=6)
        assert result["drawn_after_90min_probability"] == pytest.approx(0.0, abs=1e-9)
        assert result["home_advances_probability"] == pytest.approx(1.0, abs=1e-9)
