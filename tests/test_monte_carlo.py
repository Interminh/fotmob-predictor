import numpy as np
import pytest
import scipy.stats

from src.engine.monte_carlo import simulate_match_raw, build_score_matrix, outcome_probabilities, top_n_scores


class TestSimulateMatchRaw:
    def test_output_shape(self):
        h, a = simulate_match_raw(1.2, 0.9, n_simulations=1000, seed=0)
        assert h.shape == (1000,)
        assert a.shape == (1000,)

    def test_non_negative(self):
        h, a = simulate_match_raw(1.5, 1.1, n_simulations=5000, seed=1)
        assert (h >= 0).all()
        assert (a >= 0).all()

    def test_reproducible_with_seed(self):
        h1, a1 = simulate_match_raw(1.4, 0.9, n_simulations=500, seed=42)
        h2, a2 = simulate_match_raw(1.4, 0.9, n_simulations=500, seed=42)
        np.testing.assert_array_equal(h1, h2)
        np.testing.assert_array_equal(a1, a2)


class TestBuildScoreMatrix:
    def test_sums_to_one(self):
        h, a = simulate_match_raw(1.3, 1.0, n_simulations=10_000, seed=7)
        matrix = build_score_matrix(h, a)
        total = sum(matrix.values())
        assert total == pytest.approx(1.0, abs=1e-9)

    def test_other_bucket(self):
        # All goals capped at 0 to force "other" is never added (cap=100 means nothing is "other")
        h = np.array([9, 10, 11])
        a = np.array([0, 0, 0])
        matrix = build_score_matrix(h, a, cap_display_goals=8)
        assert "other" in matrix


class TestOutcomeProbabilities:
    def test_sums_to_one(self):
        h, a = simulate_match_raw(1.5, 1.0, n_simulations=10_000, seed=3)
        probs = outcome_probabilities(h, a)
        total = probs["home_win"] + probs["draw"] + probs["away_win"]
        assert total == pytest.approx(1.0, abs=1e-9)

    def test_favourite_wins_more(self):
        h, a = simulate_match_raw(2.5, 0.5, n_simulations=10_000, seed=4)
        probs = outcome_probabilities(h, a)
        assert probs["home_win"] > probs["away_win"]


class TestMonteCarloCovergesToAnalytical:
    """Section 9.2 cross-check: simulated matrix should match SciPy closed-form PMF."""

    def test_convergence_within_tolerance(self):
        lam_h, lam_a = 1.4, 0.9
        home, away = simulate_match_raw(lam_h, lam_a, n_simulations=200_000, seed=42)
        simulated = build_score_matrix(home, away, cap_display_goals=20)

        for h in range(7):
            for a in range(7):
                analytical = (
                    scipy.stats.poisson.pmf(h, lam_h) * scipy.stats.poisson.pmf(a, lam_a)
                )
                simulated_p = simulated.get(f"{h}-{a}", 0.0)
                assert abs(simulated_p - analytical) < 0.01, (
                    f"Cell {h}-{a}: analytical={analytical:.5f}, simulated={simulated_p:.5f}"
                )


class TestTopNScores:
    def test_returns_n_entries(self):
        matrix = {"1-0": 0.15, "0-0": 0.10, "2-1": 0.12, "other": 0.01}
        top = top_n_scores(matrix, n=3)
        assert len(top) == 3

    def test_sorted_descending(self):
        matrix = {"1-0": 0.15, "0-0": 0.10, "2-1": 0.12}
        top = top_n_scores(matrix, n=3)
        probs = [e["probability"] for e in top]
        assert probs == sorted(probs, reverse=True)

    def test_excludes_other(self):
        matrix = {"1-0": 0.80, "other": 0.20}
        top = top_n_scores(matrix, n=3)
        assert all(e["score"] != "other" for e in top)
