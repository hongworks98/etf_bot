"""
engines/portfolio_optimizer/data_models.py
All enums, dataclasses, and config for PortfolioOptimizationEngine (Step 6).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class AllocationRegime(Enum):
    AGGRESSIVE = "Aggressive"
    BALANCED   = "Balanced"
    DEFENSIVE  = "Defensive"


class RebalanceUrgency(Enum):
    IMMEDIATE   = "Immediate"
    THIS_WEEK   = "This Week"
    THIS_MONTH  = "This Month"
    MONITOR     = "Monitor"
    NO_ACTION   = "No Action"


class TradeDirection(Enum):
    BUY    = "Buy"
    SELL   = "Sell"
    HOLD   = "Hold"


class DiversificationGrade(Enum):
    EXCELLENT = "Excellent"
    GOOD      = "Good"
    FAIR      = "Fair"
    POOR      = "Poor"
    CRITICAL  = "Critical"


# ─────────────────────────────────────────────
# Input Dataclasses
# ─────────────────────────────────────────────

@dataclass
class PortfolioState:
    """Current portfolio snapshot — holdings, value, price history."""
    current_holdings: Dict[str, float]        # ticker → weight (0~1)
    portfolio_value: float                    # total $ value
    cash_pct: float                           # current cash weight 0~1
    target_tickers: List[str]                 # ETFs under consideration
    price_history: Dict[str, List[float]]     # ticker → daily close prices

    def current_weight(self, ticker: str) -> float:
        return self.current_holdings.get(ticker, 0.0)

    def total_invested(self) -> float:
        return self.portfolio_value * (1.0 - self.cash_pct)

    def daily_returns(self, ticker: str) -> List[float]:
        prices = self.price_history.get(ticker, [])
        if len(prices) < 2:
            return []
        return [(prices[i] / prices[i - 1]) - 1.0 for i in range(1, len(prices))]


@dataclass
class OptimizationInput:
    """Aggregated multi-engine input (duck-typed for engine independence)."""
    portfolio_state: PortfolioState
    decision_results: Dict[str, Any] = field(default_factory=dict)
    rotation_results: Dict[str, Any] = field(default_factory=dict)
    rs_results: Dict[str, Any]       = field(default_factory=dict)
    macro_state: str     = "Unknown"
    macro_score: float   = 50.0
    macro_direction: str = "FLAT"
    breadth_score: float = 50.0
    breadth_health: str  = "Neutral"
    market_health_score: float = 50.0
    aux_data: Optional[Any] = None

    # ── Helper accessors (getattr duck-typed) ──────────────────────────

    def get_rs_score(self, ticker: str) -> float:
        r = self.rs_results.get(ticker)
        return float(getattr(r, "rs_score", 50.0)) if r else 50.0

    def get_rotation_score(self, ticker: str) -> float:
        r = self.rotation_results.get(ticker)
        return float(getattr(r, "rotation_score", 50.0)) if r else 50.0

    def get_conviction_score(self, ticker: str) -> float:
        r = self.rotation_results.get(ticker)
        return float(getattr(r, "conviction_score", 50.0)) if r else 50.0

    def get_decision_score(self, ticker: str) -> float:
        r = self.decision_results.get(ticker)
        return float(getattr(r, "decision_score", 50.0)) if r else 50.0

    def get_rotation_stage(self, ticker: str) -> str:
        r = self.rotation_results.get(ticker)
        stage = getattr(r, "stage", None)
        if stage is None:
            return "Unknown"
        return getattr(stage, "value", str(stage))

    def is_macro_aligned(self, ticker: str, expected_leaders: Dict[str, List[str]]) -> bool:
        leaders = expected_leaders.get(self.macro_state, [])
        return ticker in leaders

    def latest_vix(self) -> float:
        if self.aux_data is None:
            return 20.0
        fn = getattr(self.aux_data, "latest_vix", None)
        return float(fn()) if callable(fn) else 20.0

    @property
    def tickers(self) -> List[str]:
        return self.portfolio_state.target_tickers


# ─────────────────────────────────────────────
# Per-ETF Result
# ─────────────────────────────────────────────

@dataclass
class AllocationResult:
    """Per-ETF allocation detail with full XAI decomposition."""
    ticker: str
    target_weight: float        = 0.0
    current_weight: float       = 0.0
    delta_weight: float         = 0.0
    signal_score: float         = 50.0   # 0~100
    regime_base_weight: float   = 0.0
    signal_adjustment: float    = 0.0
    risk_contribution: float    = 0.0    # actual % of portfolio variance
    risk_budget_pct: float      = 0.0    # target equal-risk % (100/N)
    position_value: float       = 0.0    # $ amount
    shares_estimate: float      = 0.0    # approx shares
    xai_explanation: str        = ""
    trade_direction: TradeDirection = TradeDirection.HOLD

    def __post_init__(self):
        self.delta_weight = round(self.target_weight - self.current_weight, 6)
        if self.delta_weight > 0.001:
            self.trade_direction = TradeDirection.BUY
        elif self.delta_weight < -0.001:
            self.trade_direction = TradeDirection.SELL


# ─────────────────────────────────────────────
# Risk Budget
# ─────────────────────────────────────────────

@dataclass
class RiskBudget:
    ticker: str
    weight: float             = 0.0
    marginal_risk: float      = 0.0    # Cov·w vector component
    risk_contribution: float  = 0.0    # w_i × (Cov·w)_i
    risk_pct: float           = 0.0    # % of total portfolio variance
    target_risk_pct: float    = 0.0    # equal-risk target (100/N)
    risk_overshoot: float     = 0.0    # risk_pct - target_risk_pct


# ─────────────────────────────────────────────
# Scenario & Monte Carlo
# ─────────────────────────────────────────────

@dataclass
class ScenarioResult:
    name: str                               # "Base" / "Bull" / "Bear"
    target_allocation: Dict[str, float] = field(default_factory=dict)
    expected_return_est: float = 0.0       # annualized
    expected_risk_est: float   = 0.0       # annualized vol
    sharpe_est: float          = 0.0
    max_weight: float          = 0.0
    min_weight: float          = 0.0
    cash_pct: float            = 0.0
    summary: str               = ""


@dataclass
class MonteCarloResult:
    n_simulations: int           = 500
    n_days: int                  = 252
    p5:  float = 0.0    # 5th  percentile final value (relative to 1.0)
    p25: float = 0.0
    p50: float = 0.0    # median
    p75: float = 0.0
    p95: float = 0.0
    var_5pct: float = 0.0        # Value-at-Risk (5%)
    cvar_5pct: float = 0.0       # Conditional VaR
    expected_annual_return: float = 0.0
    expected_annual_vol: float    = 0.0


# ─────────────────────────────────────────────
# Trade & Rebalancing
# ─────────────────────────────────────────────

@dataclass
class SuggestedTrade:
    ticker: str
    direction: TradeDirection
    current_weight: float   = 0.0
    target_weight: float    = 0.0
    delta_weight: float     = 0.0
    trade_value: float      = 0.0    # $ amount
    shares_estimate: float  = 0.0
    reason: str             = ""


@dataclass
class RebalanceSignal:
    urgency: RebalanceUrgency          = RebalanceUrgency.MONITOR
    max_delta: float                   = 0.0
    total_turnover: float              = 0.0     # sum of |delta|
    estimated_cost: float              = 0.0     # transaction costs
    opportunity_cost_daily: float      = 0.0
    opportunity_cost_monthly: float    = 0.0
    days_to_breakeven: int             = 0
    reason: str                        = ""


# ─────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────

@dataclass
class DashboardData:
    current_allocation: List[Dict]   = field(default_factory=list)  # pie slices
    target_allocation: List[Dict]    = field(default_factory=list)
    allocation_wheel: List[Dict]     = field(default_factory=list)  # donut chart
    sector_exposure: List[Dict]      = field(default_factory=list)  # bar chart
    correlation_matrix: List[Dict]   = field(default_factory=list)  # heat grid
    risk_budget: List[Dict]          = field(default_factory=list)  # stacked bar
    diversification_gauge: Dict      = field(default_factory=dict)  # gauge widget
    scenario_comparison: List[Dict]  = field(default_factory=list)  # grouped bar


# ─────────────────────────────────────────────
# Main Output
# ─────────────────────────────────────────────

@dataclass
class PortfolioOptimizationResult:
    """Full output from PortfolioOptimizationEngine."""
    # Per-ETF
    ticker_results: Dict[str, AllocationResult] = field(default_factory=dict)

    # Allocations
    target_allocation: Dict[str, float]  = field(default_factory=dict)
    current_allocation: Dict[str, float] = field(default_factory=dict)
    delta_allocation: Dict[str, float]   = field(default_factory=dict)
    cash_recommendation: float           = 0.03

    # Regime
    regime: AllocationRegime     = AllocationRegime.BALANCED
    regime_explanation: str      = ""

    # Risk analysis
    risk_budget: Dict[str, RiskBudget]            = field(default_factory=dict)
    diversification_score: float                   = 50.0
    diversification_grade: DiversificationGrade    = DiversificationGrade.FAIR
    correlation_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    concentration_risk: float  = 0.0     # HHI × 100

    # Exposure
    sector_exposure: Dict[str, float] = field(default_factory=dict)

    # Scenarios & Monte Carlo
    scenario_results: Dict[str, ScenarioResult] = field(default_factory=dict)
    monte_carlo: Optional[MonteCarloResult]     = None

    # Trades & Rebalancing
    suggested_trades: List[SuggestedTrade]  = field(default_factory=list)
    rebalance_signal: RebalanceSignal       = field(default_factory=RebalanceSignal)
    opportunity_cost: Dict[str, float]      = field(default_factory=dict)

    # Dashboard
    dashboard_data: DashboardData = field(default_factory=DashboardData)

    # XAI & Narrative
    reasons: List[str]   = field(default_factory=list)
    warnings: List[str]  = field(default_factory=list)
    xai_summary: str     = ""

    # ── Convenience Properties ──────────────────────────────────────────

    @property
    def top_positions(self) -> List[Tuple[str, float]]:
        """Sorted (ticker, weight) descending."""
        return sorted(self.target_allocation.items(), key=lambda x: x[1], reverse=True)

    @property
    def needs_rebalancing(self) -> bool:
        return self.rebalance_signal.urgency in {
            RebalanceUrgency.IMMEDIATE, RebalanceUrgency.THIS_WEEK
        }

    @property
    def is_well_diversified(self) -> bool:
        return self.diversification_score >= 60.0


# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

@dataclass
class OptimizationConfig:
    # Signal weights
    w_rs: float         = 0.30
    w_rotation: float   = 0.25
    w_conviction: float = 0.20
    w_macro: float      = 0.15
    w_breadth: float    = 0.10

    # Macro alignment
    aligned_strong: float   = 100.0
    aligned_neutral: float  =  65.0
    misaligned_strong: float =  25.0
    misaligned_neutral: float = 45.0
    unknown_macro: float    =  50.0
    expected_leaders: Dict[str, List[str]] = field(default_factory=lambda: {
        "Recovery":      ["XLF", "XLY", "XLI", "XLK"],
        "Expansion":     ["XLK", "XLC", "XLY", "XLF"],
        "Overheating":   ["XLE", "XLB", "XLI", "XLF"],
        "Slowdown":      ["XLP", "XLU", "XLV", "XLB"],
        "Recession":     ["XLU", "XLP", "XLV"],
        "EarlyRecovery": ["XLF", "XLK", "XLY"],
        "Unknown":       [],
    })

    # Regime
    aggressive_states: List[str] = field(default_factory=lambda: ["Recovery","Expansion"])
    defensive_states: List[str]  = field(default_factory=lambda: ["Recession","Slowdown"])
    aggressive_health_min: float = 60.0
    aggressive_vix_max: float    = 25.0
    defensive_health_max: float  = 40.0
    defensive_vix_min: float     = 35.0
    sector_categories: Dict[str, List[str]] = field(default_factory=lambda: {
        "cyclical":  ["XLK","XLC","XLY","XLF","XLI","XLE","XLB"],
        "defensive": ["XLP","XLU","XLV","XLRE"],
    })
    regime_templates: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "Aggressive": {
            "XLK":0.22,"XLC":0.10,"XLY":0.12,"XLF":0.12,"XLI":0.10,
            "XLE":0.08,"XLB":0.06,"XLV":0.06,"XLP":0.05,"XLU":0.04,"XLRE":0.05,
            "default_cyclical":0.09,"default_defensive":0.05,"default_unknown":0.07,
        },
        "Balanced": {
            "XLK":0.15,"XLC":0.09,"XLY":0.09,"XLF":0.09,"XLI":0.08,
            "XLE":0.07,"XLB":0.07,"XLV":0.09,"XLP":0.09,"XLU":0.09,"XLRE":0.09,
            "default_cyclical":0.08,"default_defensive":0.08,"default_unknown":0.08,
        },
        "Defensive": {
            "XLK":0.08,"XLC":0.06,"XLY":0.07,"XLF":0.07,"XLI":0.06,
            "XLE":0.05,"XLB":0.05,"XLV":0.14,"XLP":0.14,"XLU":0.14,"XLRE":0.14,
            "default_cyclical":0.05,"default_defensive":0.12,"default_unknown":0.08,
        },
    })

    # Allocation constraints
    max_signal_adj_pct: float = 0.40
    min_weight: float         = 0.02
    max_weight: float         = 0.35
    min_positions: int        = 4
    max_positions: int        = 11
    rebalance_threshold: float = 0.03

    # Cash
    base_cash: float     = 0.03
    vix_cash_add: float  = 0.05
    macro_cash_add: float= 0.05
    health_cash_add: float= 0.04
    breadth_cash_add: float=0.03
    vix_high: float      = 30.0
    health_low: float    = 40.0
    breadth_low: float   = 40.0
    cash_min: float      = 0.02
    cash_max: float      = 0.25

    # Risk budget
    min_history_days: int    = 20
    annualize_factor: int    = 252
    risk_free_rate: float    = 0.045

    # Diversification
    excellent_threshold: float = 80.0
    good_threshold: float      = 60.0
    fair_threshold: float      = 40.0

    # Concentration
    high_hhi: float    = 0.20
    extreme_hhi: float = 0.30

    # Correlation
    high_corr_threshold: float    = 0.80
    extreme_corr_threshold: float = 0.90
    corr_min_history: int         = 20

    # Position sizing
    min_trade_value: float  = 500.0
    price_fallback: float   = 100.0

    # Scenarios
    scenario_shocks: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "Bull": {"rs": 15.0, "rotation": 10.0, "breadth": 10.0, "vix": -5.0,  "return_premium": 0.05},
        "Bear": {"rs":-20.0, "rotation":-15.0, "breadth":-20.0, "vix":  20.0, "return_premium":-0.08},
        "Base": {"rs":  0.0, "rotation":  0.0, "breadth":  0.0, "vix":   0.0, "return_premium": 0.0},
    })

    # Monte Carlo
    mc_n_simulations: int = 500
    mc_n_days: int        = 252
    mc_percentiles: List[int] = field(default_factory=lambda: [5,25,50,75,95])
    mc_min_history: int   = 30

    # Rebalancing
    immediate_threshold: float   = 0.10
    this_week_threshold: float   = 0.05
    this_month_threshold: float  = 0.02
    daily_alpha_estimate: float  = 0.0003
    transaction_cost_pct: float  = 0.001

    # Adaptive
    max_risk_overshoot: float    = 20.0
    convergence_iter: int        = 3

    @classmethod
    def from_dict(cls, d: dict) -> "OptimizationConfig":
        cfg = cls()
        sw = d.get("signal_weights", {})
        cfg.w_rs         = sw.get("rs_score", cfg.w_rs)
        cfg.w_rotation   = sw.get("rotation_score", cfg.w_rotation)
        cfg.w_conviction = sw.get("conviction_score", cfg.w_conviction)
        cfg.w_macro      = sw.get("macro_alignment", cfg.w_macro)
        cfg.w_breadth    = sw.get("breadth_score", cfg.w_breadth)

        ma = d.get("macro_alignment_scores", {})
        cfg.aligned_strong     = ma.get("aligned_strong",   cfg.aligned_strong)
        cfg.aligned_neutral    = ma.get("aligned_neutral",  cfg.aligned_neutral)
        cfg.misaligned_strong  = ma.get("misaligned_strong",cfg.misaligned_strong)
        cfg.misaligned_neutral = ma.get("misaligned_neutral",cfg.misaligned_neutral)
        cfg.unknown_macro      = ma.get("unknown",          cfg.unknown_macro)
        if "expected_leaders" in d:
            cfg.expected_leaders = d["expected_leaders"]

        reg = d.get("regime", {})
        cfg.aggressive_states    = reg.get("aggressive_states", cfg.aggressive_states)
        cfg.defensive_states     = reg.get("defensive_states",  cfg.defensive_states)
        cfg.aggressive_health_min= reg.get("aggressive_health_min", cfg.aggressive_health_min)
        cfg.aggressive_vix_max   = reg.get("aggressive_vix_max",    cfg.aggressive_vix_max)
        cfg.defensive_health_max = reg.get("defensive_health_max",  cfg.defensive_health_max)
        cfg.defensive_vix_min    = reg.get("defensive_vix_min",     cfg.defensive_vix_min)
        if "sector_categories" in d:
            cfg.sector_categories = d["sector_categories"]
        if "regime_templates" in d:
            cfg.regime_templates = d["regime_templates"]

        al = d.get("allocation", {})
        cfg.max_signal_adj_pct = al.get("max_signal_adj_pct", cfg.max_signal_adj_pct)
        cfg.min_weight         = al.get("min_weight",         cfg.min_weight)
        cfg.max_weight         = al.get("max_weight",         cfg.max_weight)
        cfg.rebalance_threshold= al.get("rebalance_threshold",cfg.rebalance_threshold)

        ca = d.get("cash", {})
        cfg.base_cash      = ca.get("base_cash",      cfg.base_cash)
        cfg.vix_cash_add   = ca.get("vix_cash_add",   cfg.vix_cash_add)
        cfg.macro_cash_add = ca.get("macro_cash_add", cfg.macro_cash_add)
        cfg.health_cash_add= ca.get("health_cash_add",cfg.health_cash_add)
        cfg.breadth_cash_add=ca.get("breadth_cash_add",cfg.breadth_cash_add)
        cfg.vix_high       = ca.get("vix_high",       cfg.vix_high)
        cfg.health_low     = ca.get("health_low",     cfg.health_low)
        cfg.breadth_low    = ca.get("breadth_low",    cfg.breadth_low)
        cfg.cash_min       = ca.get("cash_min",       cfg.cash_min)
        cfg.cash_max       = ca.get("cash_max",       cfg.cash_max)

        rb = d.get("risk_budget", {})
        cfg.min_history_days = rb.get("min_history_days", cfg.min_history_days)
        cfg.risk_free_rate   = rb.get("risk_free_rate",   cfg.risk_free_rate)

        mc = d.get("monte_carlo", {})
        cfg.mc_n_simulations = mc.get("n_simulations",  cfg.mc_n_simulations)
        cfg.mc_n_days        = mc.get("n_days",          cfg.mc_n_days)
        cfg.mc_min_history   = mc.get("min_history_days",cfg.mc_min_history)

        re = d.get("rebalancing", {})
        cfg.immediate_threshold  = re.get("immediate_threshold",   cfg.immediate_threshold)
        cfg.this_week_threshold  = re.get("this_week_threshold",   cfg.this_week_threshold)
        cfg.this_month_threshold = re.get("this_month_threshold",  cfg.this_month_threshold)
        cfg.daily_alpha_estimate = re.get("daily_alpha_estimate",  cfg.daily_alpha_estimate)
        cfg.transaction_cost_pct = re.get("transaction_cost_pct",  cfg.transaction_cost_pct)

        sc = d.get("scenarios", {})
        for sname in ("bull", "bear", "base"):
            if sname in sc:
                key = sname.capitalize()
                s = sc[sname]
                cfg.scenario_shocks[key] = {
                    "rs":       s.get("rs_shock",        0.0),
                    "rotation": s.get("rotation_shock",  0.0),
                    "breadth":  s.get("breadth_shock",   0.0),
                    "vix":      s.get("vix_shock",       0.0),
                    "return_premium": s.get("return_premium", s.get("return_penalty", 0.0)),
                }
        return cfg
