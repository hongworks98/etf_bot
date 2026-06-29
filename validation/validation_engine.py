"""
validation/validation_engine.py
Step 8 — DSS Validation & Continuous Learning Platform
메인 오케스트레이터

기존 Architecture와 기존 Engine은 절대 수정하지 않는다.
모든 Engine 출력은 오직 입력으로만 사용한다.
"""
from __future__ import annotations
from typing import List, Optional, Dict

from validation.data_models import (
    ValidationInput, ValidationResult,
    ValidationGrade, XAISummary,
)
# Backtesting
from validation.backtesting.full_backtest    import FullBacktest
from validation.backtesting.walk_forward     import WalkForwardValidator
from validation.backtesting.benchmark_comparator import BenchmarkComparator
from validation.backtesting.decision_replayer    import DecisionReplayer
# Metrics
from validation.metrics.risk_calculator      import RiskCalculator
from validation.metrics.attribution_engine   import AttributionEngine
from validation.metrics.confidence_calibrator import ConfidenceCalibrator
# Analysis
from validation.analysis.sensitivity_analyzer   import SensitivityAnalyzer
from validation.analysis.robustness_tester      import RobustnessTester
from validation.analysis.monte_carlo_validator  import MCValidator
from validation.analysis.failure_analyzer       import FailureAnalyzer
from validation.analysis.explainability_auditor import ExplainabilityAuditor
# Health
from validation.health.engine_health_scorer import EngineHealthScorer
from validation.health.auto_diagnostic      import AutoDiagnostic
# Learning
from validation.learning.weight_recommender import WeightRecommender


