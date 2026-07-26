# Backtest: 2022 World Cup

The engine's parameters (`league_avg_goals`, `rating_sensitivity_gamma`, `home_advantage_factor`,
etc.) were originally hand-set for the 2026 tournament with no historical validation. This is a
first pass at checking whether the core Elo → Poisson methodology actually predicts real matches
better than simple baselines, using the last completed World Cup as ground truth.

Run it yourself: `python main.py backtest`

## Data

- **Match results**: all 64 matches of the 2022 FIFA World Cup, scored at the 90-minute mark
  (regulation time) — cross-checked against Wikipedia's group-stage and knockout-stage articles.
- **Team ratings**: FIFA World Ranking points from the **6 Oct 2022** release, the last ranking
  published before the tournament kicked off. Source: [balsillieschool.ca World Cup FIFA Rankings
  table](https://balsillieschool.ca/wp-content/uploads/2022/11/12-FIFA-Rankings.pdf).

### Known limitations of this backtest

- The live 2026 engine pulls **eloratings.net** Elo ratings, which are JS-rendered client-side and
  couldn't be bulk-exported for this pass. **FIFA ranking points are used as a substitute rating**,
  plugged into the same `rating_sensitivity_gamma` logistic formula. FIFA points and Elo are both
  logistic international-team ratings on a roughly similar scale, but they aren't the same number —
  this is a proxy, not the exact live rating source.
- **Attack/defense strength is held neutral (1.0) for every team.** The live engine also uses
  team-specific attack/defense coefficients derived from recent-form goals scored/conceded, but
  verified last-10-match form data for all 32 teams as of November 2022 wasn't available to source
  reliably. This backtest therefore only validates the **Elo-rating + home-advantage** half of the
  model, not the full pipeline.
- No market-odds baseline (unlike the live 2026 predictions, which do compare against sportsbook
  lines) — this is a look at the model in isolation.

## Results (90-minute outcome: home win / draw / away win)

| | Brier score ↓ | Log loss ↓ | Accuracy |
|---|---|---|---|
| **Engine (Elo + Poisson)** | 0.6152 | 1.0276 | 57.8% |
| Uniform (1/3, 1/3, 1/3) | 0.6667 | 1.0986 | 42.2% |
| Favorite-sign-only (fixed 50/25/25 split, no rating magnitude) | 0.5859 | 0.9856 | 57.8% |

*Favorite-sign-only* is a baseline that only knows which team is rated higher — not by how much —
and always assigns it a fixed 50% (draw 25%, underdog 25%).

**Takeaway:** the engine clearly beats guessing blind (uniform), but it does **not** beat the naive
"better-ranked team probably wins, regardless of gap size" baseline on Brier score or log loss —
it only matches it on raw accuracy. That means the specific way `rating_sensitivity_gamma` scales
the win probability into a goal-rate multiplier isn't adding predictive value over just knowing who
the favorite is. That's a real, useful negative result: it points at the gamma/lambda-shaping step
as the part of the pipeline most worth re-tuning, rather than the rating source itself.

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

Small per-stage samples (1-8 matches) make these individually noisy — read the overall row above
as the real signal, this table is mostly useful for spotting where the model got blindsided.

### Worst-calibrated calls

The model's five most confidently-wrong predictions, all draws it underrated:

- Mexico 0-0 Poland (Group C) — model gave the draw 24%
- Cameroon 3-3 Serbia (Group G) — 24%
- Japan 1-1 Croatia, R16 (Group F) — 24%
- Croatia 0-0 Belgium (Group F) — 24%
- Morocco 0-0 Croatia (Group F) — 24%

Every single worst call is a **draw**. A Poisson model with attack/defense held neutral has no
mechanism to boost draw probability for genuinely cagey, low-scoring matchups — worth investigating
whether `league_avg_goals` is calibrated too high, or whether a draw-boosting term is missing
entirely (some published soccer forecasting models add one explicitly).

## Next steps

- Re-source real eloratings.net pre-tournament values (or another verified Elo history) instead of
  the FIFA-points proxy, and re-run.
- Reconstruct real attack/defense coefficients from each team's pre-tournament form to backtest the
  full pipeline, not just the rating half.
- Grid-search `rating_sensitivity_gamma` and `league_avg_goals` against this dataset to see if a
  refit actually beats the favorite-sign-only baseline, rather than assuming the current
  hand-picked constants are close to optimal.
- Backtest against the 2018 World Cup too, so the calibration isn't judged on a single 64-match
  sample.
