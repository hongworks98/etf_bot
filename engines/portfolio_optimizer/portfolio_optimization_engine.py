"""
engines/portfolio_optimizer/portfolio_optimization_engine.py
PortfolioOptimizationEngine — Main Orchestrator (Decision Layer, Step 6).

4-Phase Pipeline:
  Phase 1: Regime detection + cash + per-ETF signal scores
  Phase 2: Target allocation (raw → constrained → normalized)
  Phase 3: Risk analysis (covariance, diversification, adaptive adjustment)
  Phase 4: Scenarios, Monte Carlo, Rebalancing, XAI, Dashboard
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional

import yaml

from engines.portfolio_optimizer.calculators.cash_calculator import CashCalculator
from engines.portfolio_optimizer.calculators.correlation_analyzer import CorrelationAnalyzer
from engines.portfolio_optimizer.calculators.position_sizing_calculator import PositionSizingCalculator
from engines.portfolio_optimizer.calculators.risk_budget_calculator import RiskBudgetCalculator
from engines.portfolio_optimizer.calculators.target_allocation_calculator import TargetAllocationCalculator
from engines.portfolio_optimizer.analyzers.adaptive_allocation_engine import AdaptiveAllocationEngine
from engines.portfolio_optimizer.analyzers.dashboard_builder import DashboardBuilder
from engines.portfolio_optimizer.analyzers.dynamic_regime_engine import DynamicRegimeEngine
from engines.portfolio_optimizer.analyzers.monte_carlo_simulator import MonteCarloSimulator
from engines.portfolio_optimizer.analyzers.rebalancing_analyzer import RebalancingAnalyzer
from engines.portfolio_optimizer.analyzers.scenario_analyzer import ScenarioAnalyzer
from engines.portfolio_optimizer.data_models import (
    AllocationRegime, AllocationResult, DiversificationGrade,
    OptimizationConfig, OptimizationInput, PortfolioOptimizationResult,
    PortfolioState, RebalanceSignal, TradeDirection,
)


class PortfolioOptimizationEngine:
    """
    Decision Layer Engine: converts multi-engine signals → Target Allocation.
    All weights/constraints externally managed via YAML.
    Sub-components injected via constructor (DIP).
    """

    def __init__(
        self,
        config: OptimizationConfig,
        regime_engine:    Optional[DynamicRegimeEngine]     = None,
        cash_calc:        Optional[CashCalculator]           = None,
        alloc_calc:       Optional[TargetAllocationCalculator] = None,
        risk_calc:        Optional[RiskBudgetCalculator]     = None,
        corr_analyzer:    Optional[CorrelationAnalyzer]      = None,
        pos_calc:         Optional[PositionSizingCalculator] = None,
        adaptive:         Optional[AdaptiveAllocationEngine] = None,
        scenario:         Optional[ScenarioAnalyzer]         = None,
        mc_sim:           Optional[MonteCarloSimulator]      = None,
        rebalance:        Optional[RebalancingAnalyzer]      = None,
        dashboard:        Optional[DashboardBuilder]         = None,
    ) -> None:
        self._cfg      = config
        self._regime   = regime_engine or DynamicRegimeEngine()
        self._cash     = cash_calc     or CashCalculator()
        self._alloc    = alloc_calc    or TargetAllocationCalculator()
        self._risk     = risk_calc     or RiskBudgetCalculator()
        self._corr     = corr_analyzer or CorrelationAnalyzer()
        self._pos      = pos_calc      or PositionSizingCalculator()
        self._adaptive = adaptive      or AdaptiveAllocationEngine()
        self._scenario = scenario      or ScenarioAnalyzer()
        self._mc       = mc_sim        or MonteCarloSimulator()
        self._rebal    = rebalance     or RebalancingAnalyzer()
        self._dash     = dashboard     or DashboardBuilder()

    # ── Factory ──────────────────────────────────────────────────────────

    @classmethod
    def from_yaml(cls, config_path: str = "config/portfolio_weights.yaml") -> "PortfolioOptimizationEngine":
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            cfg = OptimizationConfig.from_dict(raw)
        else:
            cfg = OptimizationConfig()
        return cls(config=cfg)

    # ── Public API ────────────────────────────────────────────────────────

    def optimize(self, inp: OptimizationInput) -> PortfolioOptimizationResult:
        """Full 4-phase portfolio optimization pipeline."""
        tickers = inp.tickers
        if not tickers:
            return PortfolioOptimizationResult()

        ps  = inp.portfolio_state
        cfg = self._cfg

        # ── Phase 1: Regime + Cash + Signal Scores ───────────────────────
        regime, regime_expl = self._regime.detect(inp, cfg)
        cash_pct            = self._cash.calculate(inp, cfg)

        # ── Phase 2: Target Allocation ────────────────────────────────────
        target_w, signal_scores, base_w = self._alloc.calculate(
            tickers, inp, regime, cash_pct, cfg
        )

        # Position sizing
        pos_sizes = self._pos.calculate(
            target_w, ps.portfolio_value, ps.price_history, cfg
        )

        # ── Phase 3: Risk Analysis ─────────────────────────────────────────
        corr_matrix, div_score, conc_risk, mean_corr = self._corr.analyze(
            target_w, ps.price_history, cfg
        )

        # Adaptive adjustment
        adj_target_w, risk_budgets = self._adaptive.adjust(
            target_w, ps.price_history, cfg
        )

        # If no risk budget from adaptive (empty history), compute directly
        if not risk_budgets:
            risk_budgets = self._risk.calculate(adj_target_w, ps.price_history, cfg)

        # Renormalize after adaptive
        total_w = sum(adj_target_w.values())
        invest   = 1.0 - cash_pct
        if total_w > 1e-9:
            adj_target_w = {t: v / total_w * invest for t, v in adj_target_w.items()}

        # Diversification grade
        div_grade = self._diversification_grade(div_score, cfg)

        # ── Phase 4: Scenarios, MC, Rebalancing, XAI, Dashboard ──────────
        scenario_results = self._scenario.analyze(inp, regime, cfg)

        mc_result = self._mc.simulate(adj_target_w, ps.price_history, cfg)

        current_w = {t: ps.current_weight(t) for t in tickers}

        rebal_signal, suggested_trades = self._rebal.analyze(
            current_w, adj_target_w, ps.portfolio_value, ps.price_history, cfg
        )

        delta_w = {
            t: round(adj_target_w.get(t, 0.0) - current_w.get(t, 0.0), 6)
            for t in tickers
        }

        # Sector exposure
        sector_exposure = self._compute_sector_exposure(adj_target_w, cfg)

        # Per-ETF AllocationResult with XAI
        ticker_results: Dict[str, AllocationResult] = {}
        for t in tickers:
            cur  = current_w.get(t, 0.0)
            tgt  = adj_target_w.get(t, 0.0)
            pv, sh = pos_sizes.get(t, (0.0, 0.0))
            rb   = risk_budgets.get(t)
            xai  = self._build_xai(t, tgt, cur, signal_scores.get(t, 50.0),
                                   base_w.get(t, 0.0), rb, inp, regime, cfg)
            ar = AllocationResult(
                ticker=t,
                target_weight=round(tgt, 4),
                current_weight=round(cur, 4),
                signal_score=round(signal_scores.get(t, 50.0), 2),
                regime_base_weight=round(base_w.get(t, 0.0), 4),
                signal_adjustment=round(tgt - base_w.get(t, 0.0), 4),
                risk_contribution=round(rb.risk_pct if rb else 0.0, 2),
                risk_budget_pct=round(rb.target_risk_pct if rb else 100.0/len(tickers), 2),
                position_value=pv,
                shares_estimate=sh,
                xai_explanation=xai,
            )
            ar.delta_weight = round(tgt - cur, 6)
            ar.trade_direction = (
                TradeDirection.BUY if ar.delta_weight > 0.001 else
                TradeDirection.SELL if ar.delta_weight < -0.001 else
                TradeDirection.HOLD
            )
            ticker_results[t] = ar

        # Opportunity cost summary
        opp_cost = {
            "daily_usd":   round(rebal_signal.opportunity_cost_daily, 2),
            "monthly_usd": round(rebal_signal.opportunity_cost_monthly, 2),
            "breakeven_days": rebal_signal.days_to_breakeven,
        }

        # Reasons & warnings
        reasons, warnings = self._build_narrative(
            regime, regime_expl, div_score, div_grade, conc_risk,
            rebal_signal, ticker_results, cfg
        )

        # Dashboard data
        dash = self._dash.build(
            current=current_w,
            target=adj_target_w,
            cash_pct=cash_pct,
            regime=regime,
            ticker_results=ticker_results,
            risk_budget=risk_budgets,
            corr_matrix=corr_matrix,
            div_score=div_score,
            div_grade=div_grade,
            scenario_results=scenario_results,
            sector_exposure=sector_exposure,
            cfg=cfg,
        )

        # XAI summary
        top3 = sorted(ticker_results.items(), key=lambda x: x[1].target_weight, reverse=True)[:3]
        xai_summary = (
            f"[{regime.value} 체제] "
            f"현금 {cash_pct:.1%} | 분산도 {div_score:.0f}/100 ({div_grade.value}) | "
            f"상위 3종목: " +
            ", ".join(f"{t} {r.target_weight:.1%}" for t, r in top3)
        )

        return PortfolioOptimizationResult(
            ticker_results=ticker_results,
            target_allocation={t: round(adj_target_w.get(t, 0.0), 4) for t in tickers},
            current_allocation={t: round(current_w.get(t, 0.0), 4) for t in tickers},
            delta_allocation=delta_w,
            cash_recommendation=round(cash_pct, 4),
            regime=regime,
            regime_explanation=regime_expl,
            risk_budget=risk_budgets,
            diversification_score=div_score,
            diversification_grade=div_grade,
            correlation_matrix=corr_matrix,
            concentration_risk=conc_risk,
            sector_exposure=sector_exposure,
            scenario_results=scenario_results,
            monte_carlo=mc_result,
            suggested_trades=suggested_trades,
            rebalance_signal=rebal_signal,
            opportunity_cost=opp_cost,
            dashboard_data=dash,
            reasons=reasons,
            warnings=warnings,
            xai_summary=xai_summary,
        )

    def explain(self, result: PortfolioOptimizationResult) -> str:
        """Full XAI explanation of optimization result."""
        lines = [
            "═══ Portfolio Optimization Result ═══",
            f"Regime      : {result.regime.value}",
            f"현금 추천   : {result.cash_recommendation:.1%}",
            f"분산도      : {result.diversification_score:.1f}/100 ({result.diversification_grade.value})",
            f"집중위험    : {result.concentration_risk:.1f}/100",
            f"리밸런싱    : {result.rebalance_signal.urgency.value} (최대 이탈 {result.rebalance_signal.max_delta:.1%})",
            "",
            "Target Allocation (상위 순):",
        ]
        for t, w in result.top_positions:
            ar = result.ticker_results.get(t)
            cur = result.current_allocation.get(t, 0.0)
            lines.append(
                f"  {t:6s}: {w:.1%}  (현재 {cur:.1%}, 변화 {w-cur:+.1%})  |  Signal={ar.signal_score:.1f}"
            )
        lines += ["", "XAI 상세:"]
        for t, ar in sorted(result.ticker_results.items(), key=lambda x: x[1].target_weight, reverse=True):
            lines.append(f"  [{t}] {ar.xai_explanation}")
        if result.reasons:
            lines += ["", "주요 신호:"]
            lines.extend(f"  + {r}" for r in result.reasons)
        if result.warnings:
            lines += ["", "경고:"]
            lines.extend(f"  ! {w}" for w in result.warnings)
        if result.monte_carlo:
            mc = result.monte_carlo
            lines += [
                "",
                f"Monte Carlo ({mc.n_simulations}회 × {mc.n_days}일):",
                f"  P5={mc.p5:.3f}  P25={mc.p25:.3f}  P50={mc.p50:.3f}  "
                f"P75={mc.p75:.3f}  P95={mc.p95:.3f}",
                f"  VaR(5%)={mc.var_5pct:.2%}  CVaR={mc.cvar_5pct:.2%}",
            ]
        lines += ["", "Scenario Comparison:"]
        for name, sc in result.scenario_results.items():
            lines.append(f"  {name:5s}: {sc.summary}")
        return "\n".join(lines)

    # ── Private ────────────────────────────────────────────────────────────

    @staticmethod
    def _diversification_grade(score: float, cfg: OptimizationConfig) -> DiversificationGrade:
        if score >= cfg.excellent_threshold:
            return DiversificationGrade.EXCELLENT
        if score >= cfg.good_threshold:
            return DiversificationGrade.GOOD
        if score >= cfg.fair_threshold:
            return DiversificationGrade.FAIR
        if score >= 20.0:
            return DiversificationGrade.POOR
        return DiversificationGrade.CRITICAL

    @staticmethod
    def _compute_sector_exposure(
        weights: Dict[str, float],
        cfg: OptimizationConfig,
    ) -> Dict[str, float]:
        cyclical  = set(cfg.sector_categories.get("cyclical", []))
        defensive = set(cfg.sector_categories.get("defensive", []))
        exp: Dict[str, float] = {"Cyclical": 0.0, "Defensive": 0.0, "Other": 0.0}
        for t, w in weights.items():
            if t in cyclical:
                exp["Cyclical"] += w
            elif t in defensive:
                exp["Defensive"] += w
            else:
                exp["Other"] += w
        return {k: round(v, 4) for k, v in exp.items()}

    @staticmethod
    def _build_xai(
        ticker: str,
        target: float,
        current: float,
        signal_score: float,
        base_weight: float,
        rb,
        inp: OptimizationInput,
        regime: AllocationRegime,
        cfg: OptimizationConfig,
    ) -> str:
        rs  = inp.get_rs_score(ticker)
        rot = inp.get_rotation_score(ticker)
        cv  = inp.get_conviction_score(ticker)
        leaders = cfg.expected_leaders.get(inp.macro_state, [])
        aligned = ticker in leaders
        macro_label = "기대 섹터" if aligned else "비기대 섹터"
        risk_pct = rb.risk_pct if rb else 0.0
        target_rpct = rb.target_risk_pct if rb else 100.0

        return (
            f"{target:.1%} 추천 | "
            f"종합신호 {signal_score:.1f}/100 | "
            f"RS {rs:.1f} / Rotation {rot:.1f} / Conviction {cv:.1f} | "
            f"{inp.macro_state} {macro_label} | "
            f"Regime 기준 {base_weight:.1%}→{target:.1%} ({target-base_weight:+.1%} 조정) | "
            f"리스크 기여도 {risk_pct:.1f}% (목표 {target_rpct:.1f}%) | "
            f"현재 대비 {target-current:+.1%}"
        )

    @staticmethod
    def _build_narrative(
        regime, regime_expl, div_score, div_grade, conc_risk,
        rebal_signal, ticker_results, cfg
    ):
        reasons, warnings = [], []
        reasons.append(regime_expl)

        if div_score >= cfg.good_threshold:
            reasons.append(f"분산도 {div_score:.1f}/100 ({div_grade.value}) — 양호")
        else:
            warnings.append(f"분산도 {div_score:.1f}/100 ({div_grade.value}) — 개선 필요")

        from engines.portfolio_optimizer.data_models import RebalanceUrgency
        if rebal_signal.urgency == RebalanceUrgency.IMMEDIATE:
            warnings.append(f"즉시 리밸런싱 필요: {rebal_signal.reason}")
        elif rebal_signal.urgency == RebalanceUrgency.THIS_WEEK:
            reasons.append(f"이번 주 리밸런싱 권고: {rebal_signal.reason}")

        if conc_risk > cfg.extreme_hhi * 100:
            warnings.append(f"집중위험 극단적 (HHI×100={conc_risk:.1f}) — 최대 단일 비중 점검 필요")
        elif conc_risk > cfg.high_hhi * 100:
            warnings.append(f"집중위험 높음 (HHI×100={conc_risk:.1f})")

        top_ticker, top_ar = max(
            ticker_results.items(), key=lambda x: x[1].target_weight, default=("", None)
        )
        if top_ar and top_ar.target_weight >= cfg.max_weight:
            warnings.append(f"{top_ticker} 최대 허용 비중 ({top_ar.target_weight:.1%}) 도달")

        return reasons, warnings
