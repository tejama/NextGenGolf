from __future__ import annotations

from statistics import mean
from typing import Dict, List
import random

from .pipeline import run_pipeline


def run_regression_checks(config: Dict) -> Dict[str, float | bool]:
    res = run_pipeline(config, "output/regression_base")

    contest = res["contest"]
    legacy = res["legacy"]

    contest_ev = [x.expected_score for x in contest]
    legacy_ev = [x.expected_score for x in legacy]

    avg_cut_gap = mean(x.cut_survival_avg for x in contest) - mean(x.cut_survival_avg for x in legacy)
    avg_win_gap = mean(x.win_equity_sum for x in contest) - mean(x.win_equity_sum for x in legacy)
    avg_top_end_gap = mean(x.top_end_hit_rate for x in contest) - mean(x.top_end_hit_rate for x in legacy)

    contest_rank_bias = _rank_bias_toward_safety(contest)
    legacy_rank_bias = _rank_bias_toward_safety(legacy)
    safety_bias_delta = contest_rank_bias - legacy_rank_bias

    lineup_change = 1.0 - _avg_jaccard(contest, legacy)

    regression_cfg = config.get("regression", {})
    n_tests = int(regression_cfg.get("n_tests", 1000))
    progress_every = int(regression_cfg.get("progress_every", 500))
    random_seed = int(regression_cfg.get("seed", 77))
    synthetic_shift = _run_stability_trials(contest_ev, n_tests=n_tests, seed=random_seed, progress_every=progress_every)

    # Contest-aware should generally trade a little cut stability for upside in a top-heavy format.
    not_floor_heavy = avg_win_gap >= -1e-6 and avg_top_end_gap >= -1e-6 and avg_cut_gap <= 0.03
    top_end_priority = safety_bias_delta <= 0.0
    stable = synthetic_shift < 0.35
    consistent = lineup_change > 0.10

    return {
        "contest_vs_legacy_expected_score_gap": mean(contest_ev) - mean(legacy_ev),
        "contest_vs_legacy_cut_survival_gap": avg_cut_gap,
        "contest_vs_legacy_win_equity_gap": avg_win_gap,
        "contest_vs_legacy_top_end_hit_rate_gap": avg_top_end_gap,
        "contest_rank_safety_bias": contest_rank_bias,
        "legacy_rank_safety_bias": legacy_rank_bias,
        "contest_minus_legacy_safety_bias": safety_bias_delta,
        "lineup_change_rate": lineup_change,
        "synthetic_shift_rate": synthetic_shift,
        "not_floor_heavy_pass": bool(not_floor_heavy),
        "top_end_priority_pass": bool(top_end_priority),
        "stability_pass": bool(stable),
        "lineup_difference_pass": bool(consistent),
        "overall_pass": bool(not_floor_heavy and top_end_priority and stable and consistent),
    }


def _rank_bias_toward_safety(lineups) -> float:
    weights = list(range(len(lineups), 0, -1))
    safety = [l.cut_survival_avg for l in lineups]
    return sum(w * s for w, s in zip(weights, safety)) / max(sum(weights), 1)


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
