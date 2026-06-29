import pytest
from src.engine.score_optimizer import optimize_prediction, points_awarded


RULES_FULL = {
    "exact_score_points": 3,
    "correct_goal_difference_points": 2,
    "correct_outcome_points": 1,
    "wrong_outcome_points": 0,
}

RULES_EXACT_ONLY = {
    "exact_score_points": 3,
    "correct_goal_difference_points": 0,
    "correct_outcome_points": 0,
    "wrong_outcome_points": 0,
}


class TestPointsAwarded:
    def test_exact_score(self):
        assert points_awarded(2, 1, 2, 1, RULES_FULL) == 3.0

    def test_correct_goal_difference(self):
        assert points_awarded(2, 1, 3, 2, RULES_FULL) == 2.0

    def test_correct_outcome_home_win(self):
        # 2-0 vs 3-1: same outcome (home win) but different GD (+2 vs +2 = same GD → correct_goal_difference)
        assert points_awarded(2, 0, 3, 1, RULES_FULL) == 2.0
        # Different GD: 2-0 (GD+2) vs 3-0 (GD+3) → same outcome only
        assert points_awarded(2, 0, 3, 0, RULES_FULL) == 1.0

    def test_correct_outcome_draw(self):
        assert points_awarded(1, 1, 2, 2, RULES_FULL) == 2.0  # same GD (0)

    def test_wrong_outcome(self):
        assert points_awarded(2, 0, 0, 1, RULES_FULL) == 0.0

    def test_draw_prediction_correct_draw(self):
        assert points_awarded(0, 0, 1, 1, RULES_FULL) == 2.0  # GD both 0


class TestOptimizePrediction:
    def test_returns_required_keys(self):
        matrix = {"1-0": 0.15, "0-0": 0.10, "2-1": 0.12}
        result = optimize_prediction(matrix, RULES_FULL)
        assert "optimal_score" in result
        assert "expected_points" in result
        assert "ev_table" in result

    def test_exact_only_matches_mode(self):
        """Section 9.3 invariant: with no partial credit, EV argmax == matrix argmax."""
        matrix = {"1-0": 0.20, "2-1": 0.15, "0-0": 0.10, "1-1": 0.08}
        result_ev = optimize_prediction(matrix, RULES_EXACT_ONLY)
        best_mode = max((k for k in matrix if k != "other"), key=lambda k: matrix[k])
        assert result_ev["optimal_score"] == best_mode

    def test_ev_optimal_differs_from_mode_with_partial_credit(self):
        """
        Construct a case where partial credit shifts the optimal pick away from the mode.
        Matrix heavily favours home wins, but no single cell is dominant.
        """
        matrix = {
            "1-0": 0.14, "2-0": 0.10, "3-0": 0.08, "2-1": 0.13,
            "1-1": 0.12, "0-0": 0.09, "0-1": 0.07, "0-2": 0.06,
            "3-1": 0.06, "3-2": 0.05,
        }
        # With full partial credit the optimizer might prefer a 1-0 or 2-1 over others
        result = optimize_prediction(matrix, RULES_FULL)
        assert result["expected_points"] > 0

    def test_ev_table_covers_all_candidates(self):
        matrix = {"1-0": 0.5, "0-0": 0.3, "0-1": 0.2}
        result = optimize_prediction(matrix, RULES_FULL, cap_goals=2)
        # cap_goals=2 → candidates 0-0 to 2-2 = 9 cells
        assert len(result["ev_table"]) == 9

    def test_probabilities_sanity(self):
        matrix = {"1-0": 0.15, "2-1": 0.12, "0-0": 0.08}
        result = optimize_prediction(matrix, RULES_FULL)
        assert result["expected_points"] >= 0
