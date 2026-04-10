from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Sequence
import csv
import json

from .data_layer import CSVConnector, DataConnector, SyntheticConnector
from .feature_layer import build_features
from .model_layer import project_players
from .optimization import (
    CONTEST_OBJECTIVE,
    LEGACY_OBJECTIVE,
    compare_objective_rankings,
    optimize_lineups,
    score_all_lineups,
)
from .reporting import per_bucket_rankings, player_diagnostics
from .schemas import LineupResult, PlayerRecord, PlayerProjection
from .simulation import simulate_tournament


def run_pipeline(
    config: Dict,
    output_dir: str | Path,
    locked_players: Sequence[str] | None = None,
    excluded_players: Sequence[str] | None = None,
) -> Dict[str, List[LineupResult]]:
    locked_players = list(locked_players or [])
    excluded_players = set(excluded_players or [])

    connector = _build_connector(config)
    players = [p for p in connector.load_players() if p.player_id not in excluded_players]
    _validate_buckets(players)

    features = build_features(players, config["feature_weights"])
    projections = project_players(features, config["model"])
    artifacts = simulate_tournament(
        projections,
        n_sims=int(config["simulation"]["n_sims"]),
        seed=int(config["simulation"]["seed"]),
        missed_cut_penalty=float(config["simulation"]["missed_cut_penalty"]),
    )

    buckets = _bucket_map(players, locked_players=locked_players)
    lineup_cap = int(config.get("optimization", {}).get("lineup_cap", 3000))
    progress_every = int(config.get("optimization", {}).get("progress_every", 0))
    contest_top_fraction = float(config.get("optimization", {}).get("contest_top_fraction", 0.02))

    scored = score_all_lineups(
        buckets,
        artifacts,
        lineup_cap=lineup_cap,
        progress_every=progress_every,
        progress_label="all-objectives",
        contest_top_fraction=contest_top_fraction,
    )

    contest = optimize_lineups(
        buckets,
        artifacts,
        top_n=10,
        lineup_cap=lineup_cap,
        diversified=False,
        progress_every=0,
        objective_mode=CONTEST_OBJECTIVE,
        contest_top_fraction=contest_top_fraction,
    )
    contest_div = optimize_lineups(
        buckets,
        artifacts,
        top_n=10,
        lineup_cap=lineup_cap,
        diversified=True,
        progress_every=0,
        objective_mode=CONTEST_OBJECTIVE,
        contest_top_fraction=contest_top_fraction,
    )
    legacy = optimize_lineups(
        buckets,
        artifacts,
        top_n=10,
        lineup_cap=lineup_cap,
        diversified=False,
        progress_every=0,
        objective_mode=LEGACY_OBJECTIVE,
        contest_top_fraction=contest_top_fraction,
    )

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    with (out_path / "player_projections.json").open("w", encoding="utf-8") as f:
        json.dump({k: asdict(v) for k, v in projections.items()}, f, indent=2)
    with (out_path / "top10_contest_aware.json").open("w", encoding="utf-8") as f:
        json.dump([_serialize_lineup(x) for x in contest], f, indent=2)
    with (out_path / "top10_legacy_floor.json").open("w", encoding="utf-8") as f:
        json.dump([_serialize_lineup(x) for x in legacy], f, indent=2)
    with (out_path / "top10_diversified.json").open("w", encoding="utf-8") as f:
        json.dump([_serialize_lineup(x) for x in contest_div], f, indent=2)
    with (out_path / "per_bucket_rankings.json").open("w", encoding="utf-8") as f:
        json.dump(per_bucket_rankings(projections), f, indent=2)
    with (out_path / "player_diagnostics.json").open("w", encoding="utf-8") as f:
        json.dump(player_diagnostics(features, projections), f, indent=2)
    with (out_path / "objective_comparison.json").open("w", encoding="utf-8") as f:
        json.dump(compare_objective_rankings(scored, top_n=10), f, indent=2)

    _write_lineup_csvs(out_path, contest, contest_div, legacy, projections)

    return {
        "ev": contest,
        "diversified": contest_div,
        "contest": contest,
        "legacy": legacy,
    }


def _serialize_lineup(lineup: LineupResult) -> dict:
    payload = asdict(lineup)
    payload.pop("simulation_scores", None)
    return payload


