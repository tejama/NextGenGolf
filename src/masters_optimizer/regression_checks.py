from __future__ import annotations

from statistics import mean
from typing import Dict

from .pipeline import run_pipeline


def run_regression_checks(config: Dict) -> Dict[str, float | bool]:
    res_a = run_pipeline(config, "output/regression_a")

    perturbed = _clone_dict(config)
    perturbed["feature_weights"]["recent_form"] *= 1.02
    res_b = run_pipeline(perturbed, "output/regression_b")

    ev_a = [x.expected_score for x in res_a["ev"]]
    ev_b = [x.expected_score for x in res_b["ev"]]
    drift = mean(abs(a - b) for a, b in zip(ev_a, ev_b))

    lineup_change = 1.0 - _avg_jaccard(res_a["ev"], res_b["ev"])
    stable = drift < 4.0
    consistent = lineup_change < 0.55

    return {
        "prediction_drift": drift,
        "lineup_change_rate": lineup_change,
        "model_stability_pass": stable,
        "lineup_consistency_pass": consistent,
        "overall_pass": bool(stable and consistent),
    }


def _avg_jaccard(lineups_a, lineups_b) -> float:
    vals = []
    for a, b in zip(lineups_a, lineups_b):
        sa, sb = set(a.players), set(b.players)
        vals.append(len(sa & sb) / len(sa | sb))
    return mean(vals)


def _clone_dict(d):
    if isinstance(d, dict):
        return {k: _clone_dict(v) for k, v in d.items()}
    if isinstance(d, list):
        return [_clone_dict(x) for x in d]
    return d
