from dataclasses import dataclass, field


@dataclass
class RecentForm:
    goals_scored_last_10: float
    goals_conceded_last_10: float
    matches_played: int


@dataclass
class Team:
    code: str
    name: str
    confederation: str
    fifa_ranking: int
    elo_rating: float
    recent_form: RecentForm
    attack_strength: float
    defense_strength: float
    is_host_nation: bool = False
    data_quality: str = "normal"
