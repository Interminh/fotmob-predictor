import pytest
from src.engine.lambda_calculator import (
    compute_elo_modifier,
    compute_h2h_modifier,
    compute_home_advantage,
    compute_lambdas,
)
from src.config import DEFAULT_CONFIG
from src.models.team import Team, RecentForm


def _make_team(code: str, atk: float, def_: float, elo: float, host: bool = False) -> Team:
    return Team(
        code=code, name=code, confederation="TEST",
        fifa_ranking=10, elo_rating=elo,
        recent_form=RecentForm(13.5, 13.5, 10),
        attack_strength=atk, defense_strength=def_,
        is_host_nation=host,
    )


class TestEloModifier:
    def test_equal_elo_returns_1_0(self):
        mod_a, mod_b = compute_elo_modifier(2000.0, 2000.0, 0.30)
        assert mod_a == pytest.approx(1.0, abs=1e-9)
        assert mod_b == pytest.approx(1.0, abs=1e-9)

    def test_sums_to_2(self):
        mod_a, mod_b = compute_elo_modifier(2100.0, 1900.0, 0.30)
        assert mod_a + mod_b == pytest.approx(2.0, abs=1e-9)

    def test_stronger_team_gets_boost(self):
        mod_a, mod_b = compute_elo_modifier(2100.0, 1900.0, 0.30)
        assert mod_a > 1.0
        assert mod_b < 1.0

    def test_gamma_zero_returns_1_0(self):
        mod_a, mod_b = compute_elo_modifier(2100.0, 1800.0, 0.0)
        assert mod_a == pytest.approx(1.0, abs=1e-9)
        assert mod_b == pytest.approx(1.0, abs=1e-9)

    def test_max_swing_capped(self):
        mod_a, _ = compute_elo_modifier(9999.0, 0.0, 0.30)
        assert mod_a < 1.16  # γ=0.30 → max ~1.15


class TestH2HModifier:
    def test_fewer_than_2_matches_returns_1(self):
        m_a, m_b = compute_h2h_modifier(1.0, 1, 0.08, 3.0)
        assert m_a == 1.0 and m_b == 1.0

    def test_zero_diff_returns_1(self):
        m_a, m_b = compute_h2h_modifier(0.0, 5, 0.08, 3.0)
        assert m_a == pytest.approx(1.0)
        assert m_b == pytest.approx(1.0)

    def test_positive_diff_boosts_a(self):
        m_a, m_b = compute_h2h_modifier(1.5, 5, 0.08, 3.0)
        assert m_a > 1.0
        assert m_b < 1.0

    def test_capped_at_8_percent(self):
        m_a, m_b = compute_h2h_modifier(99.0, 5, 0.08, 3.0)
        assert m_a == pytest.approx(1.08, abs=1e-9)
        assert m_b == pytest.approx(0.92, abs=1e-9)

    def test_no_h2h_data_returns_1(self):
        m_a, m_b = compute_h2h_modifier(None, 0, 0.08, 3.0)
        assert m_a == 1.0 and m_b == 1.0


class TestHomeAdvantage:
    def test_host_at_home(self):
        assert compute_home_advantage("USA", ["USA", "MEX", "CAN"], False, 1.08) == pytest.approx(1.08)

    def test_host_at_neutral(self):
        assert compute_home_advantage("USA", ["USA", "MEX", "CAN"], True, 1.08) == 1.0

    def test_non_host_no_advantage(self):
        assert compute_home_advantage("ARG", ["USA", "MEX", "CAN"], False, 1.08) == 1.0


class TestComputeLambdas:
    def test_symmetric_equal_teams(self):
        team = _make_team("X", 1.0, 1.0, 2000.0)
        lam_h, lam_a = compute_lambdas(team, team, [], True, None, DEFAULT_CONFIG)
        assert lam_h == pytest.approx(lam_a, rel=1e-6)

    def test_clamped_at_min(self):
        weak = _make_team("W", 0.001, 10.0, 1000.0)
        strong = _make_team("S", 10.0, 0.001, 3000.0)
        _, lam_b = compute_lambdas(strong, weak, [], True, None, DEFAULT_CONFIG)
        assert lam_b >= DEFAULT_CONFIG["lambda_min"]

    def test_clamped_at_max(self):
        strong = _make_team("S", 10.0, 0.001, 3000.0)
        weak = _make_team("W", 0.001, 10.0, 1000.0)
        lam_h, _ = compute_lambdas(strong, weak, [], True, None, DEFAULT_CONFIG)
        assert lam_h <= DEFAULT_CONFIG["lambda_max"]

    def test_host_nation_gets_boost_at_home(self):
        host = _make_team("USA", 1.0, 1.0, 2000.0, host=True)
        visitor = _make_team("ARG", 1.0, 1.0, 2000.0, host=False)
        lam_host, lam_visitor = compute_lambdas(host, visitor, ["USA"], False, None, DEFAULT_CONFIG)
        assert lam_host > lam_visitor

    def test_both_host_nations_treated_as_neutral(self):
        usa = _make_team("USA", 1.0, 1.0, 2000.0, host=True)
        mex = _make_team("MEX", 1.0, 1.0, 2000.0, host=True)
        lam_a, lam_b = compute_lambdas(usa, mex, ["USA", "MEX", "CAN"], False, None, DEFAULT_CONFIG)
        assert lam_a == pytest.approx(lam_b, rel=1e-6)
