"""
engines/relative_strength/data_models.py
RelativeStrengthEngine Data Models
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional


# ─────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────

class LeaderStatus(str, Enum):
    LEADER   = "Leader"
    FOLLOWER = "Follower"
    LAGGARD  = "Laggard"


class RSTrendDir(str, Enum):
    RISING  = "Rising"
    FLAT    = "Flat"
    FALLING = "Falling"


# ─────────────────────────────────────────────
# Input Models
# ─────────────────────────────────────────────

@dataclass
class PriceHistory:
    """Single ETF / index daily price-volume history."""
    ticker: str
    prices: List[float] = field(default_factory=list)    # close prices, oldest first
    volumes: List[float] = field(default_factory=list)   # daily volume, same order
    dates: List[date]   = field(default_factory=list)

    # ── helpers ────────────────────────────────

    def _period_to_days(self, period: str) -> int:
        mapping = {"1M": 21, "3M": 63, "6M": 126, "12M": 252}
        return mapping.get(period, 21)

    def total_return(self, period: str = "3M") -> float:
        """Return (%) over period. Returns 0.0 if insufficient data."""
        n = self._period_to_days(period)
        if len(self.prices) < n + 1:
            n = len(self.prices) - 1
        if n <= 0 or self.prices[-(n + 1)] == 0:
            return 0.0
        return (self.prices[-1] / self.prices[-(n + 1)] - 1.0) * 100.0

    def rolling_returns(self, window: int = 5) -> List[float]:
        """Weekly (5-day) rolling return series."""
        rets: List[float] = []
        for i in range(window, len(self.prices)):
            base = self.prices[i - window]
            if base != 0:
                rets.append((self.prices[i] / base - 1.0) * 100.0)
            else:
                rets.append(0.0)
        return rets

    def daily_returns(self) -> List[float]:
        """Day-over-day return series."""
        rets: List[float] = []
        for i in range(1, len(self.prices)):
            base = self.prices[i - 1]
            rets.append((self.prices[i] / base - 1.0) * 100.0 if base != 0 else 0.0)
        return rets

    def volatility(self, period: int = 63) -> float:
        """Annualised daily return std over last `period` days."""
        rets = self.daily_returns()[-period:]
        if len(rets) < 5:
            return 0.0
        mean = sum(rets) / len(rets)
        var = sum((r - mean) ** 2 for r in rets) / len(rets)
        return math.sqrt(var) * math.sqrt(252)


@dataclass
class RSInput:
    """Full input to RelativeStrengthEngine."""
    spy: PriceHistory
    sectors: Dict[str, PriceHistory] = field(default_factory=dict)
    breadth_score: float = 50.0
    macro_state: str = "Unknown"
    macro_direction: str = "FLAT"
    previous_rankings: Dict[str, int] = field(default_factory=dict)  # {ticker: rank}


# ─────────────────────────────────────────────
# Intermediate / Component Models
# ─────────────────────────────────────────────

@dataclass
class RSTimeframe:
    """Per-timeframe RS result."""
    period: str             # "1M", "3M", "6M", "12M"
    etf_return: float       # raw return (%)
    spy_return: float       # raw return (%)
    relative_return: float  # etf_return - spy_return
    rs_score: float         # 0~100 normalised


@dataclass
class RSTrend:
    """RS momentum trend analysis."""
    direction: RSTrendDir
    slope: float        # composite slope (units per day)
    acceleration: float # slope change (slope_1m - slope_3m)
    trend_score: float  # 0~100
    slope_1m: float = 0.0
    slope_3m: float = 0.0


@dataclass
class RSRankInfo:
    """Sector rank position and movement."""
    current_rank: int
    previous_rank: int
    rank_change: int       # previous - current  (positive = improved)
    rank_jump: bool        # |rank_change| >= threshold
    total_sectors: int
    percentile: float      # 0~100, higher = stronger (top rank → ~100)


@dataclass
class RSQuality:
    """Quality metrics for the RS signal."""
    consistency: float    # 0~100, inverse of spread across TF scores
    volatility: float     # 0~100, ETF lower-vol vs SPY → higher
    participation: float  # 0~100, volume participation on up-days
    persistence: float    # 0~100 (from PersistenceCalculator output)
    quality_score: float  # 0~100 weighted composite


@dataclass
class MacroValidation:
    """Does current leadership align with the macro regime?"""
    is_aligned: bool
    alignment_score: float          # 0~100
    expected_leaders: List[str]     # tickers expected to lead in this macro
    actual_position: str            # "Leading" / "Neutral" / "Lagging"
    description: str
    warning: Optional[str] = None


# ─────────────────────────────────────────────
# Explainable AI — Contribution
# ─────────────────────────────────────────────

@dataclass
class RSContribution:
    """Single factor contribution to final RS score (XAI)."""
    factor: str
    raw_value: float
    weight: float
    contribution: float   # weight * normalized_value
    direction: str        # "↑" / "↓" / "→"
    interpretation: str   # human-readable


# ─────────────────────────────────────────────
# Main Per-ETF Result
# ─────────────────────────────────────────────

@dataclass
class RelativeStrengthResult:
    """Full RS analysis result for one sector ETF."""
    ticker: str
    rs_score: float                          # 0~100  → feeds AnalysisResult.rs_score
    timeframes: List[RSTimeframe] = field(default_factory=list)
    trend: RSTrend = field(default_factory=lambda: RSTrend(
        direction=RSTrendDir.FLAT, slope=0.0, acceleration=0.0,
        trend_score=50.0
    ))
    rank: RSRankInfo = field(default_factory=lambda: RSRankInfo(
        current_rank=1, previous_rank=1, rank_change=0,
        rank_jump=False, total_sectors=1, percentile=50.0
    ))
    leader_status: LeaderStatus = LeaderStatus.FOLLOWER
    persistence_score: float = 50.0
    quality: RSQuality = field(default_factory=lambda: RSQuality(
        consistency=50.0, volatility=50.0,
        participation=50.0, persistence=50.0, quality_score=50.0
    ))
    rotation_readiness: float = 50.0
    macro_validation: MacroValidation = field(default_factory=lambda: MacroValidation(
        is_aligned=False, alignment_score=50.0, expected_leaders=[],
        actual_position="Neutral", description="No macro context"
    ))
    contributions: List[RSContribution] = field(default_factory=list)
    confidence: float = 0.5
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    # ── convenience properties ──────────────────

    @property
    def is_leader(self) -> bool:
        return self.leader_status == LeaderStatus.LEADER

    @property
    def is_laggard(self) -> bool:
        return self.leader_status == LeaderStatus.LAGGARD

    @property
    def timeframe_dict(self) -> Dict[str, float]:
        """Map period → rs_score for quick lookup."""
        return {tf.period: tf.rs_score for tf in self.timeframes}

    def summary(self) -> str:
        return (
            f"[{self.ticker}] RS={self.rs_score:.1f} | "
            f"{self.leader_status.value} | Rank #{self.rank.current_rank}/{self.rank.total_sectors} "
            f"(Δ{self.rank.rank_change:+d}) | "
            f"Trend={self.trend.direction.value} | "
            f"Rotation={self.rotation_readiness:.0f}"
        )


# ─────────────────────────────────────────────
# Heatmap
# ─────────────────────────────────────────────

@dataclass
class HeatmapCell:
    """Dashboard heatmap cell data for one ETF."""
    ticker: str
    rs_score: float
    rank: int
    leader_status: str      # "Leader" / "Follower" / "Laggard"
    timeframe_scores: Dict[str, float] = field(default_factory=dict)  # {"1M": 72.0, ...}
    trend_direction: str = "Flat"
    color_hex: str = "#f39c12"
    rank_change: int = 0
    rank_jump: bool = False


@dataclass
class HeatmapData:
    """Complete heatmap payload ready for Dashboard rendering."""
    cells: List[HeatmapCell] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    def sorted_by_rank(self) -> List[HeatmapCell]:
        return sorted(self.cells, key=lambda c: c.rank)

    def leaders(self) -> List[HeatmapCell]:
        return [c for c in self.cells if c.leader_status == "Leader"]

    def laggards(self) -> List[HeatmapCell]:
        return [c for c in self.cells if c.leader_status == "Laggard"]


# ─────────────────────────────────────────────
# Engine-Level Result
# ─────────────────────────────────────────────

@dataclass
class RSEngineResult:
    """Aggregated result across all sector ETFs from RelativeStrengthEngine."""
    sector_results: Dict[str, RelativeStrengthResult] = field(default_factory=dict)
    rankings: List[str] = field(default_factory=list)      # sorted by RS rank (best first)
    leaders: List[str]  = field(default_factory=list)
    followers: List[str] = field(default_factory=list)
    laggards: List[str]  = field(default_factory=list)
    heatmap_data: HeatmapData = field(default_factory=HeatmapData)
    portfolio_rotation_signal: float = 50.0   # aggregate rotation readiness
    timestamp: datetime = field(default_factory=datetime.now)

    def get(self, ticker: str) -> Optional[RelativeStrengthResult]:
        return self.sector_results.get(ticker)

    def top_n(self, n: int = 3) -> List[RelativeStrengthResult]:
        """Top N sectors by RS score."""
        return [self.sector_results[t] for t in self.rankings[:n] if t in self.sector_results]

    def bottom_n(self, n: int = 3) -> List[RelativeStrengthResult]:
        """Bottom N sectors by RS score."""
        return [self.sector_results[t] for t in self.rankings[-n:] if t in self.sector_results]


# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

@dataclass
class RSConfig:
    """Runtime configuration, populated from rs_weights.yaml."""
    timeframe_weights: Dict[str, float] = field(default_factory=lambda: {
        "1M": 0.30, "3M": 0.30, "6M": 0.25, "12M": 0.15
    })
    tf_normalize_lo: float = -20.0
    tf_normalize_hi: float =  20.0

    # trend
    slope_window_1m: int   = 21
    slope_window_3m: int   = 63
    slope_normalize_lo: float = -2.0
    slope_normalize_hi: float =  2.0
    acceleration_weight: float = 0.30
    direction_rising_threshold: float  =  0.1
    direction_falling_threshold: float = -0.1

    # persistence
    weekly_period: int = 52
    streak_normalize_lo: float = 0.0
    streak_normalize_hi: float = 20.0
    persistence_pos_pct_weight: float = 0.60
    persistence_streak_weight:  float = 0.40

    # quality
    quality_weights: Dict[str, float] = field(default_factory=lambda: {
        "consistency": 0.30, "volatility": 0.25,
        "participation": 0.20, "persistence": 0.25
    })
    consistency_normalize_lo: float = 0.0
    consistency_normalize_hi: float = 30.0
    volatility_normalize_lo:  float = 0.50
    volatility_normalize_hi:  float = 2.00
    participation_normalize_lo: float = 0.40
    participation_normalize_hi: float = 0.70

    # rs_score final
    rs_score_weights: Dict[str, float] = field(default_factory=lambda: {
        "composite_rs": 0.50, "trend_score": 0.20,
        "persistence": 0.15, "quality_score": 0.15
    })

    # leadership
    leader_rs_threshold:  float = 65.0
    laggard_rs_threshold: float = 35.0
    leader_rank_top_pct:  float = 0.333
    laggard_rank_bot_pct: float = 0.667

    # ranking
    rank_jump_threshold: int = 3

    # rotation readiness
    rr_weights: Dict[str, float] = field(default_factory=lambda: {
        "rank_momentum": 0.35, "trend_accel": 0.30,
        "persistence_d": 0.20, "breadth_bonus": 0.15
    })
    rr_rank_mom_lo: float  = -5.0
    rr_rank_mom_hi: float  =  5.0
    rr_accel_lo:    float  = -2.0
    rr_accel_hi:    float  =  2.0
    rr_persist_lo:  float  = -10.0
    rr_persist_hi:  float  =  10.0
    breadth_sensitivity: float = 0.30

    # macro
    macro_expected_leaders: Dict[str, List[str]] = field(default_factory=lambda: {
        "Recovery":      ["XLF", "XLY", "XLI", "XLK"],
        "Expansion":     ["XLK", "XLC", "XLY", "XLF"],
        "Overheating":   ["XLE", "XLB", "XLI", "XLF"],
        "Slowdown":      ["XLP", "XLU", "XLV", "XLB"],
        "Recession":     ["XLU", "XLP", "XLV"],
        "EarlyRecovery": ["XLF", "XLK", "XLY"],
        "Unknown":       [],
    })
    macro_alignment_scores: Dict[str, float] = field(default_factory=lambda: {
        "expected_and_leading":    100.0,
        "expected_not_leading":     50.0,
        "unexpected_leading":       30.0,
        "unexpected_not_leading":   60.0,
    })

    # heatmap
    heatmap_colors: Dict[str, str] = field(default_factory=lambda: {
        "excellent": "#1a7c4e",
        "strong":    "#2ecc71",
        "neutral":   "#f39c12",
        "weak":      "#e74c3c",
        "critical":  "#8e1a0e",
    })

    # confidence
    min_history_days:  int   = 63
    full_history_days: int   = 252
    persistence_weight: float = 0.20

    @classmethod
    def from_dict(cls, d: dict) -> "RSConfig":
        cfg = cls()
        if "timeframe_weights" in d:
            cfg.timeframe_weights = d["timeframe_weights"]
        if "timeframe_normalize" in d:
            cfg.tf_normalize_lo = d["timeframe_normalize"].get("lo", cfg.tf_normalize_lo)
            cfg.tf_normalize_hi = d["timeframe_normalize"].get("hi", cfg.tf_normalize_hi)
        if "trend" in d:
            t = d["trend"]
            cfg.slope_window_1m  = t.get("slope_window_1m", cfg.slope_window_1m)
            cfg.slope_window_3m  = t.get("slope_window_3m", cfg.slope_window_3m)
            cfg.slope_normalize_lo = t.get("slope_normalize_lo", cfg.slope_normalize_lo)
            cfg.slope_normalize_hi = t.get("slope_normalize_hi", cfg.slope_normalize_hi)
            cfg.acceleration_weight = t.get("acceleration_weight", cfg.acceleration_weight)
            cfg.direction_rising_threshold  = t.get("direction_rising_threshold",  cfg.direction_rising_threshold)
            cfg.direction_falling_threshold = t.get("direction_falling_threshold", cfg.direction_falling_threshold)
        if "persistence" in d:
            p = d["persistence"]
            cfg.weekly_period = p.get("weekly_period", cfg.weekly_period)
            cfg.streak_normalize_lo = p.get("streak_normalize_lo", cfg.streak_normalize_lo)
            cfg.streak_normalize_hi = p.get("streak_normalize_hi", cfg.streak_normalize_hi)
            sw = p.get("score_weights", {})
            cfg.persistence_pos_pct_weight = sw.get("positive_pct", cfg.persistence_pos_pct_weight)
            cfg.persistence_streak_weight  = sw.get("streak_bonus",  cfg.persistence_streak_weight)
        if "quality" in d:
            q = d["quality"]
            cfg.quality_weights = q.get("score_weights", cfg.quality_weights)
            cfg.consistency_normalize_lo  = q.get("consistency_normalize_lo",  cfg.consistency_normalize_lo)
            cfg.consistency_normalize_hi  = q.get("consistency_normalize_hi",  cfg.consistency_normalize_hi)
            cfg.volatility_normalize_lo   = q.get("volatility_normalize_lo",   cfg.volatility_normalize_lo)
            cfg.volatility_normalize_hi   = q.get("volatility_normalize_hi",   cfg.volatility_normalize_hi)
            cfg.participation_normalize_lo = q.get("participation_normalize_lo", cfg.participation_normalize_lo)
            cfg.participation_normalize_hi = q.get("participation_normalize_hi", cfg.participation_normalize_hi)
        if "rs_score_weights" in d:
            cfg.rs_score_weights = d["rs_score_weights"]
        if "leadership" in d:
            ldr = d["leadership"]
            cfg.leader_rs_threshold  = ldr.get("leader_rs_threshold",  cfg.leader_rs_threshold)
            cfg.laggard_rs_threshold = ldr.get("laggard_rs_threshold", cfg.laggard_rs_threshold)
            cfg.leader_rank_top_pct  = ldr.get("leader_rank_top_pct",  cfg.leader_rank_top_pct)
            cfg.laggard_rank_bot_pct = ldr.get("laggard_rank_bot_pct", cfg.laggard_rank_bot_pct)
        if "ranking" in d:
            cfg.rank_jump_threshold = d["ranking"].get("rank_jump_threshold", cfg.rank_jump_threshold)
        if "rotation_readiness" in d:
            rr = d["rotation_readiness"]
            cfg.rr_weights       = rr.get("weights", cfg.rr_weights)
            cfg.rr_rank_mom_lo   = rr.get("rank_momentum_normalize_lo", cfg.rr_rank_mom_lo)
            cfg.rr_rank_mom_hi   = rr.get("rank_momentum_normalize_hi", cfg.rr_rank_mom_hi)
            cfg.rr_accel_lo      = rr.get("trend_accel_normalize_lo",   cfg.rr_accel_lo)
            cfg.rr_accel_hi      = rr.get("trend_accel_normalize_hi",   cfg.rr_accel_hi)
            cfg.rr_persist_lo    = rr.get("persistence_d_normalize_lo", cfg.rr_persist_lo)
            cfg.rr_persist_hi    = rr.get("persistence_d_normalize_hi", cfg.rr_persist_hi)
            cfg.breadth_sensitivity = rr.get("breadth_sensitivity", cfg.breadth_sensitivity)
        if "macro_validator" in d:
            mv = d["macro_validator"]
            cfg.macro_expected_leaders   = mv.get("expected_leaders",   cfg.macro_expected_leaders)
            cfg.macro_alignment_scores   = mv.get("alignment_score_map", cfg.macro_alignment_scores)
        if "heatmap" in d:
            cfg.heatmap_colors = d["heatmap"].get("colors", cfg.heatmap_colors)
        if "confidence" in d:
            c = d["confidence"]
            cfg.min_history_days   = c.get("min_history_days",   cfg.min_history_days)
            cfg.full_history_days  = c.get("full_history_days",  cfg.full_history_days)
            cfg.persistence_weight = c.get("persistence_weight", cfg.persistence_weight)
        return cfg
