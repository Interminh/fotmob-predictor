# Backtest: 2022 World Cup

The engine's parameters (`league_avg_goals`, `rating_sensitivity_gamma`, `home_advantage_factor`,
and so on) were hand-set for the 2026 tournament with no historical check. That's a bad habit for
anything producing probabilities, so this is a first pass at checking whether the core Elo →
Poisson methodology actually beats simple baselines, using the last completed World Cup as ground
truth.

Run it yourself: `python main.py backtest`

## Data

- **Match results**: all 64 matches of the 2022 FIFA World Cup, scored at the 90-minute mark
  (regulation time), cross-checked against Wikipedia's group-stage and knockout-stage articles.
- **Team ratings**: FIFA World Ranking points from the 6 Oct 2022 release, the last ranking
  published before the tournament kicked off. Source: [balsillieschool.ca World Cup FIFA Rankings
  table](https://balsillieschool.ca/wp-content/uploads/2022/11/12-FIFA-Rankings.pdf).

### Known limitations of this backtest

- The live 2026 engine pulls eloratings.net Elo ratings, which render client-side and couldn't be
  bulk-exported for this pass. FIFA ranking points stand in instead, plugged into the same
  `rating_sensitivity_gamma` formula. Both are logistic international-team ratings on a roughly
  similar scale, but they aren't the same number, so this is a proxy, not the real rating source.
- Attack/defense strength is held neutral (1.0) for every team. The live engine also uses
  team-specific attack/defense coefficients built from recent-form goals scored/conceded, but
  verified last-10-match form data for all 32 teams as of November 2022 wasn't something I could
  source reliably. So this backtest only validates the Elo-rating and home-advantage half of the
  model, not the full pipeline.
- No market-odds baseline (the live 2026 predictions do compare against sportsbook lines). This is
  the model in isolation.

## Results (90-minute outcome: home win / draw / away win)

| | Brier score (lower better) | Log loss (lower better) | Accuracy |
|---|---|---|---|
| Engine (Elo + Poisson) | 0.6152 | 1.0276 | 57.8% |
| Uniform (1/3, 1/3, 1/3) | 0.6667 | 1.0986 | 42.2% |
| Favorite-sign-only (fixed 50/25/25, ignores rating gap size) | 0.5859 | 0.9856 | 57.8% |

Favorite-sign-only is a baseline that only knows which team is rated higher, not by how much, and
always gives it a fixed 50% (draw 25%, underdog 25%).

**Takeaway:** the engine clearly beats guessing blind, but it doesn't beat the naive "better-ranked
team probably wins, regardless of gap size" baseline on Brier score or log loss. It only matches
that baseline on raw accuracy. So the specific way `rating_sensitivity_gamma` scales a win
probability into a goal-rate multiplier isn't adding predictive value over just knowing who's
favored. That's a real, useful negative result: it points at the gamma/lambda-shaping step as the
part of the pipeline most worth re-tuning, not the rating source.

### By stage

| Stage | Matches | Model accuracy | Model Brier |
|---|---|---|---|
| Group A | 6 | 66.7% | 0.571 |
| Group B | 6 | 66.7% | 0.632 |
| Group C | 6 | 66.7% | 0.597 |
| Group D | 6 | 33.3% | 0.653 |
| Group E | 6 | 33.3% | 0.634 |
| Group F | 6 | 50.0% | 0.651 |
| Group G | 6 | 66.7% | 0.598 |
| Group H | 6 | 50.0% | 0.610 |
| Round of 16 | 8 | 75.0% | 0.576 |
| Quarterfinal | 4 | 50.0% | 0.696 |
| Semifinal | 2 | 100.0% | 0.477 |
| Third Place Playoff | 1 | 100.0% | 0.524 |
| Final | 1 | 0.0% | 0.842 |

Per-stage samples are small (1-8 matches), so read them as noisy. The overall row above is the
real signal; this table's mostly good for spotting where the model got blindsided.

### Worst-calibrated calls

The model's five most confidently wrong predictions, all draws it underrated:

- Mexico 0-0 Poland (Group C): model gave the draw 23.5%
- Cameroon 3-3 Serbia (Group G): 23.6%
- Japan 1-1 Croatia (Round of 16): 23.7%
- Croatia 0-0 Belgium (Group F): 23.7%
- Morocco 0-0 Croatia (Group F): 23.8%

Every single worst call is a draw. A Poisson model with attack/defense held neutral has no way to
boost draw probability for genuinely cagey, low-scoring matchups. Worth checking whether
`league_avg_goals` is set too high, or whether the model needs an explicit draw-boosting term
(some published soccer forecasting models add one).

## Next steps

- Re-source real eloratings.net pre-tournament values, or another verified Elo history, instead of the FIFA-points stand-in, and re-run
- Reconstruct real attack/defense coefficients from each team's pre-tournament form so the backtest checks the full pipeline, not just the rating half
- Grid-search `rating_sensitivity_gamma` and `league_avg_goals` against this dataset instead of assuming the hand-picked values are close to right
- Backtest against the 2018 World Cup too, so the calibration isn't judged on one 64-match sample
