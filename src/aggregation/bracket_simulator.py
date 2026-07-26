from collections import defaultdict
from typing import Optional
import numpy as np

from src.aggregation.group_standings import compute_group_standings
from src.engine.lambda_calculator import compute_lambdas
from src.engine.knockout_resolver import _clamp
from src.models.team import Team
from src.models.match import Match, Stage


def _parse_depends_on(ref: str) -> tuple[str, str]:
    """Parse 'R32_1_winner' into ('R32_1', 'winner')."""
    parts = ref.rsplit("_", 1)
    return parts[0], parts[1]  # (match_id, role)


def _resolve_slot(ref: str, match_results: dict) -> Optional[str]:
    """Return team code for a depends_on ref, or None if not yet resolved."""
    mid, role = _parse_depends_on(ref)
    result = match_results.get(mid)
    if result is None:
        return None
    return result.get(role)


def simulate_from_knockout(
    teams: dict[str, Team],
    h2h: dict[str, dict],
    knockout_stages: list[Stage],
    host_nations: list[str],
    config: dict,
    n_trials: int = 100_000,
    seed: Optional[int] = None,
) -> dict:
    """
    Simulate bracket from a set of knockout stages (e.g. starting at Round of 32).

    Completed matches (status='completed' with final_score) use their known result.
    TBD slots are resolved via depends_on references.

    Returns:
        {"team_code": {"round_of_32": p, "round_of_16": p, ...}}
    """
    from src.io.loader import get_h2h_data

    rng = np.random.default_rng(seed)

    stage_keys = [
        s.stage_name.lower().replace(" ", "_").replace("-", "_").replace(" ", "_")
        for s in knockout_stages
    ]

    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    # Pre-index all matches by match_id for O(1) lookup
    all_matches: dict[str, tuple[Match, str]] = {}  # match_id → (match, stage_key)
    for stage, sk in zip(knockout_stages, stage_keys):
        for m in stage.matches:
            all_matches[m.match_id] = (m, sk)

    for _ in range(n_trials):
        match_results: dict[str, dict[str, str]] = {}

        # completed matches are fixed, same result every trial
        for mid, (m, _) in all_matches.items():
            if m.status == "completed" and m.final_score is not None:
                fs = m.final_score
                if fs["home"] > fs["away"]:
                    match_results[mid] = {"winner": m.home, "loser": m.away}
                elif fs["away"] > fs["home"]:
                    match_results[mid] = {"winner": m.away, "loser": m.home}
                # Draws at 90min shouldn't appear in completed knockouts, but handle anyway
                else:
                    match_results[mid] = {"winner": m.home, "loser": m.away}

        # Simulate each stage in order
        for stage, stage_key in zip(knockout_stages, stage_keys):
            for m in stage.matches:
                if m.match_id in match_results:
                    # Already resolved (completed match)
                    winner = match_results[m.match_id]["winner"]
                    counts[winner][stage_key] += 1
                    continue

                # Resolve home/away slots
                home_code = m.home
                away_code = m.away

                if m.depends_on and len(m.depends_on) >= 2:
                    home_code = _resolve_slot(m.depends_on[0], match_results) or home_code
                    away_code = _resolve_slot(m.depends_on[1], match_results) or away_code

                if home_code not in teams or away_code not in teams:
                    continue  # slot not resolved yet, skip

                ta = teams[home_code]
                tb = teams[away_code]
                h2h_d = get_h2h_data(home_code, away_code, h2h)

                winner, loser = _simulate_one_match(
                    ta, tb, host_nations, m.neutral_venue, h2h_d, config, True, rng
                )
                match_results[m.match_id] = {"winner": winner, "loser": loser}
                counts[winner][stage_key] += 1

    # Normalise
    result: dict[str, dict[str, float]] = {}
    for code in teams:
        if counts[code]:
            result[code] = {k: round(v / n_trials, 5) for k, v in counts[code].items()}
        else:
            result[code] = {}
    return result


