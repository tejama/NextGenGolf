from masters_optimizer.backtest import run_backtest
from masters_optimizer.regression_checks import run_regression_checks


def _cfg():
    return {
        "data": {"source": "synthetic", "seed": 11, "players_per_bucket": 3},
        "feature_weights": {
            "recent_form": 1.0,
            "baseline_skill": 1.0,
            "augusta_fit": 1.0,
            "volatility": 1.0,
        },
        "model": {"recent_weight": 0.45, "long_term_weight": 0.55},
        "simulation": {"n_sims": 1200, "seed": 9, "missed_cut_penalty": 155.0},
        "optimization": {"lineup_cap": 300},
        "backtest": {
            "target_cut_rate": 0.28,
            "snapshots": [],
        },
    }


def test_regression_runs():
    out = run_regression_checks(_cfg())
    assert "overall_pass" in out
    assert isinstance(out["prediction_drift"], float)


def test_backtest_runs():
    out = run_backtest(_cfg())
    assert out["num_snapshots"] == 1.0
