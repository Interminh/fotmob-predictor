import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional

_CACHE_DIR = Path(__file__).parent.parent.parent / ".cache" / "api"
_TTL_SECONDS = 86_400  # 24 hours


def _cache_path(endpoint: str, params: dict) -> Path:
    key = endpoint + json.dumps(params, sort_keys=True)
    digest = hashlib.sha256(key.encode()).hexdigest()[:16]
    return _CACHE_DIR / f"{digest}.json"


def get(endpoint: str, params: dict) -> Optional[Any]:
    path = _cache_path(endpoint, params)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        entry = json.load(f)
    if time.time() - entry["ts"] > _TTL_SECONDS:
        return None
    return entry["data"]


def set(endpoint: str, params: dict, data: Any) -> None:
    path = _cache_path(endpoint, params)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"ts": time.time(), "data": data}, f)


def clear_expired() -> int:
    removed = 0
    if not _CACHE_DIR.exists():
        return 0
    for p in _CACHE_DIR.glob("*.json"):
        try:
            with open(p) as f:
                entry = json.load(f)
            if time.time() - entry["ts"] > _TTL_SECONDS:
                p.unlink()
                removed += 1
        except Exception:
            p.unlink()
            removed += 1
    return removed
