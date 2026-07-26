from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional

from src.config import DATA_DIR, DEFAULT_CONFIG
from src.engine.lambda_calculator import compute_lambdas
from src.engine.monte_carlo import simulate_match_raw, outcome_probabilities
from src.models.team import Team, RecentForm

OUTCOMES = ("home_win", "draw", "away_win")


def _actual_outcome(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "home_win"
    if home_score < away_score:
        return "away_win"
    return "draw"


def _one_hot(outcome: str) -> dict[str, float]:
    return {o: (1.0 if o == outcome else 0.0) for o in OUTCOMES}


def _brier_score(probs: dict[str, float], actual: str) -> float:
    y = _one_hot(actual)
    return sum((probs[o] - y[o]) ** 2 for o in OUTCOMES)


def _log_loss(probs: dict[str, float], actual: str, eps: float = 1e-9) -> float:
    p = max(probs[actual], eps)
    return -math.log(p)


def uniform_baseline(_home_rating: float, _away_rating: float) -> dict[str, float]:
    return {"home_win": 1 / 3, "draw": 1 / 3, "away_win": 1 / 3}


def favorite_sign_baseline(home_rating: float, away_rating: float) -> dict[str, float]:
    """Knows only which side is rated higher, not by how much."""
    if home_rating > away_rating:
        return {"home_win": 0.50, "draw": 0.25, "away_win": 0.25}
    if away_rating > home_rating:
        return {"home_win": 0.25, "draw": 0.25, "away_win": 0.50}
    return {"home_win": 1 / 3, "draw": 1 / 3, "away_win": 1 / 3}


BASELINES = {
    "uniform": uniform_baseline,
    "favorite_sign_only": favorite_sign_baseline,
}


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _make_team(code: str, rating: float, is_host: bool) -> Team:
    return Team(
        code=code,
        name=code,
        confederation="",
        fifa_ranking=0,
        elo_rating=rating,
        recent_form=RecentForm(0.0, 0.0, 0),
        attack_strength=1.0,
        defense_strength=1.0,
        is_host_nation=is_host,
    )


def run_backtest(
    teams_path: Optional[Path] = None,
    matches_path: Optional[Path] = None,
    config: Optional[dict] = None,
    n_simulations: int = 10_000,
    seed: Optional[int] = 42,
) -> dict:
    teams_path = teams_path or DATA_DIR / "historical" / "wc2022_teams.json"
    matches_path = matches_path or DATA_DIR / "historical" / "wc2022_matches.json"
    cfg = {**DEFAULT_CONFIG, **(config or {})}

    teams_raw = _load_json(teams_path)["teams"]
    match_data = _load_json(matches_path)
    host_nations = match_data["host_nations"]
    matches = match_data["matches"]

    per_match = []
    for m in matches:
        home_code, away_code = m["home"], m["away"]
        home_rating = teams_raw[home_code]["fifa_points"]
        away_rating = teams_raw[away_code]["fifa_points"]

        team_a = _make_team(home_code, home_rating, home_code in host_nations)
        team_b = _make_team(away_code, away_rating, away_code in host_nations)

        lam_h, lam_a = compute_lambdas(
            team_a, team_b, host_nations, m["neutral_venue"], None, cfg
        )
        home_g, away_g = simulate_match_raw(lam_h, lam_a, n_simulations, seed)
        model_probs = outcome_probabilities(home_g, away_g)

        actual = _actual_outcome(m["home_score_90"], m["away_score_90"])

        row = {
            "match_id": m["match_id"],
            "stage": m["stage"],
            "home": home_code,
            "away": away_code,
            "actual_outcome": actual,
            "actual_score": f"{m['home_score_90']}-{m['away_score_90']}",
            "lambda_home": round(lam_h, 3),
            "lambda_away": round(lam_a, 3),
            "model": model_probs,
            "model_brier": _brier_score(model_probs, actual),
            "model_log_loss": _log_loss(model_probs, actual),
            "model_correct": int(max(model_probs, key=model_probs.get) == actual),
        }
        for name, fn in BASELINES.items():
            bp = fn(home_rating, away_rating)
            row[f"{name}_brier"] = _brier_score(bp, actual)
            row[f"{name}_log_loss"] = _log_loss(bp, actual)
            row[f"{name}_correct"] = int(max(bp, key=bp.get) == actual)

        per_match.append(row)

    def _summary(prefix: str) -> dict:
        n = len(per_match)
        return {
            "brier_score": round(sum(r[f"{prefix}_brier"] for r in per_match) / n, 4),
            "log_loss": round(sum(r[f"{prefix}_log_loss"] for r in per_match) / n, 4),
            "accuracy": round(sum(r[f"{prefix}_correct"] for r in per_match) / n, 4),
        }

    summary = {"model": _summary("model")}
    for name in BASELINES:
        summary[name] = _summary(name)

    stage_summary = {}
    stages = sorted(set(r["stage"] for r in per_match), key=lambda s: [m["stage"] for m in matches].index(s))
    for stage in stages:
        rows = [r for r in per_match if r["stage"] == stage]
        n = len(rows)
        stage_summary[stage] = {
            "n_matches": n,
            "model_accuracy": round(sum(r["model_correct"] for r in rows) / n, 4),
            "model_brier": round(sum(r["model_brier"] for r in rows) / n, 4),
        }

    worst = sorted(per_match, key=lambda r: r["model_log_loss"], reverse=True)[:5]

    return {
        "n_matches": len(per_match),
        "summary": summary,
        "stage_summary": stage_summary,
        "worst_calls": worst,
        "per_match": per_match,
    }
