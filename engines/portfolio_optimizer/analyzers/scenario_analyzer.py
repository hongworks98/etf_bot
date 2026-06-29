"""
engines/portfolio_optimizer/analyzers/scenario_analyzer.py
Computes Base / Bull / Bear scenario allocations.
"""
from __future__ import annotations
import copy
from dataclasses import replace
from typing import Dict, List

from engines.portfolio_optimizer.calculators.base import AbstractOptimizationCalculator
from engines.portfolio_optimizer.calculators.target_allocation_calculator import TargetAllocationCalculator
from engines.portfolio_optimizer.calculators.cash_calculator import CashCalculator
from engines.portfolio_optimizer.analyzers.dynamic_regime_engine import DynamicRegimeEngine
from engines.portfolio_optimizer.data_models import (
    AllocationRegime, OptimizationConfig, OptimizationInput,
    OptimizationConfig, ScenarioResult,
)


class _ScenarioInput(OptimizationInput):
    """Thin wrapper that overrides signal scores by applying shocks."""

    def __init__(self, base: OptimizationInput, shock: Dict[str, float]) -> None:
        super().__init__(
            portfolio_state  = base.portfolio_state,
            decision_results = base.decision_results,
            rotation_results = base.rotation_results,
            rs_results       = base.rs_results,
            macro_state      = base.macro_state,
            macro_score      = base.macro_score,
            macro_direction  = base.macro_direction,
            breadth_score    = max(0.0, min(100.0, base.breadth_score + shock.get("breadth", 0.0))),
            breadth_health   = base.breadth_health,
            market_health_score = base.market_health_score,
            aux_data         = base.aux_data,
        )
        self._base = base
        self._rs_shock  = shock.get("rs", 0.0)
        self._rot_shock = shock.get("rotation", 0.0)
        self._vix_delta = shock.get("vix", 0.0)

    def get_rs_score(self, ticker: str) -> float:
        return max(0.0, min(100.0, self._base.get_rs_score(ticker) + self._rs_shock))

    def get_rotation_score(self, ticker: str) -> float:
        return max(0.0, min(100.0, self._base.get_rotation_score(ticker) + self._rot_shock))

    def get_conviction_score(self, ticker: str) -> float:
        return max(0.0, min(100.0, self._base.get_conviction_score(ticker) + self._rot_shock * 0.5))

    def latest_vix(self) -> float:
        return max(10.0, self._base.latest_vix() + self._vix_delta)


class ScenarioAnalyzer(AbstractOptimizationCalculator):
    """Applies shocks to signals and recomputes allocations for each scenario."""

    def __init__(self) -> None:
        self._alloc  = TargetAllocationCalculator()
        self._cash   = CashCalculator()
        self._regime = DynamicRegimeEngine()

    def analyze(
        self,
        inp: OptimizationInput,
        base_regime: AllocationRegime,
        cfg: OptimizationConfig,
    ) -> Dict[str, ScenarioResult]:
        results: Dict[str, ScenarioResult] = {}
        for name, shock in cfg.scenario_shocks.items():
            sc_inp = _ScenarioInput(inp, shock)
            regime, _ = self._regime.detect(sc_inp, cfg)
            cash_pct  = self._cash.calculate(sc_inp, cfg)
            weights, _, _ = self._alloc.calculate(
                inp.tickers, sc_inp, regime, cash_pct, cfg
            )

            # Estimate return/risk from regime + premium
            ann_premium = shock.get("return_premium", 0.0)
            regime_base_return = {
                AllocationRegime.AGGRESSIVE: 0.10,
                AllocationRegime.BALANCED:   0.07,
                AllocationRegime.DEFENSIVE:  0.04,
            }[regime]
            exp_return = regime_base_return + ann_premium

            # Rough vol estimate
            regime_vol = {
                AllocationRegime.AGGRESSIVE: 0.18,
                AllocationRegime.BALANCED:   0.13,
                AllocationRegime.DEFENSIVE:  0.08,
            }[regime]
            vix_factor = sc_inp.latest_vix() / 20.0
            exp_vol = regime_vol * vix_factor

            sharpe = (exp_return - cfg.risk_free_rate) / max(exp_vol, 0.01)

            results[name] = ScenarioResult(
                name=name,
                target_allocation=weights,
                expected_return_est=round(exp_return, 4),
                expected_risk_est=round(exp_vol, 4),
                sharpe_est=round(sharpe, 3),
                max_weight=round(max(weights.values(), default=0.0), 4),
                min_weight=round(min(weights.values(), default=0.0), 4),
                cash_pct=round(cash_pct, 4),
                summary=(
                    f"{name}: 예상수익={exp_return:.1%}, 예상변동성={exp_vol:.1%}, "
                    f"Sharpe={sharpe:.2f}, 현금={cash_pct:.1%}"
                ),
            )
        return results
