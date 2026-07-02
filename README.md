# ⚽ fotmob-predictor

**World Cup 2026 Monte Carlo simulation engine.**  
Predicts match outcomes, group standings, and full bracket advancement probabilities using Poisson-based statistical modelling and Elo ratings.

---

## What It Does

Given team profiles (attack/defense coefficients, Elo ratings, recent form), the engine:

1. Computes expected goals (λ) for each team in a matchup
2. Runs thousands of Poisson-sampled match simulations
3. Aggregates outcome probabilities and a predicted scoreline
4. For knockout matches — resolves extra time and penalties
5. For full tournaments — simulates the entire bracket across 100,000 trials

---

## Architecture

```
fotmob-predictor/
├── main.py                        Entry point (Typer CLI)
├── data/
│   ├── team_profiles.json         48-team profiles (Elo, attack/defense, form)
│   ├── tournament_schedule.json   Match schedule with group & knockout stages
│   ├── h2h_data.json              Head-to-head historical records
│   └── scoring_rules.json         Points system for optimal pick scoring
├── src/
│   ├── config.py                  Global defaults (λ bounds, simulation counts, etc.)
│   ├── cli.py                     All CLI commands (Typer + Rich output)
│   ├── engine/
│   │   ├── lambda_calculator.py   Computes expected goals from team profiles
│   │   ├── monte_carlo.py         Poisson simulation, score matrix, outcome probs
│   │   ├── knockout_resolver.py   Extra time + penalty shootout resolver
│   │   └── score_optimizer.py     Rounded-scoreline pick + EV-optimal calculator
│   ├── aggregation/
│   │   ├── group_standings.py     Group ranking with tiebreakers
│   │   └── bracket_simulator.py   Full tournament bracket simulation
│   ├── data_ingestion/
│   │   ├── api_football_client.py Live fixtures & stats via API-Football
│   │   ├── elo_source.py          Live ELO fetch (eloratings.net) + static fallback
│   │   ├── profile_builder.py     Builds team_profiles.json from API data
│   │   └── cache.py               Disk-based request cache
│   ├── models/
│   │   ├── team.py                Team dataclass
│   │   └── result.py              SimulationResult dataclass
│   └── io/
│       ├── loader.py              Loads JSON data files
│       └── exporter.py            Exports JSON, CSV, and heatmap PNGs
└── outputs/                       Generated predictions and charts
```

---

## The Engine

### Expected Goals (λ)

For each match, the engine computes attack/defense-adjusted expected goals per team:

```
λ_home = μ × attack_home × defense_away × elo_modifier_home × h2h_modifier_home × home_advantage
λ_away = μ × attack_away × defense_home × elo_modifier_away × h2h_modifier_away
```

Where `μ = 1.50` (tournament league average — calibrated to the 2026 group stage's observed
2.99 goals/game), the Elo modifier scales by `±(rating_sensitivity_gamma × 0.5)` based on each
team's Elo win probability, home advantage is `1.08×` for non-neutral venues, and H2H adjusts
by up to `±8%`.

### Match Simulation

Each match runs **10,000 Poisson samples** by default:

