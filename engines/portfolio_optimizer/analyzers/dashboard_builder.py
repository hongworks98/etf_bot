"""
engines/portfolio_optimizer/analyzers/dashboard_builder.py
Generates all 8 DashboardData payloads for PortfolioOptimizationResult.
"""
from __future__ import annotations
from typing import Dict, List

from engines.portfolio_optimizer.calculators.base import AbstractOptimizationCalculator
from engines.portfolio_optimizer.data_models import (
    AllocationRegime, AllocationResult, DashboardData,
    DiversificationGrade, OptimizationConfig, RiskBudget, ScenarioResult,
)


class DashboardBuilder(AbstractOptimizationCalculator):

    def build(
        self,
        current: Dict[str, float],
        target: Dict[str, float],
        cash_pct: float,
        regime: AllocationRegime,
        ticker_results: Dict[str, AllocationResult],
        risk_budget: Dict[str, RiskBudget],
        corr_matrix: Dict[str, Dict[str, float]],
        div_score: float,
        div_grade: DiversificationGrade,
        scenario_results: Dict[str, ScenarioResult],
        sector_exposure: Dict[str, float],
        cfg: OptimizationConfig,
    ) -> DashboardData:
        dd = DashboardData()
        colors = cfg.__dict__.get("dashboard_colors", {})

        # 1. Current Allocation (pie)
        dd.current_allocation = [
            {"ticker": t, "weight": round(w * 100, 2), "label": f"{t} {w:.1%}"}
            for t, w in sorted(current.items(), key=lambda x: x[1], reverse=True)
        ] + [{"ticker": "CASH", "weight": round((1.0 - sum(current.values())) * 100, 2), "label": "CASH"}]

        # 2. Target Allocation (pie)
        dd.target_allocation = [
            {"ticker": t, "weight": round(w * 100, 2), "label": f"{t} {w:.1%}",
             "delta": round((w - current.get(t, 0.0)) * 100, 2)}
            for t, w in sorted(target.items(), key=lambda x: x[1], reverse=True)
        ] + [{"ticker": "CASH", "weight": round(cash_pct * 100, 2), "label": f"CASH {cash_pct:.1%}", "delta": 0.0}]

        # 3. Allocation Wheel (donut: current outer, target inner)
        dd.allocation_wheel = [
            {
                "ticker": t,
                "current_weight": round(current.get(t, 0.0) * 100, 2),
                "target_weight":  round(target.get(t, 0.0) * 100, 2),
                "signal_score":   round(ticker_results[t].signal_score if t in ticker_results else 50.0, 1),
            }
            for t in target
        ]

        # 4. Sector Exposure (bar chart)
        dd.sector_exposure = [
            {"sector": s, "exposure_pct": round(exp * 100, 2)}
            for s, exp in sorted(sector_exposure.items(), key=lambda x: x[1], reverse=True)
        ]

        # 5. Correlation Matrix (heat grid)
        tickers = list(corr_matrix.keys())
        dd.correlation_matrix = [
            {
                "row": ti,
                "col": tj,
                "value": round(corr_matrix[ti][tj], 3),
                "color": _corr_color(corr_matrix[ti][tj]),
            }
            for ti in tickers
            for tj in tickers
        ]

        # 6. Risk Budget (stacked bar)
        dd.risk_budget = [
            {
                "ticker": t,
                "weight_pct": round(rb.weight * 100, 2),
                "risk_pct":   round(rb.risk_pct, 2),
                "target_pct": round(rb.target_risk_pct, 2),
                "overshoot":  round(rb.risk_overshoot, 2),
            }
            for t, rb in sorted(risk_budget.items(), key=lambda x: x[1].risk_pct, reverse=True)
        ]

        # 7. Diversification Gauge
        dd.diversification_gauge = {
            "score": round(div_score, 1),
            "grade": div_grade.value,
            "regime": regime.value,
            "bands": [
                {"label": "Excellent", "min": 80, "max": 100, "color": "#27AE60"},
                {"label": "Good",      "min": 60, "max":  80, "color": "#2ECC71"},
                {"label": "Fair",      "min": 40, "max":  60, "color": "#F39C12"},
                {"label": "Poor",      "min": 20, "max":  40, "color": "#E74C3C"},
                {"label": "Critical",  "min":  0, "max":  20, "color": "#8B0000"},
            ],
        }

        # 8. Scenario Comparison (grouped bar)
        dd.scenario_comparison = [
            {
                "scenario": name,
                "expected_return": round(sc.expected_return_est * 100, 2),
                "expected_vol":    round(sc.expected_risk_est * 100, 2),
                "sharpe":          round(sc.sharpe_est, 3),
                "cash_pct":        round(sc.cash_pct * 100, 2),
            }
            for name, sc in scenario_results.items()
        ]

        return dd


def _corr_color(c: float) -> str:
    """Return hex color for correlation heat cell."""
    if c >= 0.9:
        return "#8B0000"
    if c >= 0.7:
        return "#E74C3C"
    if c >= 0.4:
        return "#F39C12"
    if c >= 0.0:
        return "#27AE60"
    return "#2980B9"   # negative corr = blue (diversifying)
