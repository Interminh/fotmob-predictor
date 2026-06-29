"""
Converts raw API-Football responses into the team_profiles.json schema.
Uses the same attack/defense coefficient formula as the engine.
"""
import json
import logging
import shutil
from datetime import date
from pathlib import Path
from typing import Optional

from src.config import DATA_DIR, DEFAULT_CONFIG
from src.data_ingestion import api_football_client as api
from src.data_ingestion.elo_source import fetch_elo_ratings, get_elo_for_team

logger = logging.getLogger(__name__)

_MU = DEFAULT_CONFIG["league_avg_goals"]

# Mapping from API-Football team IDs to 3-letter codes used in this project
# Extend as needed; fetch-data will warn about unmapped teams.
TEAM_ID_TO_CODE: dict[int, str] = {
    1: "ARG", 2: "BRA", 3: "FRA", 4: "ENG", 5: "ESP", 6: "GER", 7: "NED",
    8: "POR", 9: "BEL", 10: "SUI", 11: "CRO", 12: "AUT", 13: "SRB",
    14: "DEN", 15: "SCO", 16: "POL", 17: "TUR", 18: "HUN", 19: "URU",
    20: "COL", 21: "ECU", 22: "CHI", 23: "VEN", 24: "USA", 25: "MEX",
    26: "CAN", 27: "CRC", 28: "HON", 29: "PAN", 30: "JPN", 31: "KOR",
    32: "AUS", 33: "KSA", 34: "IRN", 35: "UZB", 36: "JOR", 37: "QAT",
    38: "MAR", 39: "SEN", 40: "NGA", 41: "EGY", 42: "CMR", 43: "CIV",
    44: "RSA", 45: "MLI", 46: "ALG", 47: "NZL", 48: "GHA",
}

CODE_TO_TEAM_ID: dict[str, int] = {v: k for k, v in TEAM_ID_TO_CODE.items()}


def compute_attack_defense_coefficients(
    goals_scored: float,
    goals_conceded: float,
    matches: int,
    mu: float = _MU,
) -> tuple[float, float]:
    if matches == 0:
        return 1.0, 1.0
    atk = (goals_scored / matches) / mu
    def_ = (goals_conceded / matches) / mu
    return round(atk, 4), round(def_, 4)


def build_team_entry(team_code: str, stats: dict, elo: float) -> dict:
    goals = stats.get("goals", {})
    gf_avg = goals.get("for", {}).get("average", {}).get("total", None)
    ga_avg = goals.get("against", {}).get("average", {}).get("total", None)

    if gf_avg is not None and ga_avg is not None:
        gf = float(gf_avg) * 10
        ga = float(ga_avg) * 10
        atk, def_ = compute_attack_defense_coefficients(gf, ga, 10)
        data_quality = "normal"
    else:
        atk, def_ = 1.0, 1.0
        gf, ga = 13.5, 13.5
        data_quality = "low"

    fixtures = stats.get("fixtures", {})
    played = fixtures.get("played", {}).get("total", 10) or 10

    team_info = stats.get("team", {})
    return {
        "name": team_info.get("name", team_code),
        "confederation": "Unknown",
        "fifa_ranking": 0,
        "elo_rating": elo,
        "recent_form": {
            "goals_scored_last_10": round(gf, 1),
            "goals_conceded_last_10": round(ga, 1),
            "matches_played": min(played, 10),
        },
        "attack_strength": atk,
        "defense_strength": def_,
        "is_host_nation": team_code in ("USA", "MEX", "CAN"),
        "data_quality": data_quality,
    }


def run_ingestion(force_refresh: bool = False) -> None:
    profiles_path = DATA_DIR / "team_profiles.json"
    backup_path = DATA_DIR / f"team_profiles_backup_{date.today()}.json"

    # Backup existing
    if profiles_path.exists():
        shutil.copy2(profiles_path, backup_path)
        logger.info("Backed up existing profiles to %s", backup_path)

    with open(profiles_path, encoding="utf-8") as f:
        existing = json.load(f)

    logger.info("Fetching live ELO ratings…")
    elo_ratings = fetch_elo_ratings()

    logger.info("Fetching fixtures from API-Football…")
    fixtures = api.fetch_fixtures(force_refresh=force_refresh)
    logger.info("Found %d fixtures", len(fixtures))

    team_ids_seen: set[int] = set()
    for fix in fixtures:
        for side in ("home", "away"):
            tid = fix.get("teams", {}).get(side, {}).get("id")
            if tid:
                team_ids_seen.add(tid)

    updated = 0
    skipped_unmapped = []

    for tid in team_ids_seen:
        code = TEAM_ID_TO_CODE.get(tid)
        if not code:
            skipped_unmapped.append(tid)
            continue

        logger.info("Fetching stats for %s (id=%d)…", code, tid)
        try:
            stats = api.fetch_team_statistics(tid, force_refresh=force_refresh)
        except Exception as exc:
            logger.warning("Stats fetch failed for %s: %s", code, exc)
            continue

        if not stats:
            logger.warning("No stats returned for %s", code)
            continue

        elo = get_elo_for_team(code, elo_ratings)
        entry = build_team_entry(code, stats, elo)

        # Preserve manually set fields if available
        existing_team = existing.get("teams", {}).get(code, {})
        if existing_team.get("confederation"):
            entry["confederation"] = existing_team["confederation"]
        if existing_team.get("fifa_ranking"):
            entry["fifa_ranking"] = existing_team["fifa_ranking"]

        existing.setdefault("teams", {})[code] = entry
        updated += 1

    with open(profiles_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

    logger.info("Updated %d teams. Skipped %d unmapped IDs: %s", updated, len(skipped_unmapped), skipped_unmapped)
    if skipped_unmapped:
        logger.warning("Add these team IDs to TEAM_ID_TO_CODE in profile_builder.py: %s", skipped_unmapped)
