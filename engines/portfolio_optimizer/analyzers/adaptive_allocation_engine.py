"""
engines/portfolio_optimizer/analyzers/adaptive_allocation_engine.py
Fine-tunes weights to reduce risk-budget overshoot via iterative dampening.
"""
from __future__ import annotations
from typing import Dict

from engines.portfolio_optimizer.calculators.base import AbstractOptimizationCalculator
from engines.portfolio_optimizer.calculators.risk_budget_calculator import RiskBudgetCalculator
from engines.portfolio_optimizer.data_models import OptimizationConfig, RiskBudget


class AdaptiveAllocationEngine(AbstractOptimizationCalculator):
    """
    If any ETF has risk_pct > target + max_overshoot:
      Reduce its weight proportionally and redistribute to under-contributors.
    Iterates up to cfg.convergence_iter times.
    """

    def __init__(self) -> None:
        self._risk_calc = RiskBudgetCalculator()

    def adjust(
        self,
        weights: Dict[str, float],
        price_history: Dict[str, List[str]],
        cfg: OptimizationConfig,
    ) -> tuple[Dict[str, float], Dict[str, RiskBudget]]:
        from typing import List
        w = dict(weights)
        tickers = list(w.keys())
        n = len(tickers)
        if n == 0:
            return w, {}

        risk_budgets: Dict[str, RiskBudget] = {}
        for _ in range(cfg.convergence_iter):
            risk_budgets = self._risk_calc.calculate(w, price_history, cfg)
            target_pct   = 100.0 / n
            overweight   = [t for t, rb in risk_budgets.items()
                           if rb.risk_overshoot > cfg.max_risk_overshoot]
            underweight  = [t for t, rb in risk_budgets.items()
                           if rb.risk_overshoot < 0]
            if not overweight:
                break
            # Dampen overweighted positions
            total_freed = 0.0
            for t in overweight:
                reduction = w[t] * 0.05   # reduce by 5%
                w[t] = max(cfg.min_weight, w[t] - reduction)
                total_freed += reduction
            # Redistribute to underweighted
            if underweight and total_freed > 0:
                per = total_freed / len(underweight)
                for t in underweight:
                    w[t] = min(cfg.max_weight, w[t] + per)
            # Renormalize
            total = sum(w.values())
            if total > 1e-9:
                budget = sum(weights.values())   # keep original invest budget
                w = {t: v / total * budget for t, v in w.items()}

        return w, risk_budgets
