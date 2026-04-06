from __future__ import annotations

from abc import ABC, abstractmethod
import csv
import random
from pathlib import Path
from typing import List

from .schemas import PlayerRecord


class DataConnector(ABC):
    @abstractmethod
    def load_players(self) -> List[PlayerRecord]:
        raise NotImplementedError


class CSVConnector(DataConnector):
    def __init__(self, player_csv: str | Path):
        self.player_csv = Path(player_csv)

    def load_players(self) -> List[PlayerRecord]:
        rows = []
        with self.player_csv.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(_row_to_record(row))
        return rows


class SyntheticConnector(DataConnector):
    def __init__(self, seed: int = 42, players_per_bucket: int = 4):
        self.seed = seed
        self.players_per_bucket = players_per_bucket

    def load_players(self) -> List[PlayerRecord]:
        rng = random.Random(self.seed)
        rows: List[PlayerRecord] = []
        for bucket in range(1, 14):
            for i in range(self.players_per_bucket):
                pid = f"B{bucket:02d}_P{i+1}"
                recent = [max(1.0, min(90.0, rng.gauss(30, 12))) for _ in range(8)]
                rows.append(
                    PlayerRecord(
                        player_id=pid,
                        name=f"Player {bucket}-{i+1}",
                        bucket=bucket,
                        sg_off_tee=rng.gauss(0.2, 0.6),
                        sg_approach=rng.gauss(0.3, 0.7),
                        sg_arg=rng.gauss(0.1, 0.5),
                        sg_putting=rng.gauss(0.0, 0.5),
                        driving_distance=rng.gauss(305, 12),
                        driving_accuracy=_clip(rng.gauss(0.62, 0.08), 0.4, 0.85),
                        gir=_clip(rng.gauss(0.68, 0.06), 0.45, 0.85),
                        scrambling=_clip(rng.gauss(0.58, 0.07), 0.35, 0.8),
                        par5_scoring=rng.gauss(4.55, 0.08),
                        bogey_avoidance=_clip(rng.gauss(0.84, 0.04), 0.65, 0.95),
                        double_bogey_rate=_clip(rng.gauss(0.035, 0.012), 0.01, 0.09),
                        cut_rate=_clip(rng.gauss(0.78, 0.12), 0.35, 0.98),
                        masters_history=rng.gauss(0.0, 1.0),
                        augusta_correlated=rng.gauss(0.0, 1.0),
                        majors_perf=rng.gauss(0.0, 1.0),
                        field_adjusted_finish=rng.gauss(0.0, 1.0),
                        odds_win=_clip(_lognormal(rng, -3.2, 0.7), 0.005, 0.15),
                        odds_top5=_clip(_lognormal(rng, -1.9, 0.55), 0.02, 0.42),
                        odds_top10=_clip(_lognormal(rng, -1.2, 0.45), 0.05, 0.65),
                        recent_finishes=recent,
                    )
                )
        return rows


def _row_to_record(row) -> PlayerRecord:
    recent = [float(x) for x in str(row["recent_finishes"]).split(";") if x]
    f = lambda k: float(row[k])
    return PlayerRecord(
        player_id=str(row["player_id"]),
        name=str(row["name"]),
        bucket=int(row["bucket"]),
        sg_off_tee=f("sg_off_tee"),
        sg_approach=f("sg_approach"),
        sg_arg=f("sg_arg"),
        sg_putting=f("sg_putting"),
        driving_distance=f("driving_distance"),
        driving_accuracy=f("driving_accuracy"),
        gir=f("gir"),
        scrambling=f("scrambling"),
        par5_scoring=f("par5_scoring"),
        bogey_avoidance=f("bogey_avoidance"),
        double_bogey_rate=f("double_bogey_rate"),
        cut_rate=f("cut_rate"),
        masters_history=f("masters_history"),
        augusta_correlated=f("augusta_correlated"),
        majors_perf=f("majors_perf"),
        field_adjusted_finish=f("field_adjusted_finish"),
        odds_win=f("odds_win"),
        odds_top5=f("odds_top5"),
        odds_top10=f("odds_top10"),
        recent_finishes=recent,
    )


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _lognormal(rng: random.Random, mean: float, sigma: float) -> float:
    return rng.lognormvariate(mean, sigma)
