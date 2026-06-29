from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TeamRecord:
    code: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0

    @property
    def points(self) -> int:
        return self.wins * 3 + self.draws

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against


def _update_records(
    records: dict[str, TeamRecord],
    home: str,
    away: str,
    hg: int,
    ag: int,
) -> None:
    rh = records[home]
    ra = records[away]
    rh.played += 1
    ra.played += 1
    rh.goals_for += hg
    rh.goals_against += ag
    ra.goals_for += ag
    ra.goals_against += hg
    if hg > ag:
        rh.wins += 1
        ra.losses += 1
    elif hg < ag:
        ra.wins += 1
        rh.losses += 1
    else:
        rh.draws += 1
        ra.draws += 1


def _h2h_points(code_a: str, code_b: str, results: list[dict]) -> tuple[int, int]:
    pts_a = pts_b = 0
    for r in results:
        if r["home"] == code_a and r["away"] == code_b:
            if r["home_goals"] > r["away_goals"]:
                pts_a += 3
            elif r["home_goals"] < r["away_goals"]:
                pts_b += 3
            else:
                pts_a += 1
                pts_b += 1
        elif r["home"] == code_b and r["away"] == code_a:
            if r["home_goals"] > r["away_goals"]:
                pts_b += 3
            elif r["home_goals"] < r["away_goals"]:
                pts_a += 3
            else:
                pts_a += 1
                pts_b += 1
    return pts_a, pts_b


def rank_group(
    team_codes: list[str],
    match_results: list[dict],
    rng=None,
) -> list[TeamRecord]:
    """
    Rank teams in a group.
    match_results: list of {"home": str, "away": str, "home_goals": int, "away_goals": int}
    Tiebreakers: (1) points (2) GD (3) GF (4) H2H points (5) random draw
    """
    records = {code: TeamRecord(code=code) for code in team_codes}
    for r in match_results:
        _update_records(records, r["home"], r["away"], r["home_goals"], r["away_goals"])

    def sort_key(rec: TeamRecord):
        return (rec.points, rec.goal_difference, rec.goals_for)

    sorted_teams = sorted(records.values(), key=sort_key, reverse=True)

    # Resolve ties using H2H then random
    i = 0
    while i < len(sorted_teams):
        j = i + 1
        while j < len(sorted_teams) and sort_key(sorted_teams[j]) == sort_key(sorted_teams[i]):
            j += 1
        if j - i > 1:
            tied = sorted_teams[i:j]
            tied_codes = [t.code for t in tied]
            h2h_pts = {code: 0 for code in tied_codes}
            for r in match_results:
                if r["home"] in tied_codes and r["away"] in tied_codes:
                    if r["home_goals"] > r["away_goals"]:
                        h2h_pts[r["home"]] += 3
                    elif r["home_goals"] < r["away_goals"]:
                        h2h_pts[r["away"]] += 3
                    else:
                        h2h_pts[r["home"]] += 1
                        h2h_pts[r["away"]] += 1
            if len(set(h2h_pts.values())) > 1:
                tied.sort(key=lambda t: h2h_pts[t.code], reverse=True)
                sorted_teams[i:j] = tied
            else:
                import random
                _rng = rng or random
                _rng.shuffle(tied)
                sorted_teams[i:j] = tied
        i = j

    return sorted_teams


def compute_group_standings(
    team_codes: list[str],
    match_results: list[dict],
) -> list[TeamRecord]:
    return rank_group(team_codes, match_results)
