from masters_optimizer.pipeline import run_pipeline


def _cfg():
    return {
        "data": {"source": "synthetic", "seed": 7, "players_per_bucket": 3},
        "feature_weights": {
            "recent_form": 1.0,
            "baseline_skill": 1.0,
            "augusta_fit": 1.0,
            "volatility": 1.0,
        },
        "model": {"recent_weight": 0.45, "long_term_weight": 0.55},
        "simulation": {"n_sims": 2000, "seed": 99, "missed_cut_penalty": 155.0},
        "optimization": {"lineup_cap": 500},
    }


def test_pipeline_outputs_top10(tmp_path):
    res = run_pipeline(_cfg(), tmp_path)
    assert len(res["ev"]) == 10
    assert len(res["diversified"]) == 10
    assert all(len(x.players) == 13 for x in res["ev"])


def test_pipeline_deterministic(tmp_path):
    a = run_pipeline(_cfg(), tmp_path / "a")
    b = run_pipeline(_cfg(), tmp_path / "b")
    assert [x.players for x in a["ev"]] == [x.players for x in b["ev"]]
