# fotmob-predictor

A Monte Carlo simulation engine for World Cup match outcomes. Give it Elo ratings, attack/defense
strength, and recent form for two teams, and it runs thousands of Poisson-sampled matches to
produce win/draw/loss odds, a score distribution, and (for knockout games) extra time and penalty
resolution. It can also simulate an entire tournament bracket end to end and spit out each team's
odds of winning it all.

Built for the 2026 World Cup, but the engine itself doesn't care which tournament it's pointed at.

## What it does

1. Computes each team's expected goals (λ) from attack/defense coefficients, Elo, recent form, and home advantage
2. Samples thousands of Poisson-distributed matches from those two lambdas
3. Turns the samples into outcome probabilities and a predicted scoreline
4. For knockout matches, resolves draws through extra time and then penalties
5. For a full tournament, runs the group stage and bracket together across 100,000 trials to get each team's odds of reaching every round

## Does it actually work?

I hand-picked the parameters below with no historical check, which is a bad habit for anything
that outputs a probability. So I ran the engine against every one of the 64 real matches from the
2022 World Cup and scored it properly: Brier score, log loss, and plain accuracy, against two dumb
baselines.

**It beats guessing.** 57.8% accuracy against a coin-flip baseline's 42.2%, and a clearly better
Brier score than picking outcomes uniformly at random.

**It doesn't beat "the better team probably wins."** Against a baseline that only knows which team
is rated higher, not by how much, and gives it a flat 50/25/25 split regardless of the gap size,
the engine ties on accuracy and loses on log loss. In other words, the specific way
`rating_sensitivity_gamma` scales a rating gap into a goal-rate boost isn't currently adding much
over just knowing who's favored.

The most confidently wrong calls were all draws the model underrated (Mexico 0-0 Poland, Cameroon
3-3 Serbia, Croatia 0-0 Belgium, and so on). A plain Poisson model with no draw-specific term seems
to systematically underrate cagey, low-scoring matchups.

Full writeup, methodology, and the by-stage breakdown: [BACKTEST.md](BACKTEST.md). Run it yourself
with `python main.py backtest`.

## What's next

