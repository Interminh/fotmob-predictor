import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# Static ELO snapshot (pre-tournament best estimates — update via fetch-data)
STATIC_ELO_SNAPSHOT: dict[str, float] = {
    "ARG": 2090, "FRA": 2050, "BRA": 2010, "ENG": 2000, "ESP": 1990,
    "POR": 1960, "GER": 1960, "NED": 1940, "BEL": 1900, "URU": 1840,
    "DEN": 1840, "CRO": 1880, "MAR": 1840, "COL": 1830, "JPN": 1830,
    "USA": 1830, "SUI": 1860, "SRB": 1840, "MEX": 1800, "POL": 1800,
    "TUR": 1820, "AUT": 1820, "CAN": 1780, "SCO": 1780, "HUN": 1780,
    "KOR": 1790, "ECU": 1790, "SEN": 1800, "IRN": 1740, "AUS": 1760,
    "CHI": 1740, "VEN": 1720, "CIV": 1720, "NGA": 1710, "UZB": 1700,
    "PAN": 1700, "ALG": 1700, "CMR": 1700, "QAT": 1690, "CRC": 1690,
    "KSA": 1680, "EGY": 1680, "RSA": 1680, "MLI": 1680, "HON": 1660,
    "JOR": 1660, "GHA": 1660, "NZL": 1610,
}


def fetch_elo_ratings() -> dict[str, float]:
    """Best-effort live fetch from eloratings.net. Falls back to static snapshot."""
    try:
        resp = requests.get("https://eloratings.net/World.tsv", timeout=10)
        resp.raise_for_status()
        ratings: dict[str, float] = {}
        for line in resp.text.splitlines():
            parts = line.strip().split("\t")
            if len(parts) >= 3:
                try:
                    ratings[parts[0].upper()] = float(parts[2])
                except ValueError:
                    pass
        if ratings:
            return ratings
        logger.warning("ELO fetch returned empty data — using static snapshot")
    except Exception as exc:
        logger.warning("ELO fetch failed (%s) — using static snapshot", exc)
    return dict(STATIC_ELO_SNAPSHOT)


def get_elo_for_team(team_code: str, live_ratings: Optional[dict[str, float]] = None) -> float:
    if live_ratings and team_code in live_ratings:
        return live_ratings[team_code]
    return STATIC_ELO_SNAPSHOT.get(team_code, 1500.0)
