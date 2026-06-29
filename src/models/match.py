from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class Match:
    match_id: str
    home: str
    away: str
    date: str
    neutral_venue: bool = True
    depends_on: List[str] = field(default_factory=list)
    status: str = "scheduled"
    final_score: Optional[dict] = None


@dataclass
class Stage:
    stage_name: str
    type: str
    matches: List[Match]
    advance_count: Optional[int] = None


@dataclass
class Tournament:
    name: str
    host_nations: List[str]
    stages: List[Stage]
