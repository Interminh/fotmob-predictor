import math


def rounded_scoreline(lambda_home: float, lambda_away: float) -> str:
    """Nearest-integer scoreline from the raw expected goals (round-half-up).

    Unlike the joint-probability mode (the single most-likely cell), this
    tracks the mean of each side's Poisson distribution rather than its
    mode, which floors away the fractional part of both lambdas. For
    skewed goal distributions the mode systematically undershoots real
    goal totals; rounding the lambdas directly doesn't.
    """
    home = math.floor(lambda_home + 0.5)
    away = math.floor(lambda_away + 0.5)
    return f"{home}-{away}"


def _sign(x: int) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def _parse_score(score_str: str) -> tuple[int, int]:
    h, a = score_str.split("-")
    return int(h), int(a)


def points_awarded(p_h: int, p_a: int, a_h: int, a_a: int, scoring_rules: dict) -> float:
    if p_h == a_h and p_a == a_a:
        return float(scoring_rules["exact_score_points"])
    gd_pts = float(scoring_rules["correct_goal_difference_points"])
    outcome_pts = float(scoring_rules["correct_outcome_points"])
    # Only apply the GD check if it awards more than the outcome check.
    # When GD_pts <= outcome_pts (e.g. GD=0, outcome=2), a same-GD result
    # should still earn outcome points — skipping the GD trap.
    if gd_pts > outcome_pts and (p_h - p_a) == (a_h - a_a):
        return gd_pts
    if _sign(p_h - p_a) == _sign(a_h - a_a):
        return outcome_pts
    return float(scoring_rules["wrong_outcome_points"])


def optimize_prediction(
    score_matrix: dict[str, float],
    scoring_rules: dict,
    cap_goals: int = 6,
) -> dict:
    candidates = [(h, a) for h in range(cap_goals + 1) for a in range(cap_goals + 1)]
    ev_table: dict[str, float] = {}

    for p_h, p_a in candidates:
        ev = 0.0
        for score_str, prob in score_matrix.items():
            if score_str == "other":
                continue
            a_h, a_a = _parse_score(score_str)
            ev += prob * points_awarded(p_h, p_a, a_h, a_a, scoring_rules)
        ev_table[f"{p_h}-{p_a}"] = ev

    best = max(ev_table, key=lambda k: ev_table[k])
    return {
        "optimal_score": best,
        "expected_points": round(ev_table[best], 4),
        "ev_table": {k: round(v, 4) for k, v in ev_table.items()},
    }
