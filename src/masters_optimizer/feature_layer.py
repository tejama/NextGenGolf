from __future__ import annotations

from statistics import mean, pstdev
from typing import Dict, List

from .schemas import PlayerFeatures, PlayerRecord


def build_features(players: List[PlayerRecord], weights: Dict[str, float]) -> List[PlayerFeatures]:
    norm = _normalized(players)
    rows: List[PlayerFeatures] = []
    recent_weight = [0.32, 0.22, 0.16, 0.11, 0.08, 0.05, 0.04, 0.02]

    for p in players:
        z = norm[p.player_id]
        recent = p.recent_finishes[: len(recent_weight)] or [40.0]
        w = recent_weight[: len(recent)]
        wsum = sum(w)
        weighted_finish = sum(x * ww for x, ww in zip(recent, w)) / wsum
        weighted_form = -weighted_finish

        baseline_skill = (
            z["sg_off_tee"] * 0.16
            + z["sg_approach"] * 0.33
            + z["sg_arg"] * 0.10
            + z["sg_putting"] * 0.14
            + z["driving_distance"] * 0.05
            + z["driving_accuracy"] * 0.06
            + z["gir"] * 0.08
            + z["bogey_avoidance"] * 0.05
            - z["double_bogey_rate"] * 0.04
            - z["par5_scoring"] * 0.05
            + z["field_adjusted_finish"] * 0.12
        )
        augusta_fit = (
            z["sg_approach"] * 0.40
            + z["sg_arg"] * 0.18
            + z["sg_putting"] * 0.16
            + z["scrambling"] * 0.12
            + z["masters_history"] * 0.08
            + z["augusta_correlated"] * 0.12
        )
        vol = pstdev(recent) / 20.0 + max(0.0, z["double_bogey_rate"])
        cut = _clip(0.52 + 0.28 * z["cut_rate"] - 0.12 * z["double_bogey_rate"], 0.03, 0.995)
        contention = _clip(0.55 * z["odds_top10"] + 0.35 * z["odds_top5"] + 0.1 * z["odds_win"], 0.01, 0.85)
        birdie_upside = (
            -z["par5_scoring"] * 0.45
            + z["driving_distance"] * 0.18
            + z["sg_approach"] * 0.22
            - z["double_bogey_rate"] * 0.10
            + z["field_adjusted_finish"] * 0.15
        )
        approach_plus_form = z["sg_approach"] * 0.72 + weighted_form / 55.0
        rows.append(
            PlayerFeatures(
                player_id=p.player_id,
                name=p.name,
                bucket=p.bucket,
                weighted_form=weighted_form * weights.get("recent_form", 1.0),
                baseline_skill=baseline_skill * weights.get("baseline_skill", 1.0),
                augusta_fit=augusta_fit * weights.get("augusta_fit", 1.0),
                volatility=vol * weights.get("volatility", 1.0),
                cut_survival=cut,
                contention_prob=contention,
                birdie_upside=birdie_upside,
                approach_plus_form=approach_plus_form,
            )
        )
    return rows


def _normalized(players: List[PlayerRecord]) -> Dict[str, Dict[str, float]]:
    fields = [
        "sg_off_tee", "sg_approach", "sg_arg", "sg_putting", "driving_distance", "driving_accuracy", "gir",
        "scrambling", "par5_scoring", "bogey_avoidance", "double_bogey_rate", "cut_rate", "masters_history",
        "augusta_correlated", "majors_perf", "field_adjusted_finish", "odds_win", "odds_top5", "odds_top10",
    ]
    stats = {}
    for f in fields:
        vals = [getattr(p, f) for p in players]
        m = mean(vals)
        sd = pstdev(vals) or 1.0
        stats[f] = (m, sd)

    out = {}
    for p in players:
        out[p.player_id] = {f: (getattr(p, f) - stats[f][0]) / stats[f][1] for f in fields}
    return out


def _clip(x, lo, hi):
    return max(lo, min(hi, x))