def _simulate_one_match(
    team_a: Team,
    team_b: Team,
    host_nations: list[str],
    neutral_venue: bool,
    h2h_data: Optional[dict],
    config: dict,
    is_knockout: bool,
    rng: np.random.Generator,
) -> tuple[str, str]:
    """Returns (winner_code, loser_code)."""
    lam_a, lam_b = compute_lambdas(team_a, team_b, host_nations, neutral_venue, h2h_data, config)
    hg = int(rng.poisson(lam_a))
    ag = int(rng.poisson(lam_b))

    if not is_knockout:
        return team_a.code, team_b.code  # draw is valid; return both for group tracking

    # Knockout: resolve draws
    if hg != ag:
        return (team_a.code, team_b.code) if hg > ag else (team_b.code, team_a.code)

    # Extra time
    et_frac = config["extra_time_minutes_fraction"]
    et_h = int(rng.poisson(lam_a * et_frac))
    et_a = int(rng.poisson(lam_b * et_frac))
    if et_h != et_a:
        return (team_a.code, team_b.code) if et_h > et_a else (team_b.code, team_a.code)

    # Penalties
    from src.engine.knockout_resolver import _clamp
    e_a = 1.0 / (1.0 + 10.0 ** (-(team_a.elo_rating - team_b.elo_rating) / 400.0))
    p_a = _clamp(0.5 + config["penalty_skill_factor"] * (e_a - 0.5), 0.35, 0.65)
    return (team_a.code, team_b.code) if rng.random() < p_a else (team_b.code, team_a.code)


def _simulate_group_match(
    team_a: Team,
    team_b: Team,
    host_nations: list[str],
    neutral_venue: bool,
    h2h_data: Optional[dict],
    config: dict,
    rng: np.random.Generator,
) -> dict:
    lam_a, lam_b = compute_lambdas(team_a, team_b, host_nations, neutral_venue, h2h_data, config)
    hg = int(rng.poisson(lam_a))
    ag = int(rng.poisson(lam_b))
    return {"home": team_a.code, "away": team_b.code, "home_goals": hg, "away_goals": ag}


def simulate_tournament(
    teams: dict[str, Team],
    h2h: dict[str, dict],
    group_stages: list[Stage],
    knockout_stages: list[Stage],
    host_nations: list[str],
    config: dict,
    n_trials: int = 100_000,
    seed: Optional[int] = None,
) -> dict:
    """
    Returns advancement probabilities:
    {"team_code": {"group_advance": p, "r32": p, "r16": p, "qf": p, "sf": p, "final": p, "winner": p}}
    """
    from src.io.loader import get_h2h_data

    rng = np.random.default_rng(seed)
    n_stages = 1 + len(knockout_stages)
    stage_names = ["group_advance"] + [s.stage_name.lower().replace(" ", "_").replace("-", "_") for s in knockout_stages]

    counts: dict[str, dict[str, int]] = {code: defaultdict(int) for code in teams}

    for _ in range(n_trials):
        alive: dict[str, Team] = {}  # teams still in tournament

        # group stage
        group_winners: list[str] = []
        group_runners: list[str] = []
        all_third: list[tuple[int, str]] = []  # (points, code) for 3rd-place teams

        for stage in group_stages:
            team_codes = list({m.home for m in stage.matches} | {m.away for m in stage.matches})
            results = []
            for m in stage.matches:
                if m.status == "walkover":
                    continue
                ta = teams[m.home]
                tb = teams[m.away]
                h2h_d = get_h2h_data(m.home, m.away, h2h)
                res = _simulate_group_match(ta, tb, host_nations, m.neutral_venue, h2h_d, config, rng)
                results.append(res)

            standings = compute_group_standings(team_codes, results)
            if len(standings) >= 1:
                group_winners.append(standings[0].code)
            if len(standings) >= 2:
                group_runners.append(standings[1].code)
            if len(standings) >= 3:
                third = standings[2]
                all_third.append((third.points, third.goal_difference, third.goals_for, third.code))

        # Best 8 third-place teams advance
        all_third.sort(reverse=True)
        best_thirds = [t[-1] for t in all_third[:8]]

        advancing = set(group_winners + group_runners + best_thirds)
        for code in advancing:
            counts[code]["group_advance"] += 1
        alive = {code: teams[code] for code in advancing if code in teams}

        # knockout stages
        for stage in knockout_stages:
            next_alive: set[str] = set()
            for m in stage.matches:
                home_code = m.home
                away_code = m.away
                # Skip TBD matches without resolved teams
                if home_code.startswith("TBD") or away_code.startswith("TBD"):
                    continue
                if home_code not in alive or away_code not in alive:
                    continue
                ta = alive[home_code]
                tb = alive[away_code]
                h2h_d = get_h2h_data(home_code, away_code, h2h)
                winner, _ = _simulate_one_match(
                    ta, tb, host_nations, m.neutral_venue, h2h_d, config, True, rng
                )
                next_alive.add(winner)
                stage_key = stage.stage_name.lower().replace(" ", "_").replace("-", "_")
                counts[winner][stage_key] += 1

            alive = {code: teams[code] for code in next_alive if code in teams}

    # Normalise to probabilities
    result: dict[str, dict[str, float]] = {}
    for code in teams:
        result[code] = {k: round(v / n_trials, 5) for k, v in counts[code].items()}

    return result
