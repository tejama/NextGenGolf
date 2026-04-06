from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Sequence
import json

from .data_layer import CSVConnector, DataConnector, SyntheticConnector
from .feature_layer import build_features
from .model_layer import project_players
from .optimization import optimize_lineups
from .reporting import per_bucket_rankings
from .schemas import LineupResult, PlayerRecord
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
    ev = optimize_lineups(
        buckets,
        artifacts,
        top_n=10,
        lineup_cap=lineup_cap,
        diversified=False,
        progress_every=progress_every,
        progress_label="ev",
    )
    div = optimize_lineups(
        buckets,
        artifacts,
        top_n=10,
        lineup_cap=lineup_cap,
        diversified=True,
        progress_every=progress_every,
        progress_label="diversified",
    )

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    with (out_path / "player_projections.json").open("w", encoding="utf-8") as f:
        json.dump({k: asdict(v) for k, v in projections.items()}, f, indent=2)
    with (out_path / "top10_ev.json").open("w", encoding="utf-8") as f:
        json.dump([asdict(x) for x in ev], f, indent=2)
    with (out_path / "top10_diversified.json").open("w", encoding="utf-8") as f:
        json.dump([asdict(x) for x in div], f, indent=2)
    with (out_path / "per_bucket_rankings.json").open("w", encoding="utf-8") as f:
        json.dump(per_bucket_rankings(projections), f, indent=2)

    return {"ev": ev, "diversified": div}


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
