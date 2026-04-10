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

        p_cut_prior = _clip(0.50 + 0.26 * f.cut_survival, 0.05, 0.99)
        p_cut_like = _clip(0.43 + 0.22 * (f.baseline_skill / 10.0) + 0.15 * f.cut_survival, 0.02, 0.99)
        p_make_cut = _clip(0.50 * p_cut_prior + 0.50 * p_cut_like, 0.03, 0.995)

        ceiling_signal = (
            f.contention_prob * 0.50
            + max(0.0, (72.1 - exp_round)) * 0.07
            + max(0.0, f.birdie_upside) * 0.08
            + max(0.0, f.approach_plus_form) * 0.08
            + max(0.0, f.volatility) * 0.06
        )
        p_top20 = _clip(0.30 + ceiling_signal * 0.55 + p_make_cut * 0.12, 0.02, 0.95)
        p_top10 = _clip(0.08 + ceiling_signal * 0.45 + f.contention_prob * 0.20, 0.01, 0.85)
        p_top5 = _clip(p_top10 * 0.55 + f.contention_prob * 0.12 + max(0.0, f.birdie_upside) * 0.03, 0.005, 0.65)
        p_win = _clip(p_top5 * 0.30 + f.contention_prob * 0.04 + max(0.0, f.approach_plus_form) * 0.02, 0.001, 0.28)
        birdie_burst = _clip(0.14 + max(0.0, f.birdie_upside) * 0.18 + max(0.0, f.volatility) * 0.07, 0.01, 0.92)
        archetype = _classify_archetype(p_make_cut=p_make_cut, p_top10=p_top10, p_top5=p_top5, p_win=p_win, volatility=f.volatility)

        out[f.player_id] = PlayerProjection(
            player_id=f.player_id,
            name=f.name,
            bucket=f.bucket,
            exp_round_score=exp_round,
            round_std=round_std,
            p_make_cut=p_make_cut,
            p_top20=p_top20,
            p_top5=p_top5,
            p_top10=p_top10,
            p_win=p_win,
            win_equity=p_win,
            birdie_burst=birdie_burst,
            archetype=archetype,
        )
    return out


def _clip(x, lo, hi):
    return max(lo, min(hi, x))


def _classify_archetype(p_make_cut: float, p_top10: float, p_top5: float, p_win: float, volatility: float) -> str:
    if p_win >= 0.045 or p_top5 >= 0.22:
        return "elite_contender"
    if (volatility >= 0.11 and p_top10 >= 0.16) or p_win >= 0.025:
        return "high_ceiling_volatile"
    if p_make_cut >= 0.70 and p_top10 >= 0.12:
        return "balanced_contributor"
    return "low_ceiling_safety"