- Goals drawn from `Poisson(λ_home)` and `Poisson(λ_away)`
- Produces a full score probability matrix (e.g. P(2-1), P(1-0), …)
- Outputs: win/draw/loss %, and a predicted scoreline (`round(λ_home), round(λ_away)` —
  tracks the expected-goals mean rather than the single most-probable cell, which floors
  away both lambdas' fractional parts and undershoots real goal totals)

### Knockout Resolution

When a knockout match ends level after 90 minutes:

1. **Extra time** — simulated as `1/3` of normal match duration
2. **Penalties** — Elo-weighted probability clamped to `[35%, 65%]`

### Tournament Bracket

Runs **100,000 full tournament simulations** end-to-end:

- Groups are played out → top teams advance
- Bracket seeding resolves to produce R32, R16, QF, SF, Final matchups
- Outputs each team's advancement probability at every stage

---

## CLI Commands

```bash
python main.py --help
```

| Command | Description |
|---|---|
| `predict-match` | Simulate a single match |
| `predict-group` | Simulate all matches in a group stage |
| `predict-knockout` | Simulate all matches in a knockout stage |
| `predict-tournament` | Full tournament bracket simulation |
| `simulate-bracket` | Simulate bracket from any stage onwards |
| `fetch-data` | Refresh team data from API-Football |

### Examples

```bash
# Single match — Argentina vs France, knockout stage
python main.py predict-match ARG FRA --stage knockout --heatmap

# All Group A matches
python main.py predict-group "Group A" --export

# Full tournament (100k trials)
python main.py predict-tournament --n-trials 100000 --top 16

# Bracket from Round of 16 onward
python main.py simulate-bracket --start-stage "Round of 16" --export

# Refresh live data from API-Football
python main.py fetch-data
```

### Sample Output — predict-match

```
Argentina vs France  (lam_home=1.52, lam_away=1.38, N=10,000)
* Predicted Score: 2-1
Outcome:  Home 44% | Draw 26% | Away 30%

Knockout: drawn after 90' 26.2% | drawn after 120' 8.1%
Advances: Argentina 51% | France 49%  (score ref: 90min)
```

---

## Configuration

Key parameters live in [src/config.py](src/config.py):

| Parameter | Default | Effect |
|---|---|---|
| `league_avg_goals` | `1.50` | Baseline goals per team per match |
| `rating_sensitivity_gamma` | `0.45` | Elo influence on λ |
| `h2h_weight` | `0.08` | Head-to-head adjustment strength |
| `home_advantage_factor` | `1.08` | Multiplier for home team at non-neutral venues |
| `penalty_skill_factor` | `0.10` | Elo tilt in penalty shootout |
| `n_simulations` | `10,000` | Samples per match simulation |
| `n_tournament_trials` | `100,000` | Trials for full bracket simulation |

> **Note:** `team_profiles.json` embeds its own `config` block, which is merged over
> `DEFAULT_CONFIG` at load time (`{**DEFAULT_CONFIG, **profile_config}` in `cli.py`). If you
> change a parameter in `src/config.py`, update the matching value in `data/team_profiles.json`
> too, or it'll be silently overridden.

---

## Data Sources

| Source | Data | Update method |
|---|---|---|
| **API-Football** (`v3.football.api-sports.io`) | Fixtures, team stats, H2H results | `python main.py fetch-data` |
| **eloratings.net** | Live Elo ratings (48 WC teams) | Auto-fetched on each run, falls back to static snapshot |
| **`team_profiles.json`** | Attack/defense coefficients, confederation, FIFA ranking | Built by `fetch-data`, manually editable |
| **`tournament_schedule.json`** | Full match schedule (group + knockout) | Manually maintained |

> **Note:** a free API-Football plan does not have access to the 2026 season's stats endpoint
> (`teams/statistics`) — `fetch-data` will run without error but silently leave team stats
> unchanged. Completed-match results in `tournament_schedule.json` currently have to be
> backfilled by hand (`status: "completed"` + `final_score`) as rounds finish.

---

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set API key (only needed for fetch-data)
cp .env.example .env
# Edit .env: API_FOOTBALL_KEY=your_key_here

# 3. Run
python main.py predict-match ARG FRA
```

### Requirements

- Python 3.11+
- `numpy`, `scipy`, `pandas`
- `typer`, `rich`
- `matplotlib` (heatmaps only)
- `requests`, `python-dotenv`

---

## Outputs

All exports land in `outputs/`:

| File | Contents |
|---|---|
| `predictions.json` | Full SimulationResult objects per match |
| `tournament_summary.csv` | Flat table: scores, probabilities, optimal pick |
| `advancement_probabilities.json` | Per-team stage advancement rates |
| `heatmap_<match_id>.png` | Score probability matrix visualised as a heat map |

---

## Teams

48 teams across 6 confederations — all 2026 World Cup participants.  
Elo ratings sourced from eloratings.net as of **2026-06-28**.  
Host nations: **USA**, **Mexico**, **Canada**.
