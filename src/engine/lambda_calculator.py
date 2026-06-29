from typing import Optional
from src.models.team import Team


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def compute_elo_modifier(elo_a: float, elo_b: float, gamma: float) -> tuple[float, float]:
    e_a = 1.0 / (1.0 + 10.0 ** (-(elo_a - elo_b) / 400.0))
    e_b = 1.0 - e_a
    return 1.0 + gamma * (e_a - 0.5), 1.0 + gamma * (e_b - 0.5)


def compute_h2h_modifier(
    avg_goal_diff: Optional[float],
    matches_considered: int,
    h2h_weight: float,
    h2h_cap: float,
) -> tuple[float, float]:
    if avg_goal_diff is None or matches_considered < 2:
        return 1.0, 1.0
    norm = _clamp(avg_goal_diff / h2h_cap, -1.0, 1.0)
    return 1.0 + h2h_weight * norm, 1.0 + h2h_weight * (-norm)


def compute_home_advantage(
    team_code: str,
    host_nations: list[str],
    neutral_venue: bool,
    home_advantage_factor: float,
) -> float:
    if not neutral_venue and team_code in host_nations:
        return home_advantage_factor
    return 1.0


def compute_lambdas(
    team_a: Team,
    team_b: Team,
    host_nations: list[str],
    neutral_venue: bool,
    h2h_data: Optional[dict],
    config: dict,
) -> tuple[float, float]:
    mu = config["league_avg_goals"]
    gamma = config["rating_sensitivity_gamma"]
    h2h_weight = config["h2h_weight"]
    h2h_cap = config["h2h_normalization_cap"]
    home_adv_factor = config["home_advantage_factor"]
    lambda_min = config["lambda_min"]
    lambda_max = config["lambda_max"]

    rating_mod_a, rating_mod_b = compute_elo_modifier(team_a.elo_rating, team_b.elo_rating, gamma)

    h2h_avg_diff: Optional[float] = None
    h2h_matches = 0
    if h2h_data:
        h2h_avg_diff = h2h_data.get("avg_goal_diff_team1_minus_team2")
        h2h_matches = h2h_data.get("matches_considered", 0)
    h2h_mod_a, h2h_mod_b = compute_h2h_modifier(h2h_avg_diff, h2h_matches, h2h_weight, h2h_cap)

    both_hosts = team_a.code in host_nations and team_b.code in host_nations
    effective_neutral = neutral_venue or both_hosts
    home_adv_a = compute_home_advantage(team_a.code, host_nations, effective_neutral, home_adv_factor)
    home_adv_b = compute_home_advantage(team_b.code, host_nations, effective_neutral, home_adv_factor)

    lambda_a = mu * team_a.attack_strength * team_b.defense_strength * rating_mod_a * h2h_mod_a * home_adv_a
    lambda_b = mu * team_b.attack_strength * team_a.defense_strength * rating_mod_b * h2h_mod_b * home_adv_b

    return _clamp(lambda_a, lambda_min, lambda_max), _clamp(lambda_b, lambda_min, lambda_max)
