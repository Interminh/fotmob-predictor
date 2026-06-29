from collections import Counter
from typing import Optional
import numpy as np


def simulate_match_raw(
    lambda_home: float,
    lambda_away: float,
    n_simulations: int = 10_000,
    seed: Optional[int] = None,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    home_goals = rng.poisson(lambda_home, size=n_simulations)
    away_goals = rng.poisson(lambda_away, size=n_simulations)
    return home_goals, away_goals


def build_score_matrix(
    home_goals: np.ndarray,
    away_goals: np.ndarray,
    cap_display_goals: int = 8,
) -> dict[str, float]:
    n = len(home_goals)
    counts: Counter = Counter(zip(home_goals.tolist(), away_goals.tolist()))
    matrix: dict[str, float] = {}
    for (h, a), c in counts.items():
        key = f"{h}-{a}" if h <= cap_display_goals and a <= cap_display_goals else "other"
        matrix[key] = matrix.get(key, 0.0) + c / n
    return matrix


def outcome_probabilities(
    home_goals: np.ndarray,
    away_goals: np.ndarray,
) -> dict[str, float]:
    return {
        "home_win": float(np.mean(home_goals > away_goals)),
        "draw": float(np.mean(home_goals == away_goals)),
        "away_win": float(np.mean(home_goals < away_goals)),
    }


def top_n_scores(score_matrix: dict[str, float], n: int = 3) -> list[dict]:
    scored = [(k, v) for k, v in score_matrix.items() if k != "other"]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [{"score": k, "probability": round(v, 6)} for k, v in scored[:n]]
