from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from .schemas import PlayerProjection


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
                "p_top10": p.p_top10,
                "p_win": p.p_win,
                "safe_score": safety,
                "upside_score": upside,
            }
        )
    for b in by_bucket:
        by_bucket[b].sort(key=lambda x: x["exp_round_score"])
    return dict(by_bucket)
