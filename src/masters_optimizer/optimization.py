from __future__ import annotations

import itertools
import random
from collections import defaultdict
from statistics import mean, pstdev
from typing import Dict, Iterable, List, Sequence, Set, Tuple

from .schemas import LineupResult, PipelineArtifacts


def optimize_lineups(
    buckets: Dict[int, List[str]],
    artifacts: PipelineArtifacts,
    top_n: int = 10,
    lineup_cap: int = 5000,
    diversified: bool = False,
    progress_every: int = 0,
    progress_label: str = "optimization",
) -> List[LineupResult]:
    candidates = list(_generate_candidates(buckets, lineup_cap=lineup_cap))
    scored = []
    for idx, lineup in enumerate(candidates, start=1):
        scored.append(_score_lineup(lineup, artifacts))
        if progress_every > 0 and idx % progress_every == 0:
            print(f"[{progress_label}] scored {idx}/{len(candidates)} lineups")

    scored.sort(key=lambda x: x.expected_score)
    ev_top = scored[: max(top_n * 8, 50)]

    if not diversified:
        out = ev_top[:top_n]
        _annotate_overlap(out)
        return out

    diversified_top = _diversify(ev_top, top_n)
    _annotate_overlap(diversified_top)
    return diversified_top


def _generate_candidates(buckets: Dict[int, List[str]], lineup_cap: int) -> Iterable[Tuple[str, ...]]:
    ordered = [buckets[b] for b in sorted(buckets)]
    total = 1
    for x in ordered:
        total *= max(1, len(x))
    if total <= lineup_cap:
        return list(itertools.product(*ordered))

    trimmed = [bucket_players[: min(3, len(bucket_players))] for bucket_players in ordered]
    total_trim = 1
    for x in trimmed:
        total_trim *= max(1, len(x))
    if total_trim <= lineup_cap:
        return list(itertools.product(*trimmed))

    rng = random.Random(7)
    samples = []
    for _ in range(lineup_cap):
        lineup = tuple(bucket_players[rng.randrange(len(bucket_players))] for bucket_players in trimmed)
        samples.append(lineup)
    seen, unique = set(), []
    for s in samples:
        if s in seen:
            continue
        seen.add(s)
        unique.append(s)
    return unique


def _score_lineup(lineup: Sequence[str], artifacts: PipelineArtifacts) -> LineupResult:
    n_sims = len(next(iter(artifacts.simulation_scores.values())))
    per_player = [artifacts.simulation_scores[pid] for pid in lineup]
    per_player_expected = [mean(vals) for vals in per_player]
    best8_expected = sum(sorted(per_player_expected)[:8])

    lineup_scores = []
    for i in range(n_sims):
        lineup_scores.append(sum(sorted(vals[i] for vals in per_player)[:8]))

    cut_survival = [1.0 - artifacts.missed_cut_rates[pid] for pid in lineup]
    win_equity = sum(artifacts.projections[pid].win_equity for pid in lineup)

    exp = mean(lineup_scores)
    floor = _percentile(lineup_scores, 85)
    ceiling = _percentile(lineup_scores, 15)
    vol = pstdev(lineup_scores)

    rationale = f"Balanced cut profile ({mean(cut_survival):.2f}), win equity {win_equity:.3f}, volatility {vol:.2f}."

    return LineupResult(
        players=list(lineup),
        player_names=[artifacts.projections[pid].name for pid in lineup],
        expected_score=exp,
        floor=floor,
        ceiling=ceiling,
        volatility=vol,
        best8_expected=best8_expected,
        cut_survival_avg=mean(cut_survival),
        win_equity_sum=win_equity,
        rationale=rationale,
    )


def _diversify(scored: List[LineupResult], top_n: int) -> List[LineupResult]:
    selected: List[LineupResult] = []
    exposure: Dict[str, int] = defaultdict(int)

    while len(selected) < top_n and scored:
        best_idx, best_score = None, float("inf")
        for idx, lineup in enumerate(scored[:500]):
            overlap_pen = 0.0
            for chosen in selected:
                overlap = len(set(lineup.players) & set(chosen.players)) / len(lineup.players)
                overlap_pen += overlap * 7.0
            exposure_pen = sum(exposure[p] for p in lineup.players) * 0.08
            obj = lineup.expected_score + overlap_pen + exposure_pen
            if obj < best_score:
                best_score, best_idx = obj, idx
        if best_idx is None:
            break
        chosen = scored.pop(best_idx)
        selected.append(chosen)
        for p in chosen.players:
            exposure[p] += 1
    return selected


def _annotate_overlap(lineups: List[LineupResult]) -> None:
    for i, lineup in enumerate(lineups):
        others: Set[str] = set()
        for j, other in enumerate(lineups):
            if i != j:
                others.update(other.players)
        lineup.overlap_pct = 100.0 * len(set(lineup.players) & others) / len(lineup.players)


def _percentile(vals: List[float], q: float) -> float:
    arr = sorted(vals)
    idx = int((q / 100.0) * (len(arr) - 1))
    return arr[idx]
