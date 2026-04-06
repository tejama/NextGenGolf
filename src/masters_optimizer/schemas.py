from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class PlayerRecord:
    player_id: str
    name: str
    bucket: int
    sg_off_tee: float
    sg_approach: float
    sg_arg: float
    sg_putting: float
    driving_distance: float
    driving_accuracy: float
    gir: float
    scrambling: float
    par5_scoring: float
    bogey_avoidance: float
    double_bogey_rate: float
    cut_rate: float
    masters_history: float
    augusta_correlated: float
    majors_perf: float
    field_adjusted_finish: float
    odds_win: float
    odds_top5: float
    odds_top10: float
    recent_finishes: List[float]


@dataclass(frozen=True)
class PlayerFeatures:
    player_id: str
    name: str
    bucket: int
    weighted_form: float
    baseline_skill: float
    augusta_fit: float
    volatility: float
    cut_survival: float
    contention_prob: float


@dataclass(frozen=True)
class PlayerProjection:
    player_id: str
    name: str
    bucket: int
    exp_round_score: float
    round_std: float
    p_make_cut: float
    p_top20: float
    p_top10: float
    p_win: float
    win_equity: float


@dataclass
class LineupResult:
    players: List[str]
    player_names: List[str]
    expected_score: float
    floor: float
    ceiling: float
    volatility: float
    best8_expected: float
    cut_survival_avg: float
    win_equity_sum: float
    overlap_pct: float = 0.0
    rationale: str = ""


@dataclass
class PipelineArtifacts:
    projections: Dict[str, PlayerProjection]
    simulation_scores: Dict[str, List[float]]
    missed_cut_rates: Dict[str, float]
