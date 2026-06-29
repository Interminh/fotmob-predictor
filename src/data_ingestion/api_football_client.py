import os
from typing import Any, Optional

import requests

from src.data_ingestion import cache as _cache

_BASE_URL = "https://v3.football.api-sports.io"
_WC_LEAGUE_ID = 1
_WC_SEASON = 2026


def _get_key() -> str:
    key = os.environ.get("API_FOOTBALL_KEY", "")
    if not key:
        raise EnvironmentError(
            "API_FOOTBALL_KEY not set. "
            "Export it or add it to a .env file. "
            "Get a free key at https://www.api-football.com/"
        )
    return key


def _request(endpoint: str, params: dict, force_refresh: bool = False) -> Any:
    cached = None if force_refresh else _cache.get(endpoint, params)
    if cached is not None:
        return cached

    headers = {"x-apisports-key": _get_key()}
    url = f"{_BASE_URL}/{endpoint}"
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    _cache.set(endpoint, params, data)
    return data


def fetch_fixtures(force_refresh: bool = False) -> list[dict]:
    data = _request("fixtures", {"league": _WC_LEAGUE_ID, "season": _WC_SEASON}, force_refresh)
    return data.get("response", [])


def fetch_team_statistics(team_id: int, force_refresh: bool = False) -> Optional[dict]:
    data = _request(
        "teams/statistics",
        {"team": team_id, "league": _WC_LEAGUE_ID, "season": _WC_SEASON},
        force_refresh,
    )
    response = data.get("response")
    if not response:
        return None
    return response if isinstance(response, dict) else response[0] if response else None


def fetch_head_to_head(team_id_1: int, team_id_2: int, last: int = 5, force_refresh: bool = False) -> list[dict]:
    data = _request(
        "fixtures/headtohead",
        {"h2h": f"{team_id_1}-{team_id_2}", "last": last},
        force_refresh,
    )
    return data.get("response", [])


def fetch_predictions(fixture_id: int, force_refresh: bool = False) -> Optional[dict]:
    data = _request("predictions", {"fixture": fixture_id}, force_refresh)
    response = data.get("response", [])
    return response[0] if response else None
