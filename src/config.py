from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUTS_DIR = BASE_DIR / "outputs"

DEFAULT_CONFIG = {
    "league_avg_goals": 1.50,
    "rating_sensitivity_gamma": 1.40,
    "h2h_weight": 0.08,
    "h2h_normalization_cap": 3.0,
    "home_advantage_factor": 1.08,
    "lambda_min": 0.15,
    "lambda_max": 5.0,
    "penalty_skill_factor": 0.10,
    "extra_time_minutes_fraction": 0.3333,
    "n_simulations": 10_000,
    "n_tournament_trials": 100_000,
    "cap_display_goals": 8,
    "cap_ev_goals": 6,
}