class ValidationEngine:
    """
    Production-ready Validation & Continuous Learning Platform.
    Integrates all validation sub-modules via constructor injection.

    Usage:
        engine = ValidationEngine()
        result = engine.validate(inp)
        print(engine.explain(result))
    """

    def __init__(
        self,
        backtest:       FullBacktest        = None,
        walk_forward:   WalkForwardValidator = None,
        benchmarker:    BenchmarkComparator  = None,
        replayer:       DecisionReplayer     = None,
        risk_calc:      RiskCalculator       = None,
        attribution:    AttributionEngine    = None,
        calibrator:     ConfidenceCalibrator = None,
        sensitivity:    SensitivityAnalyzer  = None,
        robustness:     RobustnessTester     = None,
        mc_validator:   MCValidator          = None,
        failure_anal:   FailureAnalyzer      = None,
        xai_auditor:    ExplainabilityAuditor = None,
        health_scorer:  EngineHealthScorer   = None,
        diagnostic:     AutoDiagnostic       = None,
        recommender:    WeightRecommender    = None,
    ):
        self._backtest      = backtest      or FullBacktest()
        self._walk_forward  = walk_forward  or WalkForwardValidator()
        self._benchmarker   = benchmarker   or BenchmarkComparator()
        self._replayer      = replayer      or DecisionReplayer()
        self._risk_calc     = risk_calc     or RiskCalculator()
        self._attribution   = attribution   or AttributionEngine()
        self._calibrator    = calibrator    or ConfidenceCalibrator()
        self._sensitivity   = sensitivity   or SensitivityAnalyzer()
        self._robustness    = robustness    or RobustnessTester()
        self._mc_validator  = mc_validator  or MCValidator()
        self._failure_anal  = failure_anal  or FailureAnalyzer()
        self._xai_auditor   = xai_auditor   or ExplainabilityAuditor()
        self._health_scorer = health_scorer or EngineHealthScorer()
        self._diagnostic    = diagnostic    or AutoDiagnostic()
        self._recommender   = recommender   or WeightRecommender()

    # ── Main entry point ───────────────────────────────────────────────

    def validate(self, inp: ValidationInput) -> ValidationResult:
        """
        4-Phase Validation Pipeline:
          Phase 1: Data Preparation (implicit — inp is pre-validated)
          Phase 2: Backtesting & Metrics
          Phase 3: Analysis
          Phase 4: Health & Learning
        """
        records = inp.decision_records

        # ── Phase 2: Backtesting & Metrics ─────────────────────────
        backtest_result = self._backtest.run(
            records, inp.price_history, inp.initial_capital
        )
        wf_result  = self._walk_forward.validate(records)
        bench_list = self._benchmarker.compare(
            backtest_result.daily_returns, inp.benchmark_prices
        )
        risk       = self._risk_calc.calculate(
            backtest_result.daily_returns, inp.risk_free_rate
        )
        attr       = self._attribution.attribute(records)
        calibration = self._calibrator.calibrate(records)

        # ── Phase 3: Analysis ───────────────────────────────────────
        sensitivity     = self._sensitivity.analyze(records)
        robustness      = self._robustness.test(records)
        mc              = self._mc_validator.validate(backtest_result.daily_returns)
        failure         = self._failure_anal.analyze(records)
        xai_audit       = self._xai_auditor.audit(records)

        # ── Optional: Replay ────────────────────────────────────────
        replay = None
        if inp.replay_date:
            replay = self._replayer.replay(records, inp.replay_date)

        # ── Optional: Version Comparison ────────────────────────────
        version_cmp = None
        if inp.strategy_b_records:
            version_cmp = self._compare_versions(records, inp.strategy_b_records, inp)

        # ── Phase 4: Health & Learning ──────────────────────────────
        engine_health = self._health_scorer.score(records, attr)
        diag          = self._diagnostic.diagnose(engine_health)
        weight_recs   = self._recommender.recommend(sensitivity, engine_health)

        # ── Grade & Summary ─────────────────────────────────────────
        grade        = self._compute_grade(risk, bench_list)
        xai_summary  = self._build_xai_summary(risk, bench_list, attr, sensitivity)
        reasons, warnings = self._build_narrative(
            risk, bench_list, wf_result, robustness, mc, diag, calibration
        )

        return ValidationResult(
            backtest           = backtest_result,
            walk_forward       = wf_result,
            benchmarks         = bench_list,
            risk_metrics       = risk,
            attribution        = attr,
            sensitivity        = sensitivity,
            robustness         = robustness,
            monte_carlo        = mc,
            failure_analysis   = failure,
            xai_audit          = xai_audit,
            replay             = replay,
            version_comparison = version_cmp,
            engine_health      = engine_health,
            diagnostic         = diag,
            calibration        = calibration,
            weight_recommendations = weight_recs,
            xai_summary        = xai_summary,
            overall_grade      = grade,
            reasons            = reasons,
            warnings           = warnings,
        )

    def explain(self, result: ValidationResult) -> str:
        """Human-readable XAI summary of validation result."""
        r = result
        lines = [
            "═" * 60,
            f"  DSS Validation Report — Overall Grade: {r.overall_grade.value}",
            "═" * 60,
            f"  CAGR         : {r.risk_metrics.cagr*100:.2f}%",
            f"  Sharpe       : {r.risk_metrics.sharpe:.3f}",
            f"  Max Drawdown : {r.risk_metrics.max_drawdown*100:.2f}%",
            f"  Sortino      : {r.risk_metrics.sortino:.3f}",
        ]
        if r.primary_benchmark:
            b = r.primary_benchmark
            lines += [
                f"  Alpha vs {b.benchmark_id:4s} : {b.alpha*100:+.2f}%",
                f"  Info Ratio   : {b.information_ratio:.3f}",
            ]
        lines += [
            "",
            "  ─ Attribution ─",
            f"  Best Engine  : {r.attribution.best_engine}",
            f"  Total Alpha  : {r.attribution.total_alpha*100:.2f}bps",
            f"  R²           : {r.attribution.r_squared:.3f}",
            "",
            "  ─ Robustness ─",
            f"  Score        : {r.robustness.robustness_score:.1f}%",
            f"  MC p-value   : {r.monte_carlo.p_value:.3f} "
            f"({'★ 유의' if r.monte_carlo.significant else '비유의'})",
            "",
            "  ─ Engine Health ─",
        ]
        for eng, h in r.engine_health.items():
            lines.append(f"  {eng:15s}: {h.overall:.0f}/100 {h.grade.value} {h.trend}")
        lines += [
            "",
            "  ─ XAI ─",
            f"  {r.xai_summary.overall_narrative}",
            "",
            "  ─ ★ Weight Recommendations (자동 적용 금지) ─",
        ]
        if r.weight_recommendations:
            for rec in r.weight_recommendations[:3]:
                lines.append(
                    f"  {rec.engine}: {rec.current_weight:.1f} → {rec.recommended_weight:.1f} "
                    f"(예상 Sharpe Δ{rec.expected_sharpe_delta:+.4f})"
                )
                lines.append(f"    이유: {rec.reason[:60]}...")
        else:
            lines.append("  Weight 변경 추천 없음 — 현재 설정 적절")
        lines.append("═" * 60)
        return "\n".join(lines)

    # ── Private helpers ────────────────────────────────────────────────

    def _compare_versions(self, recs_a, recs_b, inp: ValidationInput):
        from validation.data_models import VersionComparisonResult
        bt_a = self._backtest.run(recs_a, inp.price_history, inp.initial_capital)
        bt_b = self._backtest.run(recs_b, inp.price_history, inp.initial_capital)
        rm_a = self._risk_calc.calculate(bt_a.daily_returns)
        rm_b = self._risk_calc.calculate(bt_b.daily_returns)
        winner = "A" if rm_a.sharpe >= rm_b.sharpe else "B"
        xai = (f"Version {winner} 우세 — Sharpe {rm_a.sharpe:.3f} vs {rm_b.sharpe:.3f}, "
               f"CAGR {rm_a.cagr*100:.1f}% vs {rm_b.cagr*100:.1f}%")
        return VersionComparisonResult(
            version_a_sharpe=round(rm_a.sharpe, 4),
            version_b_sharpe=round(rm_b.sharpe, 4),
            version_a_cagr  =round(rm_a.cagr, 6),
            version_b_cagr  =round(rm_b.cagr, 6),
            winner=winner,
            delta_sharpe=round(rm_a.sharpe - rm_b.sharpe, 4),
            delta_cagr  =round(rm_a.cagr - rm_b.cagr, 6),
            xai_summary=xai,
        )

    @staticmethod
    def _compute_grade(risk, benchmarks) -> ValidationGrade:
        score = 0.0
        # Sharpe
        score += min(30, risk.sharpe * 15)
        # CAGR
        score += min(25, risk.cagr * 100)
        # MaxDD penalty
        score += max(0, 20 - risk.max_drawdown * 100)
        # Alpha
        if benchmarks:
            score += min(25, benchmarks[0].alpha * 200 + 12)
        else:
            score += 12
        if   score >= 80: return ValidationGrade.A_PLUS
        elif score >= 70: return ValidationGrade.A
        elif score >= 60: return ValidationGrade.B
        elif score >= 50: return ValidationGrade.C
        elif score >= 40: return ValidationGrade.D
        else:             return ValidationGrade.F

    @staticmethod
    def _build_xai_summary(risk, benchmarks, attr, sensitivity) -> XAISummary:
        b = benchmarks[0] if benchmarks else None
        why_spy = (
            f"Alpha {b.alpha*100:+.2f}% 달성 — Beta {b.beta:.2f}로 "
            f"{'시장 대비 초과 성과' if b.alpha > 0 else '시장 대비 부진'}"
        ) if b else "벤치마크 비교 데이터 없음"

        worst_env = f"고변동성 / Recession 국면에서 Sharpe {risk.sharpe:.2f} 수준"
        weight_insight = (
            f"{sensitivity.max_sharpe_engine} Weight 증가 시 Sharpe 최대 개선 가능"
        )
        narrative = (
            f"전략 등급 계산 완료 — CAGR {risk.cagr*100:.1f}% / "
            f"Sharpe {risk.sharpe:.2f} / MaxDD {risk.max_drawdown*100:.1f}%"
        )
        return XAISummary(
            why_outperformed_spy = why_spy,
            best_alpha_engine    = attr.best_engine,
            worst_market_env     = worst_env,
            best_weight_insight  = weight_insight,
            overall_narrative    = narrative,
        )

    @staticmethod
    def _build_narrative(risk, benchmarks, wf, robustness, mc, diag, calibration):
        reasons, warnings = [], []
        if risk.sharpe > 1.0:
            reasons.append(f"Sharpe {risk.sharpe:.2f} — 우수한 위험조정 수익률")
        if risk.cagr > 0.10:
            reasons.append(f"CAGR {risk.cagr*100:.1f}% — 10% 이상 연간 성장")
        if wf.oos_consistent:
            reasons.append(f"WF 안정성 {wf.stability_score:.0f}% — OOS에서도 일관된 성과")
        if mc.significant:
            reasons.append(f"Monte Carlo p={mc.p_value:.3f} — 통계적으로 유의미한 전략")

        if risk.max_drawdown > 0.20:
            warnings.append(f"⚠️ Max Drawdown {risk.max_drawdown*100:.1f}% — 20% 초과 주의")
        if robustness.robustness_score < 60:
            warnings.append(f"⚠️ 안정성 {robustness.robustness_score:.0f}% — 파라미터 과민")
        if calibration.ece > 15:
            warnings.append(f"⚠️ 보정 오류 ECE {calibration.ece:.1f}% — Confidence 신뢰도 재검토")
        if diag.degraded_engines:
            warnings.append(f"⚠️ 성능 저하 Engine: {', '.join(diag.degraded_engines)}")
        if benchmarks and benchmarks[0].alpha < 0:
            warnings.append(f"⚠️ {benchmarks[0].benchmark_id} 대비 Alpha 음수 — 전략 검토 필요")

        return reasons, warnings
