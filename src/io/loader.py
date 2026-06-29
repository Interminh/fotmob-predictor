import json
from pathlib import Path
from typing import Optional

from src.models.team import Team, RecentForm
from src.models.match import Match, Stage, Tournament
from src.config import DATA_DIR


def _require(obj: dict, key: str, context: str) -> object:
    if key not in obj:
        raise ValueError(f"Missing required field '{key}' in {context}")
    return obj[key]


def load_team_profiles(path: Optional[Path] = None) -> tuple[dict[str, Team], dict[str, dict], dict]:
    path = path or DATA_DIR / "team_profiles.json"
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    config = raw.get("config", {})
    teams: dict[str, Team] = {}

    for code, t in raw.get("teams", {}).items():
        rf = t.get("recent_form", {})
        recent_form = RecentForm(
            goals_scored_last_10=rf.get("goals_scored_last_10", 13.5),
            goals_conceded_last_10=rf.get("goals_conceded_last_10", 13.5),
            matches_played=rf.get("matches_played", 10),
        )
        atk = t.get("attack_strength")
        def_ = t.get("defense_strength")
        data_quality = "normal"
        if atk is None or def_ is None:
            atk = atk or 1.0
            def_ = def_ or 1.0
            data_quality = "low"

        teams[code] = Team(
            code=code,
            name=_require(t, "name", f"team {code}"),
            confederation=t.get("confederation", "Unknown"),
            fifa_ranking=t.get("fifa_ranking", 100),
            elo_rating=t.get("elo_rating", 1500.0),
            recent_form=recent_form,
            attack_strength=float(atk),
            defense_strength=float(def_),
            is_host_nation=t.get("is_host_nation", False),
            data_quality=data_quality,
        )

    h2h: dict[str, dict] = raw.get("head_to_head", {})
    return teams, h2h, config


def load_tournament_schedule(path: Optional[Path] = None) -> Tournament:
    path = path or DATA_DIR / "tournament_schedule.json"
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    stages = []
    for s in raw.get("stages", []):
        matches = [
            Match(
                match_id=_require(m, "match_id", f"match in {s['stage_name']}"),
                home=_require(m, "home", f"match {m.get('match_id', '?')}"),
                away=_require(m, "away", f"match {m.get('match_id', '?')}"),
                date=m.get("date", "TBD"),
                neutral_venue=m.get("neutral_venue", True),
                depends_on=m.get("depends_on", []),
                status=m.get("status", "scheduled"),
                final_score=m.get("final_score"),
            )
            for m in s.get("matches", [])
        ]
        stages.append(Stage(
            stage_name=s["stage_name"],
            type=s["type"],
            matches=matches,
            advance_count=s.get("advance_count"),
        ))

    return Tournament(
        name=raw.get("tournament", "World Cup"),
        host_nations=raw.get("host_nations", []),
        stages=stages,
    )


def load_scoring_rules(path: Optional[Path] = None) -> dict:
    path = path or DATA_DIR / "scoring_rules.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_h2h_data(
    code_a: str,
    code_b: str,
    h2h: dict[str, dict],
) -> Optional[dict]:
    key1 = f"{code_a}_{code_b}"
    key2 = f"{code_b}_{code_a}"
    if key1 in h2h:
        entry = h2h[key1]
        if entry.get("team1") == code_a:
            return entry
        inverted = dict(entry)
        inverted["avg_goal_diff_team1_minus_team2"] = -entry["avg_goal_diff_team1_minus_team2"]
        inverted["team1"], inverted["team2"] = code_a, code_b
        return inverted
    if key2 in h2h:
        entry = h2h[key2]
        inverted = dict(entry)
        inverted["avg_goal_diff_team1_minus_team2"] = -entry["avg_goal_diff_team1_minus_team2"]
        inverted["team1"], inverted["team2"] = code_a, code_b
        return inverted
    return None
