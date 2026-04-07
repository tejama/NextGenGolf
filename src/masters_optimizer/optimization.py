from __future__ import annotations

import itertools
import random
from collections import Counter, defaultdict
from statistics import mean, pstdev
from typing import Dict, Iterable, List, Sequence, Set, Tuple

from .schemas import LineupResult, PipelineArtifacts


LEGACY_OBJECTIVE = "legacy_floor"
CONTEST_OBJECTIVE = "contest_ceiling"


def optimize_lineups(
    buckets: Dict[int, List[str]],
    artifacts: PipelineArtifacts,
    top_n: int = 10,
    lineup_cap: int = 5000,
    diversified: bool = False,
    progress_every: int = 0,
    progress_label: str = "optimization",
    objective_mode: str = CONTEST_OBJECTIVE,
    contest_top_fraction: float = 0.02,
) -> List[LineupResult]:
    scored = score_all_lineups(
        buckets,
        artifacts,
        lineup_cap=lineup_cap,
        progress_every=progress_every,
        progress_label=progress_label,
        contest_top_fraction=contest_top_fraction,
    )
    ranked = rank_lineups(scored, objective_mode=objective_mode)
    pool = ranked[: max(top_n * 8, 50)]

    if not diversified:
        out = pool[:top_n]
        _annotate_overlap(out)
        return out

    diversified_top = _diversify(pool, top_n, objective_mode=objective_mode)
    _annotate_overlap(diversified_top)
    return diversified_top


def score_all_lineups(
    buckets: Dict[int, List[str]],
    artifacts: PipelineArtifacts,
    lineup_cap: int,
    progress_every: int = 0,
    progress_label: str = "optimization",
    contest_top_fraction: float = 0.02,
) -> List[LineupResult]:
    candidates = list(_generate_candidates(buckets, lineup_cap=lineup_cap))
    scored: List[LineupResult] = []
    for idx, lineup in enumerate(candidates, start=1):
        scored.append(_score_lineup(lineup, artifacts))
        if progress_every > 0 and idx % progress_every == 0:
            print(f"[{progress_label}] scored {idx}/{len(candidates)} lineups")

    _annotate_contest_hit_rates(scored, contest_top_fraction=contest_top_fraction)
    for lineup in scored:
        _apply_objectives(lineup)
    return scored


def rank_lineups(scored: List[LineupResult], objective_mode: str) -> List[LineupResult]:
    if objective_mode == CONTEST_OBJECTIVE:
        ranked = sorted(scored, key=lambda x: x.objective_contest)
    elif objective_mode == LEGACY_OBJECTIVE:
        ranked = sorted(scored, key=lambda x: x.objective_legacy)
    else:
        raise ValueError(f"Unknown objective_mode: {objective_mode}")

    for lineup in ranked:
        lineup.objective_mode = objective_mode
    return ranked


def compare_objective_rankings(scored: List[LineupResult], top_n: int = 10) -> Dict[str, object]:
    legacy = rank_lineups(scored, LEGACY_OBJECTIVE)
    contest = rank_lineups(scored, CONTEST_OBJECTIVE)

    legacy_top = legacy[:top_n]
    contest_top = contest[:top_n]

    legacy_players = Counter(p for lineup in legacy_top for p in lineup.players)
    contest_players = Counter(p for lineup in contest_top for p in lineup.players)

    player_overlap = len(set(legacy_players) & set(contest_players))
    lineup_overlap = _lineup_overlap_rate(legacy_top, contest_top)

    rank_shift = {}
    legacy_idx = {tuple(x.players): i + 1 for i, x in enumerate(legacy_top)}
    for i, lineup in enumerate(contest_top, start=1):
        key = tuple(lineup.players)
        if key in legacy_idx:
            rank_shift["|".join(lineup.players)] = {"legacy_rank": legacy_idx[key], "contest_rank": i}

    exposure_diff = {}
    for player_id in sorted(set(legacy_players) | set(contest_players)):
        exposure_diff[player_id] = {
            "legacy_top10": legacy_players.get(player_id, 0),
            "contest_top10": contest_players.get(player_id, 0),
            "delta": contest_players.get(player_id, 0) - legacy_players.get(player_id, 0),
        }

    return {
        "lineup_overlap_rate": lineup_overlap,
        "player_overlap_count": player_overlap,
        "shared_player_rate": player_overlap / max(len(set(legacy_players) | set(contest_players)), 1),
        "rank_shift_examples": rank_shift,
        "exposure_diff": exposure_diff,
    }


def _lineup_overlap_rate(a: List[LineupResult], b: List[LineupResult]) -> float:
    a_set = {tuple(x.players) for x in a}
    b_set = {tuple(x.players) for x in b}
    if not a_set and not b_set:
        return 0.0
    return len(a_set & b_set) / max(len(a_set | b_set), 1)


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
    top10_equity = sum(artifacts.projections[pid].p_top10 for pid in lineup)

    exp = mean(lineup_scores)
    floor = _percentile(lineup_scores, 85)
    ceiling = _percentile(lineup_scores, 15)
    tail75 = _percentile(lineup_scores, 25)
    tail90 = _percentile(lineup_scores, 10)
    tail95 = _percentile(lineup_scores, 5)
    vol = pstdev(lineup_scores)

    rationale = (
        f"Cut profile ({mean(cut_survival):.2f}), top-10 equity {top10_equity:.3f}, "
        f"win equity {win_equity:.3f}, volatility {vol:.2f}."
    )

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
        top10_equity_sum=top10_equity,
        p75_score=tail75,
        p90_score=tail90,
        p95_score=tail95,
        simulation_scores=lineup_scores,
        rationale=rationale,
    )


def _annotate_contest_hit_rates(lineups: List[LineupResult], contest_top_fraction: float) -> None:
    if not lineups:
        return
    n_sims = len(lineups[0].simulation_scores)
    top_k = max(1, int(len(lineups) * contest_top_fraction))

    for lineup in lineups:
        lineup.top_end_hits = 0

    for sim_idx in range(n_sims):
        ranked = sorted(enumerate(lineups), key=lambda x: x[1].simulation_scores[sim_idx])
        for idx, _lineup in ranked[:top_k]:
            lineups[idx].top_end_hits += 1

    for lineup in lineups:
        lineup.top_end_hit_rate = lineup.top_end_hits / n_sims


def _apply_objectives(lineup: LineupResult) -> None:
    # Lower is better.
    lineup.objective_legacy = (
        lineup.expected_score
        + (1.0 - lineup.cut_survival_avg) * 20.0
        + lineup.volatility * 0.55
        - lineup.win_equity_sum * 4.0
    )
    lineup.objective_contest = (
        lineup.expected_score * 0.35
        + lineup.p75_score * 0.20
        + lineup.p90_score * 0.25
        + lineup.p95_score * 0.20
        - lineup.win_equity_sum * 14.0
        - lineup.top10_equity_sum * 4.0
        - lineup.top_end_hit_rate * 45.0
        + (1.0 - lineup.cut_survival_avg) * 5.0
        + lineup.volatility * 0.08
    )


def _diversify(scored: List[LineupResult], top_n: int, objective_mode: str) -> List[LineupResult]:
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
            base_obj = lineup.objective_contest if objective_mode == CONTEST_OBJECTIVE else lineup.objective_legacy
            obj = base_obj + overlap_pen + exposure_pen
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
