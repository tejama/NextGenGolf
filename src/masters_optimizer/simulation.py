from __future__ import annotations

import random
from typing import Dict, List

from .schemas import PipelineArtifacts, PlayerProjection


def simulate_tournament(
    projections: Dict[str, PlayerProjection],
    n_sims: int,
    seed: int,
    missed_cut_penalty: float,
) -> PipelineArtifacts:
    rng = random.Random(seed)
    ids = list(projections.keys())
    all_scores: Dict[str, List[float]] = {pid: [] for pid in ids}
    missed: Dict[str, int] = {pid: 0 for pid in ids}

    for _ in range(n_sims):
        two = {}
        for pid, p in projections.items():
            two[pid] = rng.gauss(p.exp_round_score, p.round_std) + rng.gauss(p.exp_round_score, p.round_std)

        cutline = _percentile(list(two.values()), 65)

        for pid, p in projections.items():
            made_cut = (two[pid] <= cutline) and (rng.random() < p.p_make_cut)
            if made_cut:
                total = two[pid] + rng.gauss(p.exp_round_score, p.round_std) + rng.gauss(p.exp_round_score, p.round_std)
            else:
                missed[pid] += 1
                total = two[pid] + missed_cut_penalty
            all_scores[pid].append(total)

    missed_rates = {pid: missed[pid] / n_sims for pid in ids}
    return PipelineArtifacts(projections=projections, simulation_scores=all_scores, missed_cut_rates=missed_rates)


def _percentile(vals: List[float], q: float) -> float:
    arr = sorted(vals)
    if not arr:
        return 0.0
    idx = int((q / 100.0) * (len(arr) - 1))
    return arr[idx]
