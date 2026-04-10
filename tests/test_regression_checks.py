from masters_optimizer.backtest import run_backtest
from masters_optimizer.pipeline import run_pipeline
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
        "optimization": {"lineup_cap": 300, "contest_top_fraction": 0.02},
        "backtest": {
            "target_cut_rate": 0.28,
            "snapshots": [],
        },
    }


def test_regression_runs():
    out = run_regression_checks(_cfg())
    assert "overall_pass" in out
    assert "not_floor_heavy_pass" in out
    assert "elite_not_underranked_pass" in out
    assert "low_ceiling_not_overloaded_pass" in out
    assert isinstance(out["contest_vs_legacy_win_equity_gap"], float)


def test_backtest_runs():
    out = run_backtest(_cfg())
    assert out["num_snapshots"] == 1.0


def test_contest_objective_prioritizes_ceiling(tmp_path):
    out = run_pipeline(_cfg(), tmp_path)
    contest = out["contest"]
    legacy = out["legacy"]

    assert len(contest) == 10
    assert len(legacy) == 10
    assert [x.players for x in contest] != [x.players for x in legacy]
    assert sum(x.objective_contest for x in contest) / 10 <= sum(x.objective_contest for x in legacy) / 10
    assert sum(x.top5_equity_sum for x in contest) / 10 >= sum(x.top5_equity_sum for x in legacy) / 10
    assert sum(x.low_ceiling_count for x in contest) / 10 <= 3.2
