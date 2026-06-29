"""Portfolio Optimization Engine Adapter"""
from __future__ import annotations
from typing import Any, Dict
from dss_integration.adapters.base_adapter import AbstractEngineAdapter
from dss_integration.data.base_loader import RawMarketData


class OptimizerAdapter(AbstractEngineAdapter):
    def adapt(self, raw: RawMarketData, prev: Dict[str, Any]) -> Any:
        return {"raw": raw, **{k: prev.get(k) for k in
                ["macro_result","breadth_result","rs_result",
                 "rotation_result","portfolio_decision_result"]}}

    @staticmethod
    def synthetic_result(raw: RawMarketData, prev: Dict[str, Any]) -> Any:
        """dashboard/demo_factory의 FakePortResult 재사용."""
        import sys, os
        sys.path.insert(0, os.path.join(
            os.path.dirname(__file__), '..', '..', '..'))
        try:
            from dashboard.demo_factory import create_demo_data
            _, _, _, _, port_result, _ = create_demo_data()
            return port_result
        except Exception:
            from types import SimpleNamespace
            n = len(raw.tickers)
            w = {t: 0.95/n for t in raw.tickers}
            class _V:
                value = "Aggressive"
            return SimpleNamespace(
                target_allocation=w,
                current_allocation=w,
                delta_allocation={t: 0.0 for t in raw.tickers},
                cash_recommendation=0.05,
                regime=_V(),
                regime_explanation="Expansion 국면",
                diversification_score=72.0,
                concentration_risk=22.0,
                monte_carlo=SimpleNamespace(
                    p5=0.88, p25=0.95, p50=1.08, p75=1.22, p95=1.45,
                    var_5pct=-0.12, cvar_5pct=-0.17,
                    expected_annual_return=0.08, expected_annual_vol=0.14,
                ),
                ticker_results={t: SimpleNamespace(signal_score=60.0) for t in raw.tickers},
                rebalance_signal=SimpleNamespace(
                    urgency=SimpleNamespace(value="This Week"), max_delta=0.07),
                suggested_trades=[],
                reasons=["Expansion 국면 유지"],
                warnings=[],
            )
