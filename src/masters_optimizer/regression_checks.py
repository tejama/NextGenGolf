from __future__ import annotations

from statistics import mean
from typing import Dict, List
import random

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

    regression_cfg = config.get("regression", {})
    n_tests = int(regression_cfg.get("n_tests", 1000))
    progress_every = int(regression_cfg.get("progress_every", 500))
    random_seed = int(regression_cfg.get("seed", 77))
    synthetic_shift = _run_stability_trials(ev_a, n_tests=n_tests, seed=random_seed, progress_every=progress_every)

    stable = drift < 4.0 and synthetic_shift < 0.30
    consistent = lineup_change < 0.55

    return {
        "prediction_drift": drift,
        "lineup_change_rate": lineup_change,
        "synthetic_shift_rate": synthetic_shift,
        "model_stability_pass": stable,
        "lineup_consistency_pass": consistent,
        "overall_pass": bool(stable and consistent),
    }


def _run_stability_trials(ev_scores: List[float], n_tests: int, seed: int, progress_every: int) -> float:
    rng = random.Random(seed)
    base_order = sorted(range(len(ev_scores)), key=lambda i: ev_scores[i])
    disruptions = 0

    for i in range(1, n_tests + 1):
        noise = [rng.gauss(0.0, 0.2) for _ in ev_scores]
        shifted = [score + n for score, n in zip(ev_scores, noise)]
        test_order = sorted(range(len(shifted)), key=lambda idx: shifted[idx])

        top_k = min(5, len(base_order))
        base_top = set(base_order[:top_k])
        test_top = set(test_order[:top_k])
        jaccard = len(base_top & test_top) / len(base_top | test_top)
        if jaccard < 0.6:
            disruptions += 1

        if progress_every > 0 and i % progress_every == 0:
            print(f"[regression] completed {i}/{n_tests} stability tests")

    return disruptions / max(n_tests, 1)


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