- Re-source real Elo history instead of the FIFA-ranking-points stand-in used in the backtest (eloratings.net renders its table client-side, so a bulk export wasn't available)
- Reconstruct real attack/defense numbers for the 2022 teams so the backtest checks the whole pipeline, not just the rating half
- Grid-search `rating_sensitivity_gamma` and `league_avg_goals` against the backtest data instead of assuming the hand-picked values are close to right
- Add a second tournament (2018) to the backtest so the calibration isn't judged on one 64-match sample
- Look at adding an explicit draw-probability adjustment, given how consistently the model underrates draws

## Project layout

```
fotmob-predictor/
├── main.py                        entry point (Typer CLI)
├── data/
│   ├── team_profiles.json         48-team profiles: Elo, attack/defense, form
│   ├── tournament_schedule.json   match schedule, group + knockout stages
│   ├── h2h_data.json              head-to-head history
│   ├── scoring_rules.json         points system for the optimal-pick calculator
│   └── historical/                real match results + ratings used for backtesting
├── src/
│   ├── config.py                  global defaults (lambda bounds, simulation counts, etc.)
│   ├── cli.py                     CLI commands (Typer + Rich output)
│   ├── backtest/
│   │   └── runner.py              scores the engine against real historical tournaments
│   ├── engine/
│   │   ├── lambda_calculator.py   expected goals from team profiles
│   │   ├── monte_carlo.py         Poisson simulation, score matrix, outcome probabilities
│   │   ├── knockout_resolver.py   extra time + penalty shootout resolver
│   │   └── score_optimizer.py     rounded-scoreline pick + EV-optimal calculator
│   ├── aggregation/
│   │   ├── group_standings.py     group ranking with tiebreakers
│   │   └── bracket_simulator.py   full tournament bracket simulation
│   ├── data_ingestion/
│   │   ├── api_football_client.py live fixtures + stats via API-Football
│   │   ├── elo_source.py          live Elo fetch (eloratings.net) + static fallback
│   │   ├── profile_builder.py     builds team_profiles.json from API data
│   │   └── cache.py               disk-based request cache
│   ├── models/
│   │   ├── team.py                Team dataclass
│   │   └── result.py              SimulationResult dataclass
│   └── io/
│       ├── loader.py              loads JSON data files
│       └── exporter.py            exports JSON, CSV, and heatmap PNGs
└── outputs/                       generated predictions and charts (gitignored)
```

## How the engine works

### Expected goals

```
lambda_home = mu * attack_home * defense_away * elo_modifier_home * h2h_modifier_home * home_advantage
lambda_away = mu * attack_away * defense_home * elo_modifier_away * h2h_modifier_away
```

`mu = 1.50` is the tournament's baseline goals per team per match. The Elo modifier scales each
side by `± (rating_sensitivity_gamma * 0.5)` based on that team's Elo win probability, home
advantage is a flat `1.08x` for non-neutral venues, and head-to-head history adjusts by up to `±8%`.

### Match simulation

Each match runs 10,000 Poisson samples by default: goals drawn from `Poisson(lambda_home)` and
`Poisson(lambda_away)`, giving a full score probability matrix plus win/draw/loss percentages. The
predicted scoreline is `round(lambda_home), round(lambda_away)` rather than the single most likely
score cell, since the mode tends to undershoot real goal totals on skewed distributions.

### Knockout resolution

If a knockout match is level after 90 minutes: extra time is simulated as a third of a normal
match, and if it's still level, penalties are decided by an Elo-weighted coin flip clamped to
`[35%, 65%]`.

### Tournament bracket

Runs the group stage and knockout rounds together across 100,000 trials, seeding completed matches
with their known result and simulating the rest, to get each team's odds of reaching every stage.

## CLI commands

```bash
python main.py --help
```

| Command | Description |
|---|---|
| `predict-match` | Simulate a single match |
| `predict-group` | Simulate all matches in a group stage |
| `predict-knockout` | Simulate all matches in a knockout stage |
| `predict-tournament` | Full tournament bracket simulation |
| `simulate-bracket` | Simulate bracket from any stage onward |
| `backtest` | Score the engine against real 2022 World Cup results |
| `fetch-data` | Refresh team data from API-Football |

```bash
# single match, knockout stage
python main.py predict-match ARG FRA --stage knockout --heatmap

# every match in a group
python main.py predict-group "Group A" --export

# full tournament, 100k trials
python main.py predict-tournament --n-trials 100000 --top 16

# bracket from Round of 16 onward
python main.py simulate-bracket --start-stage "Round of 16" --export

# refresh live data
python main.py fetch-data

# check the engine against real history
python main.py backtest
```

Sample output from `predict-match`:

```
Argentina vs France  (lam_home=1.52, lam_away=1.38, N=10,000)
* Predicted Score: 2-1
Outcome:  Home 44% | Draw 26% | Away 30%

Knockout: drawn after 90' 26.2% | drawn after 120' 8.1%
Advances: Argentina 51% | France 49%  (score ref: 90min)
```

## Configuration

Parameters live in [src/config.py](src/config.py):

| Parameter | Default | Effect |
|---|---|---|
| `league_avg_goals` | `1.50` | baseline goals per team per match |
| `rating_sensitivity_gamma` | `0.45` | how much Elo moves lambda |
| `h2h_weight` | `0.08` | head-to-head adjustment strength |
| `home_advantage_factor` | `1.08` | multiplier for the home team at non-neutral venues |
| `penalty_skill_factor` | `0.10` | Elo tilt in a penalty shootout |
| `n_simulations` | `10,000` | samples per match |
| `n_tournament_trials` | `100,000` | trials for a full bracket run |

`team_profiles.json` carries its own `config` block, which gets merged on top of `DEFAULT_CONFIG`
at load time. If you change a value in `src/config.py`, update the matching value in
`data/team_profiles.json` too, or the profile's copy silently wins.

## Data sources

| Source | Data | Update method |
|---|---|---|
| API-Football (`v3.football.api-sports.io`) | fixtures, team stats, head-to-head | `python main.py fetch-data` |
| eloratings.net | live Elo ratings for the 48 WC teams | fetched automatically, falls back to a static snapshot |
| `team_profiles.json` | attack/defense, confederation, FIFA ranking | built by `fetch-data`, editable by hand |
| `tournament_schedule.json` | full match schedule | maintained by hand |

A free API-Football plan doesn't include the 2026 season's stats endpoint, so `fetch-data` runs
without error but leaves team stats untouched. Completed-match results in
`tournament_schedule.json` have to be backfilled by hand as rounds finish.

## Setup

```bash
pip install -r requirements.txt

# API key is only needed for fetch-data
cp .env.example .env
# edit .env: API_FOOTBALL_KEY=your_key_here

python main.py predict-match ARG FRA
```

Requires Python 3.11+, `numpy`, `scipy`, `pandas`, `typer`, `rich`, `requests`, `python-dotenv`,
and `matplotlib` for heatmaps.

## Outputs

Exports land in `outputs/` (gitignored):

| File | Contents |
|---|---|
| `predictions.json` | full simulation results per match |
| `tournament_summary.csv` | flat table of scores, probabilities, optimal pick |
| `advancement_probabilities.json` | per-team stage advancement rates |
| `heatmap_<match_id>.png` | score probability matrix as a heatmap |
| `backtest_wc2022_report.json` | full per-match backtest output |

## Teams

48 teams across 6 confederations, all 2026 World Cup participants. Elo ratings from eloratings.net
as of 2026-06-28. Host nations: USA, Mexico, Canada.

## License

MIT, see [LICENSE](LICENSE).
