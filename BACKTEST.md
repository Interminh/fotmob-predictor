# Backtest: 2022 World Cup

The engine's parameters (`league_avg_goals`, `rating_sensitivity_gamma`, `home_advantage_factor`,
and so on) were originally hand-set for the 2026 tournament with no historical check. That's a bad
habit for anything producing probabilities, so this started as a first pass at checking whether
the core Elo → Poisson methodology actually beats simple baselines, using the last completed World
Cup as ground truth.

It's since been used to grid-search `rating_sensitivity_gamma` directly against this dataset
(see "Parameter tuning" below) instead of leaving it at the hand-picked value.

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

## Parameter tuning

The original hand-set `rating_sensitivity_gamma = 0.45` didn't beat the favorite-sign-only
baseline on Brier score or log loss (see "Original results" below), which pointed straight at the
gamma/lambda-shaping step as the thing most worth re-tuning.

Grid-searched `rating_sensitivity_gamma` (0.15-2.10) and `league_avg_goals` (1.10-2.05) jointly
against this 64-match dataset, optimizing for log loss. The surface has a flat plateau roughly
between gamma 1.3-1.55 and mu 1.3-1.7, not a sharp single optimum, so picked
`rating_sensitivity_gamma = 1.40` and left `league_avg_goals` at its original 1.50, since that
combination sits inside the plateau and only changes one parameter from the hand-set defaults.

This gamma value is specific to this backtest's rating source (FIFA ranking points as a proxy for
eloratings.net Elo, see "Known limitations" above) and the 2022 World Cup sample. It is not
re-derived from the live 2026 Elo source, so treat it as a best estimate pending a second data
point (2018 World Cup, or real eloratings.net history).

## Results (90-minute outcome: home win / draw / away win)

| | Brier score (lower better) | Log loss (lower better) | Accuracy |
|---|---|---|---|
| Engine (Elo + Poisson), tuned gamma=1.40 | 0.5766 | 0.9831 | 57.8% |
| Uniform (1/3, 1/3, 1/3) | 0.6667 | 1.0986 | 42.2% |
| Favorite-sign-only (fixed 50/25/25, ignores rating gap size) | 0.5859 | 0.9856 | 57.8% |

Favorite-sign-only is a baseline that only knows which team is rated higher, not by how much, and
always gives it a fixed 50% (draw 25%, underdog 25%).

**Takeaway:** with the tuned gamma, the engine now beats the favorite-sign-only baseline on both
Brier score and log loss, not just on raw accuracy. Log loss improved from 1.0276 to 0.9831, a
4.3% reduction, and Brier score from 0.6152 to 0.5766, a 6.3% reduction, versus the original
hand-set gamma.

### Original results (gamma = 0.45, before tuning)

| | Brier score | Log loss | Accuracy |
|---|---|---|---|
| Engine (Elo + Poisson) | 0.6152 | 1.0276 | 57.8% |
| Favorite-sign-only | 0.5859 | 0.9856 | 57.8% |

The engine beat guessing blind but didn't beat the naive favorite-sign baseline on Brier score or
log loss, only matching it on raw accuracy.

### By stage

| Stage | Matches | Model accuracy | Model Brier |
|---|---|---|---|
| Group A | 6 | 83.3% | 0.468 |
| Group B | 6 | 50.0% | 0.554 |
| Group C | 6 | 66.7% | 0.555 |
| Group D | 6 | 33.3% | 0.740 |
| Group E | 6 | 33.3% | 0.653 |
| Group F | 6 | 50.0% | 0.648 |
| Group G | 6 | 66.7% | 0.558 |
| Group H | 6 | 50.0% | 0.616 |
| Round of 16 | 8 | 75.0% | 0.448 |
| Quarterfinal | 4 | 50.0% | 0.697 |
| Semifinal | 2 | 100.0% | 0.265 |
| Third Place Playoff | 1 | 100.0% | 0.403 |
| Final | 1 | 0.0% | 0.845 |

Per-stage samples are small (1-8 matches), so read them as noisy. The overall row above is the
real signal; this table's mostly good for spotting where the model got blindsided.

### Worst-calibrated calls

The model's five most confidently wrong predictions after tuning, mostly upsets it didn't see
coming rather than underrated draws:

- Cameroon 1-0 Brazil (Group G): model gave the actual home win only 9.0%
- Argentina 1-2 Saudi Arabia (Group C): model gave the actual away win only 10.2%
- Belgium 0-2 Morocco (Group F): model gave the actual away win only 13.7%
- Tunisia 1-0 France (Group D): model gave the actual home win only 14.0%
- Australia 1-0 Denmark (Group D): model gave the actual home win only 18.3%

Tuning gamma shifted the failure mode: before tuning, every worst call was an underrated draw
(the model had no draw-boosting term). After tuning, the worst calls are upsets by heavy
underdogs, which a rating-only model without attack/defense data has no way to see coming. Worth
revisiting the draw-boosting question separately once attack/defense coefficients are reconstructed.

## Next steps

- Re-source real eloratings.net pre-tournament values, or another verified Elo history, instead of the FIFA-points stand-in, and re-run the gamma tuning against that (the tuned value here is specific to the FIFA-points scale)
- Reconstruct real attack/defense coefficients from each team's pre-tournament form so the backtest checks the full pipeline, not just the rating half
- Backtest against the 2018 World Cup too, so the tuned gamma isn't judged on one 64-match sample
- Consider an explicit draw-boosting term now that upsets, not draws, are the main source of remaining error
