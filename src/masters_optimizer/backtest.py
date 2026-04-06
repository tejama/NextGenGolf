from __future__ import annotations

from pathlib import Path
from statistics import mean
from typing import Dict, List

from .pipeline import run_pipeline


def run_backtest(config: Dict) -> Dict[str, float]:
    snapshots: List[Dict] = config.get("backtest", {}).get("snapshots", []) or [config]

    lineup_avgs = []
    brier_cut = []

    for i, snapshot in enumerate(snapshots):
        output_dir = Path("output") / f"backtest_{i}"
        results = run_pipeline(snapshot, output_dir)
        ev = results["ev"]
        lineup_avgs.append(mean(x.expected_score for x in ev))

        target_cut = snapshot.get("backtest", {}).get("target_cut_rate", 0.27)
        pred_cut = mean(1.0 - x.cut_survival_avg for x in ev)
        brier_cut.append((pred_cut - target_cut) ** 2)

    return {
        "avg_expected_lineup_score": mean(lineup_avgs),
        "cut_calibration_brier": mean(brier_cut),
        "num_snapshots": float(len(snapshots)),
    }
