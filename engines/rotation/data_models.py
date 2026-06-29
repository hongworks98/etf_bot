"""
engines/rotation/data_models.py
RotationSignalEngine — Data Models (Step 5)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


# ─────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────

class RotationStage(str, Enum):
    EMERGING  = "Emerging"
    BUILDING  = "Building"
    CONFIRMED = "Confirmed"
    MATURE    = "Mature"
    WEAKENING = "Weakening"
    REVERSING = "Reversing"


class RotationStrength(str, Enum):
    WEAK     = "Weak"
    MODERATE = "Moderate"
    STRONG   = "Strong"
    EXTREME  = "Extreme"


class RotationTiming(str, Enum):
    NOW        = "NOW"
    THIS_WEEK  = "THIS_WEEK"
    THIS_MONTH = "THIS_MONTH"
    WAIT       = "WAIT"


class RotationSpeedLevel(str, Enum):
    SLOW     = "Slow"
    MODERATE = "Moderate"
    FAST     = "Fast"
    RAPID    = "Rapid"


class ConvictionLevel(str, Enum):
    IMMEDIATE_ROTATION = "Immediate Rotation"
    GRADUAL_ROTATION   = "Gradual Rotation"
    WATCHLIST          = "Watchlist"
    OBSERVE            = "Observe"
    NO_ROTATION        = "No Rotation"


# ─────────────────────────────────────────────
# Input Models
# ─────────────────────────────────────────────

@dataclass
class AuxMarketData:
    """Optional auxiliary market data (VIX, DXY, Yields, Commodities, Fund Flows)."""
    vix:          List[float] = field(default_factory=list)
    dollar_index: List[float] = field(default_factory=list)
    treasury_10y: List[float] = field(default_factory=list)
    oil:          List[float] = field(default_factory=list)
    gold:         List[float] = field(default_factory=list)
    copper:       List[float] = field(default_factory=list)
    etf_flows:    Dict[str, List[float]] = field(default_factory=dict)

    def latest_vix(self) -> float:
        return self.vix[-1] if self.vix else 20.0

    def vix_trend(self, period: int = 10) -> float:
        if len(self.vix) < period + 1:
            return 0.0
        return self.vix[-1] - self.vix[-period - 1]

    def etf_flow_trend(self, ticker: str, period: int = 10) -> float:
        flows = self.etf_flows.get(ticker, [])
        if len(flows) < period:
            return 0.0
        recent = flows[-period:]
        return sum(recent) / len(recent)


@dataclass
class TrendInputData:
    """Lightweight trend data per ETF."""
    ticker: str
    trend_score: float = 50.0
    trend_direction: str = "FLAT"
    momentum: float = 0.0
    above_200ma: bool = True
    slope_quality: float = 50.0


@dataclass
class RotationInput:
    """Complete input to RotationSignalEngine. Accepts outputs from all preceding engines."""
    spy: object
    sectors: Dict[str, object] = field(default_factory=dict)
    sector_volumes: Dict[str, List[float]] = field(default_factory=dict)

    # Analysis Layer engine outputs (read-only)
    breadth_score: float = 50.0
    breadth_health: str = "Healthy"
    breadth_trend: str = "FLAT"
    rs_results: Dict[str, object] = field(default_factory=dict)
    trend_data: Dict[str, TrendInputData] = field(default_factory=dict)

    # Macro
    macro_state: str = "Unknown"
    macro_score: float = 50.0
    macro_direction: str = "FLAT"

    # Market Health
    market_health_score: float = 50.0

    # Auxiliary
    aux_data: AuxMarketData = field(default_factory=AuxMarketData)

    # Portfolio
    current_holdings: Dict[str, float] = field(default_factory=dict)
    portfolio_value: float = 1_000_000.0

    # History
    previous_rotation_scores: Dict[str, List[float]] = field(default_factory=dict)
    previous_rotation_state: Dict[str, str] = field(default_factory=dict)

    # Costs
    transaction_cost_pct: float = 0.001

    def get_rs_score(self, ticker: str) -> float:
        rs = self.rs_results.get(ticker)
        if rs is None:
            return 50.0
        return getattr(rs, "rs_score", 50.0)

    def get_rs_rank_change(self, ticker: str) -> int:
        rs = self.rs_results.get(ticker)
        if rs is None:
            return 0
        rank = getattr(rs, "rank", None)
        if rank is None:
            return 0
        return getattr(rank, "rank_change", 0)

    def get_rs_acceleration(self, ticker: str) -> float:
        rs = self.rs_results.get(ticker)
        if rs is None:
            return 0.0
        trend = getattr(rs, "trend", None)
        if trend is None:
            return 0.0
        return getattr(trend, "acceleration", 0.0)

    def get_persistence_score(self, ticker: str) -> float:
        rs = self.rs_results.get(ticker)
        if rs is None:
            return 50.0
        return getattr(rs, "persistence_score", 50.0)


# ─────────────────────────────────────────────
# Intermediate Models
# ─────────────────────────────────────────────

@dataclass
class RotationAttribution:
    factor: str
    score_contribution: float
    pct_contribution: float
    direction: str
    interpretation: str


@dataclass
class RotationDirection:
    from_sector: str
    to_sector: str
    strength: RotationStrength
    confidence: float
    rotation_score_from: float
    rotation_score_to: float
    description: str


@dataclass
class CostAnalysis:
    from_ticker: str
    to_ticker: str
    transaction_cost: float
    slippage_est: float
    tax_impact: float
    total_cost_pct: float
    net_benefit: float
    breakeven_days: int
    is_worth_rotating: bool


@dataclass
class DashboardData:
    rotation_heatmap:  List[Dict] = field(default_factory=list)
    sector_flow_map:   List[Dict] = field(default_factory=list)
    rotation_network:  List[Dict] = field(default_factory=list)
    capital_flow_map:  List[Dict] = field(default_factory=list)
    rotation_timeline: List[Dict] = field(default_factory=list)
    attribution_chart: List[Dict] = field(default_factory=list)


# ─────────────────────────────────────────────
# Main Per-ETF Result
# ─────────────────────────────────────────────

@dataclass
class RotationResult:
    ticker: str
    rotation_score: float = 50.0
    stage: RotationStage = RotationStage.BUILDING
    strength: RotationStrength = RotationStrength.MODERATE
    timing: RotationTiming = RotationTiming.WAIT
    speed: float = 50.0
    speed_level: RotationSpeedLevel = RotationSpeedLevel.MODERATE
    persistence_days: int = 0
    persistence_weeks: int = 0
    confidence: float = 50.0
    forecast: float = 50.0
    opportunity_score: float = 50.0
    capital_flow_score: float = 50.0
    conviction_score: float = 50.0
    conviction_level: ConvictionLevel = ConvictionLevel.OBSERVE
    stability: float = 50.0
    rotation_risk: float = 50.0
    is_false_rotation: bool = False
    false_rotation_reason: str = ""
    attribution: List[RotationAttribution] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    why_now: str = ""
    why_this_etf: str = ""
    xai_summary: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def is_actionable(self) -> bool:
        return (
            not self.is_false_rotation and
            self.conviction_level in {
                ConvictionLevel.IMMEDIATE_ROTATION,
                ConvictionLevel.GRADUAL_ROTATION,
                ConvictionLevel.WATCHLIST,
            }
        )

    @property
    def top_attribution_factors(self) -> List[str]:
        top = sorted(self.attribution, key=lambda a: a.pct_contribution, reverse=True)
        return [a.factor for a in top[:3]]

    def summary(self) -> str:
        flag = " | FALSE_ROTATION" if self.is_false_rotation else ""
        return (
            f"[{self.ticker}] Score={self.rotation_score:.1f}"
            f" | {self.stage.value} | {self.strength.value}"
            f" | Conviction={self.conviction_score:.1f}({self.conviction_level.value})"
            f" | Timing={self.timing.value}{flag}"
        )


# ─────────────────────────────────────────────
# Engine-Level Result
# ─────────────────────────────────────────────

@dataclass
class RotationEngineResult:
    sector_results: Dict[str, RotationResult] = field(default_factory=dict)
    rotation_directions: List[RotationDirection] = field(default_factory=list)
    top_opportunities: List[str] = field(default_factory=list)
    conviction_rankings: List[str] = field(default_factory=list)
    dashboard_data: DashboardData = field(default_factory=DashboardData)
    cost_analysis: Dict[str, CostAnalysis] = field(default_factory=dict)
    market_rotation_active: bool = False
    dominant_rotation: Optional[RotationDirection] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def get(self, ticker: str) -> Optional[RotationResult]:
        return self.sector_results.get(ticker)

    def actionable(self) -> List[RotationResult]:
        return [r for r in self.sector_results.values() if r.is_actionable]

    def immediate_rotations(self) -> List[RotationResult]:
        return [r for r in self.sector_results.values()
                if r.conviction_level == ConvictionLevel.IMMEDIATE_ROTATION]


# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

@dataclass
class RotationConfig:
    rs_weight:      float = 0.28
    macro_weight:   float = 0.22
    breadth_weight: float = 0.18
    flow_weight:    float = 0.15
    trend_weight:   float = 0.10
    risk_weight:    float = 0.07
    rs_momentum_lo: float = -10.0
    rs_momentum_hi: float =  10.0
    breadth_scale:  float = 2.0
    below_200ma_penalty: float = 0.60
    macro_expected_and_strong:   float = 100.0
    macro_expected_and_neutral:  float = 65.0
    macro_unexpected_strong:     float = 25.0
    macro_unexpected_neutral:    float = 45.0
    macro_unknown:               float = 50.0
    macro_expected_leaders: Dict[str, List[str]] = field(default_factory=lambda: {
        "Recovery":      ["XLF", "XLY", "XLI", "XLK"],
        "Expansion":     ["XLK", "XLC", "XLY", "XLF"],
        "Overheating":   ["XLE", "XLB", "XLI", "XLF"],
        "Slowdown":      ["XLP", "XLU", "XLV", "XLB"],
        "Recession":     ["XLU", "XLP", "XLV"],
        "EarlyRecovery": ["XLF", "XLK", "XLY"],
        "Unknown":       [],
    })
    mfi_period: int = 14
    vol_window_short: int = 10
    vol_window_long:  int = 60
    mfi_lo: float = 20.0
    mfi_hi: float = 80.0
    vol_ratio_lo: float = 0.50
    vol_ratio_hi: float = 2.00
    flow_weights: Dict[str, float] = field(default_factory=lambda: {
        "mfi": 0.35, "volume": 0.35, "etf_flow": 0.30
    })
    emerging_max_score:  float = 45.0
    emerging_max_days:   int   = 5
    building_max_score:  float = 62.0
    building_max_days:   int   = 15
    confirmed_min_score: float = 62.0
    confirmed_min_days:  int   = 15
    mature_min_score:    float = 75.0
    weakening_drop:      float = 8.0
    reversing_threshold: float = 30.0
    lifecycle_bonus: Dict[str, float] = field(default_factory=lambda: {
        "Confirmed": 80.0, "Mature": 70.0, "Building": 60.0,
        "Emerging": 40.0, "Weakening": 30.0, "Reversing": 10.0,
    })
    conviction_weights: Dict[str, float] = field(default_factory=lambda: {
        "rotation_score": 0.30, "confidence": 0.25,
        "lifecycle": 0.20, "opportunity": 0.15, "timing": 0.10,
    })
    immediate_threshold: float = 90.0
    gradual_threshold:   float = 75.0
    watchlist_threshold: float = 60.0
    observe_threshold:   float = 40.0
    timing_scores: Dict[str, float] = field(default_factory=lambda: {
        "NOW": 100.0, "THIS_WEEK": 70.0, "THIS_MONTH": 50.0, "WAIT": 20.0,
    })
    opp_weights: Dict[str, float] = field(default_factory=lambda: {
        "rs_gap": 0.40, "conviction_gap": 0.30,
        "persistence_gap": 0.20, "cost_adj": 0.10,
    })
    min_rs_gap_to_act: float = 15.0
    spike_sigma: float = 2.0
    spike_window_days: int = 30
    spike_change_days: int = 3
    volume_spike_ratio: float = 3.0
    volume_follow_days: int = 3
    min_persistence_days: int = 3
    now_min_conviction: float = 75.0
    this_week_min_conviction: float = 60.0
    this_month_min_forecast: float = 60.0
    wait_threshold: float = 60.0
    risk_weights: Dict[str, float] = field(default_factory=lambda: {
        "vix_risk": 0.30, "breadth_divergence": 0.25,
        "macro_misalign": 0.20, "speed_risk": 0.15, "stage_risk": 0.10,
    })
    vix_high: float = 30.0
    vix_extreme: float = 40.0
    vix_lo: float = 10.0
    vix_hi: float = 50.0
    breadth_div_threshold: float = 15.0
    extreme_threshold:  float = 85.0
    strong_threshold:   float = 65.0
    moderate_threshold: float = 45.0
    rapid_speed:    float = 80.0
    fast_speed:     float = 60.0
    moderate_speed: float = 40.0
    speed_lookback: int = 7
    into_threshold: float = 65.0
    out_threshold:  float = 35.0
    min_dir_confidence: float = 0.60
    persistence_score_threshold: float = 50.0
    confidence_weights: Dict[str, float] = field(default_factory=lambda: {
        "rs_aligned": 0.25, "macro_aligned": 0.25,
        "breadth_aligned": 0.20, "trend_aligned": 0.15, "flow_aligned": 0.15,
    })
    default_spread_pct: float = 0.001
    slippage_pct:       float = 0.0005
    tax_rate:           float = 0.154
    daily_alpha_est:    float = 0.0003
    forecast_weights: Dict[str, float] = field(default_factory=lambda: {
        "rs_acceleration": 0.30, "macro_cycle_phase": 0.25,
        "breadth_trend": 0.20, "capital_momentum": 0.15, "vix_trend": 0.10,
    })
    heatmap_colors: Dict[str, str] = field(default_factory=lambda: {
        "extreme": "#8B0000", "strong": "#E74C3C",
        "moderate": "#F39C12", "weak": "#27AE60", "none": "#2ECC71",
    })
    flow_colors: Dict[str, str] = field(default_factory=lambda: {
        "inflow": "#1A7C4E", "outflow": "#C0392B", "neutral": "#7F8C8D",
    })

    @classmethod
    def from_dict(cls, d: dict) -> "RotationConfig":
        cfg = cls()
        if "rotation_score_weights" in d:
            w = d["rotation_score_weights"]
            cfg.rs_weight      = w.get("rs_momentum",    cfg.rs_weight)
            cfg.macro_weight   = w.get("macro_align",    cfg.macro_weight)
            cfg.breadth_weight = w.get("breadth_supp",   cfg.breadth_weight)
            cfg.flow_weight    = w.get("capital_flow",   cfg.flow_weight)
            cfg.trend_weight   = w.get("trend_strength", cfg.trend_weight)
            cfg.risk_weight    = w.get("risk_inverse",   cfg.risk_weight)
        if "lifecycle" in d:
            lc = d["lifecycle"]
            cfg.emerging_max_score  = lc.get("emerging_max_score",   cfg.emerging_max_score)
            cfg.emerging_max_days   = lc.get("emerging_max_days",    cfg.emerging_max_days)
            cfg.building_max_score  = lc.get("building_max_score",   cfg.building_max_score)
            cfg.building_max_days   = lc.get("building_max_days",    cfg.building_max_days)
            cfg.confirmed_min_score = lc.get("confirmed_min_score",  cfg.confirmed_min_score)
            cfg.confirmed_min_days  = lc.get("confirmed_min_days",   cfg.confirmed_min_days)
            cfg.mature_min_score    = lc.get("mature_min_score",     cfg.mature_min_score)
            cfg.weakening_drop      = lc.get("weakening_drop",       cfg.weakening_drop)
            cfg.reversing_threshold = lc.get("reversing_threshold",  cfg.reversing_threshold)
        if "conviction" in d:
            cv = d["conviction"]
            cfg.conviction_weights  = cv.get("weights", cfg.conviction_weights)
            cfg.immediate_threshold = cv.get("immediate_threshold", cfg.immediate_threshold)
            cfg.gradual_threshold   = cv.get("gradual_threshold",   cfg.gradual_threshold)
            cfg.watchlist_threshold = cv.get("watchlist_threshold", cfg.watchlist_threshold)
            cfg.observe_threshold   = cv.get("observe_threshold",   cfg.observe_threshold)
            cfg.timing_scores       = cv.get("timing_scores",       cfg.timing_scores)
        if "false_rotation" in d:
            fr = d["false_rotation"]
            cfg.spike_sigma          = fr.get("spike_sigma",          cfg.spike_sigma)
            cfg.spike_window_days    = fr.get("spike_window_days",    cfg.spike_window_days)
            cfg.spike_change_days    = fr.get("spike_change_days",    cfg.spike_change_days)
            cfg.volume_spike_ratio   = fr.get("volume_spike_ratio",   cfg.volume_spike_ratio)
            cfg.min_persistence_days = fr.get("min_persistence_days", cfg.min_persistence_days)
        if "rotation_risk" in d:
            rr = d["rotation_risk"]
            cfg.risk_weights          = rr.get("weights", cfg.risk_weights)
            cfg.vix_high              = rr.get("vix_high_threshold",    cfg.vix_high)
            cfg.vix_extreme           = rr.get("vix_extreme_threshold", cfg.vix_extreme)
        if "rotation_direction" in d:
            rd = d["rotation_direction"]
            cfg.into_threshold = rd.get("into_threshold", cfg.into_threshold)
            cfg.out_threshold  = rd.get("out_threshold",  cfg.out_threshold)
        return cfg
