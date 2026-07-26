from src.backtest.runner import run_backtest, favorite_sign_baseline, uniform_baseline


def test_run_backtest_covers_all_2022_matches():
    result = run_backtest(n_simulations=500, seed=1)
    assert result["n_matches"] == 64
    assert len(result["per_match"]) == 64


def test_summary_metrics_are_bounded():
    result = run_backtest(n_simulations=500, seed=1)
    for key in ("model", "uniform", "favorite_sign_only"):
        s = result["summary"][key]
        assert 0.0 <= s["brier_score"] <= 2.0
        assert s["log_loss"] >= 0.0
        assert 0.0 <= s["accuracy"] <= 1.0


def test_uniform_baseline_is_even():
    probs = uniform_baseline(1800, 1500)
    assert probs["home_win"] == probs["draw"] == probs["away_win"]


def test_favorite_sign_baseline_favors_higher_rating():
    probs = favorite_sign_baseline(1800, 1500)
    assert probs["home_win"] > probs["away_win"]
    probs_reversed = favorite_sign_baseline(1500, 1800)
    assert probs_reversed["away_win"] > probs_reversed["home_win"]
