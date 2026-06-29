import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from src.models.result import SimulationResult
from src.config import OUTPUTS_DIR


def _result_to_dict(r: SimulationResult) -> dict:
    d = asdict(r)
    d["outcome_probabilities"] = {
        "home_win": r.outcome_probabilities.home_win,
        "draw": r.outcome_probabilities.draw,
        "away_win": r.outcome_probabilities.away_win,
    }
    d["optimal_prediction"] = {
        "score": r.optimal_prediction.score,
        "expected_points": r.optimal_prediction.expected_points,
        "note": r.optimal_prediction.note,
    }
    d["top_3_scores"] = [{"score": s.score, "probability": s.probability} for s in r.top_3_scores]
    if r.knockout_resolution:
        ko = r.knockout_resolution
        d["knockout_resolution"] = {
            "drawn_after_90min_probability": ko.drawn_after_90min_probability,
            "drawn_after_120min_probability": ko.drawn_after_120min_probability,
            "home_advances_probability": ko.home_advances_probability,
            "away_advances_probability": ko.away_advances_probability,
            "score_reference_used": ko.score_reference_used,
        }
    else:
        d["knockout_resolution"] = None
    d.pop("score_matrix", None)
    return d


def export_results_json(results: list[SimulationResult], path: Optional[Path] = None) -> Path:
    path = path or OUTPUTS_DIR / "predictions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [_result_to_dict(r) for r in results]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path


def export_results_csv(results: list[SimulationResult], path: Optional[Path] = None) -> Path:
    path = path or OUTPUTS_DIR / "tournament_summary.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for r in results:
        top = r.top_3_scores
        rows.append({
            "match_id": r.match_id,
            "home": r.home_team,
            "away": r.away_team,
            "lambda_home": round(r.lambda_home, 4),
            "lambda_away": round(r.lambda_away, 4),
            "top1_score": top[0].score if len(top) > 0 else "",
            "top1_prob": top[0].probability if len(top) > 0 else "",
            "top2_score": top[1].score if len(top) > 1 else "",
            "top2_prob": top[1].probability if len(top) > 1 else "",
            "top3_score": top[2].score if len(top) > 2 else "",
            "top3_prob": top[2].probability if len(top) > 2 else "",
            "optimal_pick": r.optimal_prediction.score,
            "expected_points": r.optimal_prediction.expected_points,
            "home_win_pct": round(r.outcome_probabilities.home_win * 100, 1),
            "draw_pct": round(r.outcome_probabilities.draw * 100, 1),
            "away_win_pct": round(r.outcome_probabilities.away_win * 100, 1),
        })
    if not rows:
        return path
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


def export_advancement_json(adv: dict, path: Optional[Path] = None) -> Path:
    path = path or OUTPUTS_DIR / "advancement_probabilities.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(adv, f, indent=2)
    return path


def export_heatmap(
    score_matrix: dict[str, float],
    home_team: str,
    away_team: str,
    match_id: str,
    path: Optional[Path] = None,
    cap: int = 7,
) -> Path:
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        raise ImportError("matplotlib is required for heatmap export: pip install matplotlib")

    path = path or OUTPUTS_DIR / f"heatmap_{match_id}.png"
    path.parent.mkdir(parents=True, exist_ok=True)

    matrix = np.zeros((cap, cap))
    for h in range(cap):
        for a in range(cap):
            matrix[h, a] = score_matrix.get(f"{h}-{a}", 0.0)

    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto")
    plt.colorbar(im, ax=ax, label="Probability")
    ax.set_xticks(range(cap))
    ax.set_yticks(range(cap))
    ax.set_xticklabels(range(cap))
    ax.set_yticklabels(range(cap))
    ax.set_xlabel(f"{away_team} Goals")
    ax.set_ylabel(f"{home_team} Goals")
    ax.set_title(f"{home_team} vs {away_team} — Score Probability Matrix")

    for h in range(cap):
        for a in range(cap):
            val = matrix[h, a]
            if val > 0.005:
                ax.text(a, h, f"{val:.1%}", ha="center", va="center", fontsize=7)

    fig.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)
    return path
