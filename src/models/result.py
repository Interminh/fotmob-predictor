from dataclasses import dataclass, field
from typing import Optional, Dict, List


@dataclass
class ScoreEntry:
    score: str
    probability: float


@dataclass
class OutcomeProbabilities:
    home_win: float
    draw: float
    away_win: float


@dataclass
class KnockoutResolution:
    drawn_after_90min_probability: float
    drawn_after_120min_probability: float
    home_advances_probability: float
    away_advances_probability: float
    score_reference_used: str


@dataclass
class OptimalPrediction:
    score: str
    expected_points: float
    note: str = "EV-optimized for configured scoring rules"


@dataclass
class SimulationResult:
    match_id: str
    home_team: str
    away_team: str
    lambda_home: float
    lambda_away: float
    simulations_run: int
    top_3_scores: List[ScoreEntry]
    outcome_probabilities: OutcomeProbabilities
    optimal_prediction: OptimalPrediction
    score_matrix: Dict[str, float] = field(default_factory=dict)
    knockout_resolution: Optional[KnockoutResolution] = None
