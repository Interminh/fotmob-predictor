// ============================================================================
// data.js — World Cup 2026 Predictor match data
//
// This is the ONLY file you should ever need to edit. The HTML never changes.
//
// HOW TO UPDATE A RESULT WHEN A MATCH FINISHES:
//   1. Find the match by match_id below.
//   2. Set status: "completed"
//   3. Set actual_score: "H-A"   (the 90-minute score — that's what scoring
//      is graded against, per meta.scoring_rules and data/scoring_rules.json
//      in the main project)
//   4. Leave points_earned as null — the page computes it automatically from
//      predicted_score vs actual_score using meta.scoring_rules. You only
//      need to set points_earned by hand if you want to override the auto
//      calculation for some reason.
//   5. If the match went to extra time / penalties, add a short "note" string
//      (see R32_3, R32_4, R32_9 below for examples) — it's cosmetic only and
//      doesn't affect points, since points are graded on the 90-minute score.
//
// predicted_score is the model's single pick: round(lambda_home), round(lambda_away).
// This is NOT the old "most likely single cell" (EV-optimal / top probability
// score) — that approach floors away the fractional part of both lambdas and
// systematically undershoots real goal totals (it defaulted to 1-0 almost
// every match). Rounding the raw expected goals instead tracks the mean of
// each team's Poisson distribution, which is what you want from a single
// point-estimate. See src/engine/score_optimizer.py::rounded_scoreline in the
// main project for the implementation this data was generated from.
// ============================================================================

