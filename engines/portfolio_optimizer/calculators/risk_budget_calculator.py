"""
engines/portfolio_optimizer/calculators/risk_budget_calculator.py
Computes per-ETF risk contribution from covariance matrix.
"""
from __future__ import annotations
from typing import Dict, List

from engines.portfolio_optimizer.calculators.base import AbstractOptimizationCalculator
from engines.portfolio_optimizer.data_models import OptimizationConfig, RiskBudget


class RiskBudgetCalculator(AbstractOptimizationCalculator):
    """
    Risk contribution formula:
      cov[i,j]         = Cov(returns_i, returns_j)
      (Cov·w)[i]       = Σ_j cov[i,j] × w_j        (marginal risk)
      rc[i]            = w_i × (Cov·w)[i]
      portfolio_var    = Σ_i rc[i]
      risk_pct[i]      = rc[i] / portfolio_var × 100
    """

    def calculate(
        self,
        weights: Dict[str, float],
        price_history: Dict[str, List[float]],
        cfg: OptimizationConfig,
    ) -> Dict[str, RiskBudget]:
        tickers = list(weights.keys())
        n = len(tickers)
        if n == 0:
            return {}

        # ── Daily returns ─────────────────────────────────────────────
        returns: Dict[str, List[float]] = {}
        for t in tickers:
            prices = price_history.get(t, [])
            if len(prices) >= 2:
                returns[t] = [(prices[i] / prices[i - 1]) - 1.0 for i in range(1, len(prices))]
            else:
                returns[t] = []

        # Check if sufficient history
        valid = {t for t in tickers if len(returns[t]) >= cfg.min_history_days}

        # ── Covariance matrix ─────────────────────────────────────────
        def cov_pair(ra: List[float], rb: List[float]) -> float:
            m = min(len(ra), len(rb))
            if m < 2:
                return 0.0
            ma = sum(ra[-m:]) / m
            mb = sum(rb[-m:]) / m
            return sum((ra[-m+i] - ma) * (rb[-m+i] - mb) for i in range(m)) / (m - 1)

        cov = [[0.0] * n for _ in range(n)]
        for i, ti in enumerate(tickers):
            for j, tj in enumerate(tickers):
                if ti in valid and tj in valid:
                    cov[i][j] = cov_pair(returns[ti], returns[tj]) * cfg.annualize_factor
                elif i == j:
                    # Fallback: estimate from std
                    std_i = self.std_dev(returns.get(ti, [])) if returns.get(ti) else 0.02
                    cov[i][j] = (std_i ** 2) * cfg.annualize_factor
                else:
                    cov[i][j] = 0.0

        # ── Marginal risk contribution ────────────────────────────────
        w = [weights.get(t, 0.0) for t in tickers]
        cov_w = [sum(cov[i][j] * w[j] for j in range(n)) for i in range(n)]
        risk_contribs = [w[i] * cov_w[i] for i in range(n)]
        portfolio_var = max(sum(risk_contribs), 1e-12)

        target_pct = 100.0 / n if n > 0 else 0.0

        result: Dict[str, RiskBudget] = {}
        for i, t in enumerate(tickers):
            risk_pct = risk_contribs[i] / portfolio_var * 100.0
            result[t] = RiskBudget(
                ticker=t,
                weight=w[i],
                marginal_risk=cov_w[i],
                risk_contribution=risk_contribs[i],
                risk_pct=round(risk_pct, 2),
                target_risk_pct=round(target_pct, 2),
                risk_overshoot=round(risk_pct - target_pct, 2),
            )
        return result
