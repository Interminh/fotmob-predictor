from typing import Optional
import numpy as np


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def simulate_extra_time(
    lambda_home: float,
    lambda_away: float,
    n_drawn: int,
    config: dict,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    et_fraction = config["extra_time_minutes_fraction"]
    et_home = rng.poisson(lambda_home * et_fraction, size=n_drawn)
    et_away = rng.poisson(lambda_away * et_fraction, size=n_drawn)
    return et_home, et_away


def simulate_penalties(
    team_a_elo: float,
    team_b_elo: float,
    n_shootouts: int,
    config: dict,
    rng: np.random.Generator,
) -> np.ndarray:
    e_a = 1.0 / (1.0 + 10.0 ** (-(team_a_elo - team_b_elo) / 400.0))
    p_a_wins = 0.5 + config["penalty_skill_factor"] * (e_a - 0.5)
    p_a_wins = _clamp(p_a_wins, 0.35, 0.65)
    return rng.random(n_shootouts) < p_a_wins


def resolve_knockout(
    home_goals: np.ndarray,
    away_goals: np.ndarray,
    team_a_elo: float,
    team_b_elo: float,
    lambda_home: float,
    lambda_away: float,
    config: dict,
    seed: Optional[int] = None,
) -> dict:
    rng = np.random.default_rng(seed)
    n = len(home_goals)

    drawn_90 = home_goals == away_goals
    n_drawn_90 = int(drawn_90.sum())

    et_home = np.zeros(n, dtype=np.int64)
    et_away = np.zeros(n, dtype=np.int64)

    if n_drawn_90 > 0:
        et_h, et_a = simulate_extra_time(lambda_home, lambda_away, n_drawn_90, config, rng)
        et_home[drawn_90] = et_h
        et_away[drawn_90] = et_a

    total_home = home_goals + et_home
    total_away = away_goals + et_away

    drawn_after_et = total_home == total_away
    n_drawn_et = int(drawn_after_et.sum())

    pen_home_advances = np.zeros(n, dtype=bool)
    if n_drawn_et > 0:
        pen_result = simulate_penalties(team_a_elo, team_b_elo, n_drawn_et, config, rng)
        pen_home_advances[drawn_after_et] = pen_result

    home_advances = (total_home > total_away) | pen_home_advances

    return {
        "drawn_after_90min_probability": float(n_drawn_90 / n),
        "drawn_after_120min_probability": float(n_drawn_et / n),
        "home_advances_probability": float(home_advances.mean()),
        "away_advances_probability": float((~home_advances).mean()),
        "home_goals_90": home_goals,
        "away_goals_90": away_goals,
        "home_goals_120": total_home,
        "away_goals_120": total_away,
    }