window.MATCH_DATA = {
  meta: {
    model_name: "Monte Carlo Poisson (N=10,000, recalibrated)",
    pool_name: "FotMob Predict 2026",
    // Matches data/scoring_rules.json in the main project: exact score = 3,
    // goal_diff bonus is disabled (0, folded into outcome), correct outcome = 2.
    scoring_rules: { exact: 3, goal_diff: 0, outcome: 2 },
    last_updated: "2026-07-01"
  },

  // ------------------------------------------------------------------------
  // HOW TO UPDATE COMPARISON MODELS (see also the walkthrough below):
  //
  // "Naive Baseline" always predicts the home (first-listed) team to win 1-0.
  //   Its exact_scores = count of R32 matches whose 90-minute score was
  //   literally 1-0 to the home team. Its correct_outcomes = count of R32
  //   matches the home team won by any score (draws/away wins score 0).
  //
  // "Simple Elo (outcome only)" always predicts the Elo-favourite to win 1-0,
  //   scored from that team's home/away slot. Elo favourites in these 10
  //   completed R32 matches: CAN, BRA, GER, NED, NOR (away side), FRA, MEX,
  //   ENG, BEL, USA.
  //
  // Both baselines below are computed directly from the 10 completed R32
  // results using data/scoring_rules.json's points (exact=3, outcome=2,
  // wrong=0) — same rules as the model. Recompute the same way as more
  // rounds finish: for each completed match, apply the baseline's fixed
  // pick against the real 90-minute score.
  //
  // "FotMob Community" is left null — no public aggregate data available yet.
  // Fill it in from the pool's real leaderboard once accessible.
  // ------------------------------------------------------------------------
  comparison_models: [
    {
      name: "FotMob Community",
      description: "Aggregate of all public FotMob Predict picks",
      points_scored: null,
      correct_outcomes: null,
      exact_scores: null
    },
    {
      name: "Simple Elo (outcome only)",
      description: "Always picks the Elo-favourite to win 1-0",
      points_scored: 15,
      correct_outcomes: 7,
      exact_scores: 1
    },
    {
      name: "Naive Baseline",
      description: "Always predicts 1-0 to the team listed first",
      points_scored: 13,
      correct_outcomes: 6,
      exact_scores: 1
    }
  ],

  matches: [
    {
      match_id: "R32_1",
      home: "Canada", home_code: "CAN",
      away: "South Africa", away_code: "RSA",
      date: "2026-06-28",
      status: "completed",
      predicted_score: "2-1",
      top_scores: [
        { score: "1-1", prob: 0.1163 },
        { score: "1-0", prob: 0.1147 },
        { score: "2-0", prob: 0.1037 }
      ],
      outcome_probs: { home: 0.5375, draw: 0.2451, away: 0.2174 },
      lambda: { home: 1.676, away: 0.952 },
      actual_score: "1-0",
      points_earned: null,
      note: "Eustaquio 90+2'"
    },
    {
      match_id: "R32_2",
      home: "Brazil", home_code: "BRA",
      away: "Japan", away_code: "JPN",
      date: "2026-06-29",
      status: "completed",
      predicted_score: "2-1",
      top_scores: [
        { score: "1-1", prob: 0.1168 },
        { score: "1-0", prob: 0.1058 },
        { score: "2-1", prob: 0.0957 }
      ],
      outcome_probs: { home: 0.4766, draw: 0.2497, away: 0.2738 },
      lambda: { home: 1.568, away: 1.121 },
      actual_score: "2-1",
      points_earned: null,
      note: "Casemiro 56', Martinelli 90+5' — Sano 29'"
    },
    {
      match_id: "R32_3",
      home: "Germany", home_code: "GER",
      away: "Paraguay", away_code: "PRY",
      date: "2026-06-29",
      status: "completed",
      predicted_score: "2-1",
      top_scores: [
        { score: "1-1", prob: 0.1031 },
        { score: "2-1", prob: 0.0986 },
        { score: "1-0", prob: 0.0940 }
      ],
      outcome_probs: { home: 0.5603, draw: 0.2207, away: 0.2191 },
      lambda: { home: 1.889, away: 1.081 },
      actual_score: "1-1",
      points_earned: null,
      note: "a.e.t. — Paraguay won on penalties 4-3. Pre-tournament favourite eliminated."
    },
    {
      match_id: "R32_4",
      home: "Netherlands", home_code: "NED",
      away: "Morocco", away_code: "MAR",
      date: "2026-06-29",
      status: "completed",
      predicted_score: "1-1",
      top_scores: [
        { score: "1-1", prob: 0.1254 },
        { score: "1-0", prob: 0.1011 },
        { score: "0-1", prob: 0.0941 }
      ],
      outcome_probs: { home: 0.3955, draw: 0.2635, away: 0.3411 },
      lambda: { home: 1.348, away: 1.215 },
      actual_score: "1-1",
      points_earned: null,
      note: "a.e.t. — Morocco won on penalties 3-2. Pre-tournament favourite eliminated."
    },
    {
      match_id: "R32_5",
      home: "Ivory Coast", home_code: "CIV",
      away: "Norway", away_code: "NOR",
      date: "2026-06-30",
      status: "completed",
      predicted_score: "1-2",
      top_scores: [
        { score: "1-1", prob: 0.1142 },
        { score: "0-1", prob: 0.1137 },
        { score: "0-2", prob: 0.1008 }
      ],
      outcome_probs: { home: 0.2027, draw: 0.2382, away: 0.5592 },
      lambda: { home: 0.954, away: 1.755 },
      actual_score: "1-2",
      points_earned: null,
      note: "Diallo 74' — Nusa 39', Haaland 86'"
    },
    {
      match_id: "R32_6",
      home: "France", home_code: "FRA",
      away: "Sweden", away_code: "SWE",
      date: "2026-06-30",
      status: "completed",
      predicted_score: "2-1",
      top_scores: [
        { score: "2-0", prob: 0.1210 },
        { score: "1-0", prob: 0.1108 },
        { score: "2-1", prob: 0.0977 }
      ],
      outcome_probs: { home: 0.7018, draw: 0.1800, away: 0.1183 },
      lambda: { home: 2.221, away: 0.791 },
      actual_score: "3-0",
      points_earned: null,
      note: "Mbappe 45', 74', Barcola 53'"
    },
    {
      match_id: "R32_7",
      home: "Mexico", home_code: "MEX",
      away: "Ecuador", away_code: "ECU",
      date: "2026-06-30",
      status: "completed",
      predicted_score: "1-1",
      top_scores: [
        { score: "1-1", prob: 0.1252 },
        { score: "1-0", prob: 0.1113 },
        { score: "2-1", prob: 0.0890 }
      ],
      outcome_probs: { home: 0.4257, draw: 0.2620, away: 0.3124 },
      lambda: { home: 1.397, away: 1.159 },
      actual_score: "2-0",
      points_earned: null,
      note: "Quinones, Jimenez"
    },
    {
      match_id: "R32_8",
      home: "England", home_code: "ENG",
      away: "DR Congo", away_code: "COD",
      date: "2026-07-01",
      status: "completed",
      predicted_score: "2-1",
      top_scores: [
        { score: "2-0", prob: 0.1131 },
        { score: "1-0", prob: 0.1025 },
        { score: "2-1", prob: 0.0986 }
      ],
      outcome_probs: { home: 0.6551, draw: 0.1947, away: 0.1503 },
      lambda: { home: 2.114, away: 0.890 },
      actual_score: "2-1",
      points_earned: null,
      note: "Kane 75', 86' — Cipenga early"
    },
    {
      match_id: "R32_9",
      home: "Belgium", home_code: "BEL",
      away: "Senegal", away_code: "SEN",
      date: "2026-07-01",
      status: "completed",
      predicted_score: "1-1",
      top_scores: [
        { score: "1-1", prob: 0.1285 },
        { score: "1-0", prob: 0.1062 },
        { score: "0-1", prob: 0.1017 }
      ],
      outcome_probs: { home: 0.3791, draw: 0.2743, away: 0.3467 },
      lambda: { home: 1.265, away: 1.184 },
      actual_score: "2-2",
      points_earned: null,
      note: "2-2 at 90', a.e.t. 3-2 — Belgium won on a stoppage-time penalty in extra time"
    },
    {
      match_id: "R32_10",
      home: "United States", home_code: "USA",
      away: "Bosnia and Herzegovina", away_code: "BIH",
      date: "2026-07-01",
      status: "completed",
      predicted_score: "2-1",
      top_scores: [
        { score: "1-0", prob: 0.1167 },
        { score: "2-0", prob: 0.1131 },
        { score: "1-1", prob: 0.1008 }
      ],
      outcome_probs: { home: 0.6123, draw: 0.2164, away: 0.1714 },
      lambda: { home: 1.898, away: 0.889 },
      actual_score: "2-0",
      points_earned: null,
      note: "Balogun, Tillman"
    },
    {
      match_id: "R32_11",
      home: "Spain", home_code: "ESP",
      away: "Austria", away_code: "AUT",
      date: "2026-07-02",
      status: "upcoming",
      predicted_score: "2-1",
      top_scores: [
        { score: "2-0", prob: 0.1113 },
        { score: "1-0", prob: 0.1063 },
        { score: "2-1", prob: 0.0977 }
      ],
      outcome_probs: { home: 0.6499, draw: 0.2011, away: 0.1490 },
      lambda: { home: 2.085, away: 0.881 },
      actual_score: null,
      points_earned: null
    },
    {
      match_id: "R32_12",
      home: "Portugal", home_code: "POR",
      away: "Croatia", away_code: "CRO",
      date: "2026-07-02",
      status: "upcoming",
      predicted_score: "2-1",
      top_scores: [
        { score: "1-1", prob: 0.1108 },
        { score: "1-0", prob: 0.1032 },
        { score: "2-1", prob: 0.0975 }
      ],
      outcome_probs: { home: 0.5225, draw: 0.2357, away: 0.2419 },
      lambda: { home: 1.731, away: 1.092 },
      actual_score: null,
      points_earned: null
    },
    {
      match_id: "R32_13",
      home: "Switzerland", home_code: "SUI",
      away: "Algeria", away_code: "ALG",
      date: "2026-07-02",
      status: "upcoming",
      predicted_score: "2-1",
      top_scores: [
        { score: "1-0", prob: 0.1152 },
        { score: "1-1", prob: 0.1089 },
        { score: "2-0", prob: 0.1001 }
      ],
      outcome_probs: { home: 0.5564, draw: 0.2356, away: 0.2081 },
      lambda: { home: 1.752, away: 0.958 },
      actual_score: null,
      points_earned: null
    },
    {
      match_id: "R32_14",
      home: "Colombia", home_code: "COL",
      away: "Ghana", away_code: "GHA",
      date: "2026-07-03",
      status: "upcoming",
      predicted_score: "2-1",
      top_scores: [
        { score: "2-0", prob: 0.1302 },
        { score: "1-0", prob: 0.1159 },
        { score: "3-0", prob: 0.0968 }
      ],
      outcome_probs: { home: 0.7103, draw: 0.1787, away: 0.1110 },
      lambda: { home: 2.209, away: 0.728 },
      actual_score: null,
      points_earned: null
    },
    {
      match_id: "R32_15",
      home: "Australia", home_code: "AUS",
      away: "Egypt", away_code: "EGY",
      date: "2026-07-03",
      status: "upcoming",
      predicted_score: "2-1",
      top_scores: [
        { score: "1-1", prob: 0.1194 },
        { score: "1-0", prob: 0.1053 },
        { score: "2-1", prob: 0.0921 }
      ],
      outcome_probs: { home: 0.4653, draw: 0.2516, away: 0.2832 },
      lambda: { home: 1.553, away: 1.144 },
      actual_score: null,
      points_earned: null
    },
    {
      match_id: "R32_16",
      home: "Argentina", home_code: "ARG",
      away: "Cape Verde", away_code: "CPV",
      date: "2026-07-03",
      status: "upcoming",
      predicted_score: "3-1",
      top_scores: [
        { score: "2-0", prob: 0.1303 },
        { score: "3-0", prob: 0.1281 },
        { score: "4-0", prob: 0.0948 }
      ],
      outcome_probs: { home: 0.8507, draw: 0.1034, away: 0.0460 },
      lambda: { home: 2.931, away: 0.561 },
      actual_score: null,
      points_earned: null
    }
  ]
};
