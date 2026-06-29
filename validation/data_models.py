"""
validation/data_models.py
Step 8 — DSS Validation & Continuous Learning Platform
모든 데이터 클래스 정의
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class ValidationGrade(Enum):
    A_PLUS  = "A+"   # ≥ 80점
    A       = "A"    # ≥ 70점
    B       = "B"    # ≥ 60점
    C       = "C"    # ≥ 50점
    D       = "D"    # ≥ 40점
    F       = "F"    # < 40점

class HealthGrade(Enum):
    EXCELLENT = "Excellent"   # ≥ 80
    GOOD      = "Good"        # ≥ 65
    FAIR      = "Fair"        # ≥ 50
    POOR      = "Poor"        # ≥ 35
    CRITICAL  = "Critical"    # < 35

class FailureType(Enum):
    CONSECUTIVE_LOSS  = "ConsecutiveLoss"
    LARGE_DRAWDOWN    = "LargeDrawdown"
    SIGNAL_MISS       = "SignalMiss"
    REGIME_ERROR      = "RegimeError"
    CALIBRATION_MISS  = "CalibrationMiss"

class DiagnosticSeverity(Enum):
    CRITICAL = "Critical"
    WARNING  = "Warning"
    INFO     = "Info"


# ═══════════════════════════════════════════════════════════════════════════
# Core Input
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DecisionRecord:
    """단일 날짜의 의사결정 스냅샷"""
    date: str
    # Engine scores at that point in time
    macro_score:    float = 50.0
    breadth_score:  float = 50.0
    rs_score:       float = 50.0
    rotation_score: float = 50.0
    portfolio_score: float = 50.0
    risk_score:     float = 50.0
    # Decision outputs
    confidence:     float = 50.0
    action:         str   = "HOLD"
    # Allocation at time of decision
    weights:        Dict[str, float] = field(default_factory=dict)
    # Actual outcome (filled in retrospectively)
    actual_return:  float = 0.0
    correct:        bool  = False


@dataclass
class PriceHistory:
    """가격 이력 컨테이너"""
    dates:  List[str]
    prices: Dict[str, List[float]]   # ticker → price list

    def returns(self, ticker: str) -> List[float]:
        p = self.prices.get(ticker, [])
        if len(p) < 2:
            return []
        return [(p[i] / p[i-1]) - 1.0 for i in range(1, len(p))]

    def all_tickers(self) -> List[str]:
        return list(self.prices.keys())


@dataclass
class ValidationInput:
    """ValidationEngine 진입점 입력"""
    decision_records:  List[DecisionRecord]
    price_history:     PriceHistory
    benchmark_prices:  Dict[str, List[float]]   # "SPY" → [...], "QQQ" → [...]
    initial_capital:   float = 100_000.0
    risk_free_rate:    float = 0.045
    # 선택적 입력 (없으면 해당 검증 skip)
    replay_date:       Optional[str] = None
    strategy_b_records: Optional[List[DecisionRecord]] = None


# ═══════════════════════════════════════════════════════════════════════════
# Backtest
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class TradeRecord:
    date:   str
    ticker: str
    action: str   # BUY / SELL / HOLD
    weight_before: float
    weight_after:  float
    price:  float = 0.0

@dataclass
class BacktestResult:
    dates:             List[str]
    portfolio_values:  List[float]
    daily_returns:     List[float]
    trades:            List[TradeRecord]
    total_return:      float
    n_trades:          int
    win_rate:          float    # % of profitable trades
    avg_hold_days:     float

@dataclass
class WalkForwardWindow:
    window_id:    int
    is_start:     int    # index into decision_records
    is_end:       int
    oos_start:    int
    oos_end:      int
    is_sharpe:    float
    oos_sharpe:   float
    oos_return:   float
    degradation:  float  # oos_sharpe / is_sharpe

@dataclass
class WalkForwardResult:
    windows:          List[WalkForwardWindow]
    avg_oos_sharpe:   float
    avg_degradation:  float
    stability_score:  float   # 0~100
    oos_consistent:   bool    # OOS Sharpe > 0 in ≥ 70% windows

@dataclass
class BenchmarkResult:
    benchmark_id:       str
    benchmark_return:   float
    strategy_return:    float
    alpha:              float
    beta:               float
    information_ratio:  float
    tracking_error:     float
    win_rate_vs_bench:  float   # % months strategy > bench
    correlation:        float


# ═══════════════════════════════════════════════════════════════════════════
# Risk Metrics
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class RiskMetrics:
    cagr:           float
    volatility:     float
    sharpe:         float
    sortino:        float
    calmar:         float
    max_drawdown:   float   # positive value (e.g. 0.18 = 18%)
    ulcer_index:    float
    # Derived
    var_95:         float   # Value at Risk 95%
    best_day:       float
    worst_day:      float
    positive_days:  float   # ratio


# ═══════════════════════════════════════════════════════════════════════════
# Attribution
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class EngineAttribution:
    engine:              str
    beta_coefficient:    float   # regression coefficient
    contribution_pct:    float   # % of total alpha
    signal_accuracy:     float   # % correct direction calls
    avg_signal:          float   # average score
    correlation_with_return: float

@dataclass
class AttributionResult:
    engine_attributions: List[EngineAttribution]
    total_alpha:         float
    r_squared:           float   # regression R²
    best_engine:         str
    worst_engine:        str
    xai_summary:         str


# ═══════════════════════════════════════════════════════════════════════════
# Sensitivity & Robustness
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SensitivityCell:
    engine:        str
    delta_pct:     float     # -20%, -10%, 0%, +10%, +20%
    sharpe_change: float
    return_change: float
    risk_change:   float

@dataclass
class SensitivityResult:
    grid:          List[SensitivityCell]
    most_sensitive_engine:  str
    least_sensitive_engine: str
    max_sharpe_engine:      str    # engine with best upside sensitivity
    xai_summary:   str

@dataclass
class RobustnessCell:
    parameter:     str
    delta_pct:     float
    sharpe_base:   float
    sharpe_perturbed: float
    stable:        bool    # |change| < 10%

@dataclass
class RobustnessResult:
    cells:         List[RobustnessCell]
    robustness_score: float   # 0~100 (% stable cells × 100)
    fragile_params: List[str]
    stable_params:  List[str]
    xai_summary:   str


# ═══════════════════════════════════════════════════════════════════════════
# Monte Carlo Validation
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MCValidationResult:
    n_simulations:    int
    strategy_sharpe:  float
    sim_sharpe_p5:    float
    sim_sharpe_p50:   float
    sim_sharpe_p95:   float
    p_value:          float     # P(sim ≥ strategy_sharpe)
    significant:      bool      # p_value < 0.05
    strategy_cagr:    float
    sim_cagr_p5:      float
    sim_cagr_p50:     float
    sim_cagr_p95:     float
    xai_summary:      str


# ═══════════════════════════════════════════════════════════════════════════
# Failure Analysis
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class FailureRecord:
    date:           str
    failure_type:   FailureType
    loss:           float
    context:        str    # market environment at failure
    engine_signals: Dict[str, float] = field(default_factory=dict)

@dataclass
class FailureAnalysisResult:
    total_failures:  int
    by_type:         Dict[str, int]
    worst_failure:   Optional[FailureRecord]
    common_context:  str    # most common market env during failures
    failure_rate:    float  # failures / total decisions
    recovery_avg_days: float
    xai_summary:     str


# ═══════════════════════════════════════════════════════════════════════════
# Explainability Audit
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class XAIConsistencyRecord:
    date:           str
    decision:       str
    confidence:     float
    feature_scores: Dict[str, float]
    consistency_score: float   # 0~100 (how well signals agree)
    contradictions:  List[str]  # signals that contradict the decision

@dataclass
class XAIAuditResult:
    records:            List[XAIConsistencyRecord]
    avg_consistency:    float
    low_consistency_cnt: int   # consistency < 50
    high_confidence_wrong: int  # confidence > 70 but wrong
    xai_summary:        str


# ═══════════════════════════════════════════════════════════════════════════
# Decision Replay
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DecisionReplay:
    replay_date:     str
    engine_scores:   Dict[str, float]
    decision:        str
    confidence:      float
    weights:         Dict[str, float]
    actual_return:   float
    was_correct:     bool
    explanation:     str


# ═══════════════════════════════════════════════════════════════════════════
# Strategy Version Comparison
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class VersionComparisonResult:
    version_a_sharpe:  float
    version_b_sharpe:  float
    version_a_cagr:    float
    version_b_cagr:    float
    winner:            str    # "A" or "B"
    delta_sharpe:      float
    delta_cagr:        float
    xai_summary:       str


# ═══════════════════════════════════════════════════════════════════════════
# Confidence Calibration
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CalibrationBin:
    confidence_lo:  float
    confidence_hi:  float
    avg_confidence: float
    actual_accuracy: float
    count:          int

@dataclass
class CalibrationResult:
    bins:           List[CalibrationBin]
    ece:            float   # Expected Calibration Error
    brier_score:    float
    overconfident_pct: float   # % bins where confidence > accuracy
    underconfident_pct: float
    xai_summary:    str


# ═══════════════════════════════════════════════════════════════════════════
# Engine Health
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class EngineHealthScore:
    engine:         str
    accuracy:       float    # 0~100: % correct direction calls
    consistency:    float    # 0~100: signal stability (1 - CV)
    calibration:    float    # 0~100: 100 - ECE*100
    contribution:   float    # 0~100: normalized alpha contribution
    overall:        float    # weighted composite
    grade:          HealthGrade
    trend:          str      # "↑" improving / "↓" degrading / "→" stable

@dataclass
class DiagnosticFinding:
    engine:        str
    severity:      DiagnosticSeverity
    issue:         str
    root_cause:    str
    recommendation: str

@dataclass
class DiagnosticResult:
    findings:          List[DiagnosticFinding]
    degraded_engines:  List[str]
    healthy_engines:   List[str]
    overall_health:    float    # 0~100
    xai_summary:       str


# ═══════════════════════════════════════════════════════════════════════════
# ★★★★★ Weight Recommendation (자동 적용 절대 금지)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class WeightRecommendation:
    """
    ★★★★★ RECOMMEND ONLY — 절대 자동 적용 금지.
    추천 Weight, 추천 이유, 예상 효과만 제시한다.
    실제 Weight 변경은 사용자가 직접 수행해야 한다.
    """
    engine:           str
    current_weight:   float
    recommended_weight: float
    delta:            float     # recommended - current
    reason:           str       # 추천 이유
    expected_sharpe_delta: float   # 예상 Sharpe 변화
    expected_return_delta: float   # 예상 수익률 변화
    confidence_level: str       # "High" / "Medium" / "Low"
    caveat:           str       # 주의사항


# ═══════════════════════════════════════════════════════════════════════════
# XAI Summary (Top-level narrative)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class XAISummary:
    why_outperformed_spy:  str
    best_alpha_engine:     str
    worst_market_env:      str
    best_weight_insight:   str
    overall_narrative:     str


# ═══════════════════════════════════════════════════════════════════════════
# Top-level ValidationResult
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ValidationResult:
    # Backtesting
    backtest:          BacktestResult
    walk_forward:      WalkForwardResult
    benchmarks:        List[BenchmarkResult]

    # Risk
    risk_metrics:      RiskMetrics

    # Analysis
    attribution:       AttributionResult
    sensitivity:       SensitivityResult
    robustness:        RobustnessResult
    monte_carlo:       MCValidationResult
    failure_analysis:  FailureAnalysisResult
    xai_audit:         XAIAuditResult

    # Replay / Comparison
    replay:            Optional[DecisionReplay]
    version_comparison: Optional[VersionComparisonResult]

    # Health
    engine_health:     Dict[str, EngineHealthScore]
    diagnostic:        DiagnosticResult

    # Calibration
    calibration:       CalibrationResult

    # ★★★★★ Recommendations (자동 적용 금지)
    weight_recommendations: List[WeightRecommendation]

    # Summary
    xai_summary:       XAISummary
    overall_grade:     ValidationGrade
    reasons:           List[str]
    warnings:          List[str]

    @property
    def primary_benchmark(self) -> Optional[BenchmarkResult]:
        return self.benchmarks[0] if self.benchmarks else None

    @property
    def best_engine(self) -> str:
        return self.attribution.best_engine

    @property
    def is_robust(self) -> bool:
        return self.robustness.robustness_score >= 70.0

    @property
    def mc_significant(self) -> bool:
        return self.monte_carlo.significant
