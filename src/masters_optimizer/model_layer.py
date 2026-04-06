from __future__ import annotations

from typing import Dict, List

from .schemas import PlayerFeatures, PlayerProjection


def project_players(features: List[PlayerFeatures], priors: Dict[str, float]) -> Dict[str, PlayerProjection]:
    out = {}
    for f in features:
        baseline = 72.1 - (f.baseline_skill * 1.1 + f.augusta_fit * 0.7)
        recent_adj = priors.get("recent_weight", 0.45) * (-f.weighted_form / 80.0)
        skill_adj = priors.get("long_term_weight", 0.55) * (f.baseline_skill / 30.0)
        exp_round = _clip(baseline - recent_adj - skill_adj, 66.5, 76.5)
        round_std = _clip(1.8 + f.volatility * 2.7, 1.7, 5.4)

        p_cut_prior = _clip(0.52 + 0.34 * f.cut_survival, 0.05, 0.99)
        p_cut_like = _clip(0.45 + 0.25 * (f.baseline_skill / 10.0) + 0.2 * f.cut_survival, 0.02, 0.99)
        p_make_cut = _clip(0.58 * p_cut_prior + 0.42 * p_cut_like, 0.03, 0.995)

        contention = _clip(f.contention_prob + max(0.0, (72.0 - exp_round) * 0.03), 0.01, 0.95)
        p_top20 = _clip(contention * 1.4, 0.02, 0.95)
        p_top10 = _clip(contention * 0.9, 0.01, 0.85)
        p_win = _clip(p_top10 * 0.18, 0.001, 0.28)

        out[f.player_id] = PlayerProjection(
            player_id=f.player_id,
            name=f.name,
            bucket=f.bucket,
            exp_round_score=exp_round,
            round_std=round_std,
            p_make_cut=p_make_cut,
            p_top20=p_top20,
            p_top10=p_top10,
            p_win=p_win,
            win_equity=p_win,
        )
    return out


def _clip(x, lo, hi):
    return max(lo, min(hi, x))
