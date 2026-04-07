from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from .schemas import PlayerFeatures, PlayerProjection


def per_bucket_rankings(projections: Dict[str, PlayerProjection]) -> Dict[int, List[dict]]:
    by_bucket = defaultdict(list)
    for p in projections.values():
        upside = p.p_top10 * 0.7 + p.p_win * 0.3
        safety = p.p_make_cut * 0.7 + (1.0 / p.exp_round_score) * 20.0 * 0.3
        by_bucket[p.bucket].append(
            {
                "player_id": p.player_id,
                "name": p.name,
                "exp_round_score": p.exp_round_score,
                "p_make_cut": p.p_make_cut,
                "p_top20": p.p_top20,
                "p_top10": p.p_top10,
                "p_win": p.p_win,
                "safe_score": safety,
                "upside_score": upside,
            }
        )
    for b in by_bucket:
        by_bucket[b].sort(key=lambda x: x["exp_round_score"])
    return dict(by_bucket)


def player_diagnostics(features: List[PlayerFeatures], projections: Dict[str, PlayerProjection]) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for feat in features:
        proj = projections[feat.player_id]
        components = {
            "cut_making_probability": 0.40 * proj.p_make_cut,
            "top20_probability": 0.65 * proj.p_top20,
            "top10_probability": 0.95 * proj.p_top10,
            "win_probability": 1.15 * proj.p_win,
            "recent_form": 0.50 * max(feat.weighted_form, 0.0) / 100.0,
            "course_history": 0.45 * max(feat.cut_survival, 0.0),
            "course_fit": 0.55 * max(feat.augusta_fit, 0.0) / 10.0,
            "volatility": -0.30 * feat.volatility,
            "projected_best8_contribution": 0.90 * max(72.0 - proj.exp_round_score, 0.0),
        }

        pos_total = sum(max(v, 0.0) for v in components.values())
        importance = {
            k: (max(v, 0.0) / pos_total if pos_total else 0.0)
            for k, v in components.items()
        }

        out[feat.player_id] = {
            "name": feat.name,
            "bucket": feat.bucket,
            "raw_component_scores": components,
            "relative_importance": importance,
            "safety_vs_ceiling_signal": {
                "safety": proj.p_make_cut,
                "ceiling": proj.p_top10 * 0.7 + proj.p_win * 0.3,
            },
        }
    return out