def _write_lineup_csvs(
    out_path: Path,
    contest_lineups: List[LineupResult],
    diversified_lineups: List[LineupResult],
    legacy_lineups: List[LineupResult],
    projections: Dict[str, PlayerProjection],
) -> None:
    wide_cols = [
        "mode",
        "rank",
        "expected_score",
        "floor",
        "ceiling",
        "p75_score",
        "p90_score",
        "p95_score",
        "top_end_hit_rate",
        "volatility",
        "best8_expected",
        "cut_survival_avg",
        "win_equity_sum",
        "top5_equity_sum",
        "top10_equity_sum",
        "low_ceiling_count",
        "elite_or_volatile_count",
        "objective_legacy",
        "objective_contest",
        "lineup_justification",
    ]
    for i in range(1, 14):
        wide_cols.extend([f"bucket_{i}_player", f"bucket_{i}_player_id"])

    with (out_path / "top10_lineups.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=wide_cols)
        writer.writeheader()
        for mode, lineups in [
            ("contest", contest_lineups),
            ("contest_diversified", diversified_lineups),
            ("legacy_floor", legacy_lineups),
        ]:
            for rank, lineup in enumerate(lineups, start=1):
                row = {
                    "mode": mode,
                    "rank": rank,
                    "expected_score": f"{lineup.expected_score:.2f}",
                    "floor": f"{lineup.floor:.2f}",
                    "ceiling": f"{lineup.ceiling:.2f}",
                    "p75_score": f"{lineup.p75_score:.2f}",
                    "p90_score": f"{lineup.p90_score:.2f}",
                    "p95_score": f"{lineup.p95_score:.2f}",
                    "top_end_hit_rate": f"{lineup.top_end_hit_rate:.4f}",
                    "volatility": f"{lineup.volatility:.2f}",
                    "best8_expected": f"{lineup.best8_expected:.2f}",
                    "cut_survival_avg": f"{lineup.cut_survival_avg:.3f}",
                    "win_equity_sum": f"{lineup.win_equity_sum:.3f}",
                    "top5_equity_sum": f"{lineup.top5_equity_sum:.3f}",
                    "top10_equity_sum": f"{lineup.top10_equity_sum:.3f}",
                    "low_ceiling_count": lineup.low_ceiling_count,
                    "elite_or_volatile_count": lineup.elite_or_volatile_count,
                    "objective_legacy": f"{lineup.objective_legacy:.3f}",
                    "objective_contest": f"{lineup.objective_contest:.3f}",
                    "lineup_justification": _lineup_english(lineup),
                }
                for idx, (name, pid) in enumerate(zip(lineup.player_names, lineup.players), start=1):
                    row[f"bucket_{idx}_player"] = name
                    row[f"bucket_{idx}_player_id"] = pid
                writer.writerow(row)

    long_cols = [
        "mode",
        "rank",
        "bucket",
        "player_name",
        "player_id",
        "p_make_cut",
        "p_top10",
        "p_top5",
        "p_win",
        "birdie_burst",
        "archetype",
        "pick_label",
        "pick_justification",
    ]
    with (out_path / "all_picks_with_justification.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=long_cols)
        writer.writeheader()
        for mode, lineups in [
            ("contest", contest_lineups),
            ("contest_diversified", diversified_lineups),
            ("legacy_floor", legacy_lineups),
        ]:
            for rank, lineup in enumerate(lineups, start=1):
                for pid, name in zip(lineup.players, lineup.player_names):
                    p = projections[pid]
                    label, justification = _pick_english(p)
                    writer.writerow(
                        {
                            "mode": mode,
                            "rank": rank,
                            "bucket": p.bucket,
                            "player_name": name,
                            "player_id": pid,
                            "p_make_cut": f"{p.p_make_cut:.3f}",
                            "p_top10": f"{p.p_top10:.3f}",
                            "p_top5": f"{p.p_top5:.3f}",
                            "p_win": f"{p.p_win:.3f}",
                            "birdie_burst": f"{p.birdie_burst:.3f}",
                            "archetype": p.archetype,
                            "pick_label": label,
                            "pick_justification": justification,
                        }
                    )


def _lineup_english(lineup: LineupResult) -> str:
    return (
        "Prioritizes high-end best-8 tournament outcomes with explicit contest tail emphasis. "
        f"Top-end hit rate {lineup.top_end_hit_rate:.3f}, p95 lineup score {lineup.p95_score:.2f}, "
        f"win equity {lineup.win_equity_sum:.3f}, top-5 equity {lineup.top5_equity_sum:.3f}, and cut survival {lineup.cut_survival_avg:.2f}."
    )


def _pick_english(proj: PlayerProjection) -> tuple[str, str]:
    if proj.archetype == "elite_contender":
        return (
            "elite win-equity play",
            "Win probability is strong enough to drive first-place paths, even if variance is elevated.",
        )
    if proj.archetype == "high_ceiling_volatile":
        return (
            "high-ceiling contender",
            "Top-10 frequency meaningfully raises lineup ceiling and best-8 scoring in top-heavy outcomes.",
        )
    if proj.archetype == "low_ceiling_safety":
        return (
            "cut-stable but limited ceiling",
            "Main value is preserving best-8 coverage; slate-winning upside is more limited.",
        )
    if proj.archetype == "balanced_contributor":
        return (
            "strong best-8 contributor",
            "Profile blends cut survival with enough top-end finish equity to matter in ceiling builds.",
        )
    return (
        "portfolio diversification play",
        "Used to diversify correlated outcomes while preserving a plausible path to best-8 contribution.",
    )


def _build_connector(config: Dict) -> DataConnector:
    source = config["data"]["source"]
    if source == "csv":
        return CSVConnector(config["data"]["player_csv"])
    if source == "synthetic":
        return SyntheticConnector(
            seed=int(config["data"].get("seed", 42)),
            players_per_bucket=int(config["data"].get("players_per_bucket", 4)),
        )
    raise ValueError(f"Unsupported data source: {source}")


def _bucket_map(players: List[PlayerRecord], locked_players: Sequence[str]) -> Dict[int, List[str]]:
    by_id = {p.player_id: p for p in players}
    locks_by_bucket = {}
    for pid in locked_players:
        if pid not in by_id:
            continue
        b = by_id[pid].bucket
        if b in locks_by_bucket and locks_by_bucket[b] != pid:
            raise ValueError(f"Multiple locks in bucket {b}: {locks_by_bucket[b]}, {pid}")
        locks_by_bucket[b] = pid

    buckets: Dict[int, List[str]] = {}
    for p in players:
        buckets.setdefault(p.bucket, []).append(p.player_id)

    for b in buckets:
        if b in locks_by_bucket:
            buckets[b] = [locks_by_bucket[b]]
        else:
            buckets[b] = sorted(buckets[b])
    return buckets


def _validate_buckets(players: List[PlayerRecord]) -> None:
    buckets = {p.bucket for p in players}
    missing = set(range(1, 14)).difference(buckets)
    if missing:
        raise ValueError(f"Missing bucket(s): {sorted(missing)}")
