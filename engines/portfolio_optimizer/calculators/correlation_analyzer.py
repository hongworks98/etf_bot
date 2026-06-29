"""
engines/portfolio_optimizer/calculators/correlation_analyzer.py
Pearson correlation matrix, diversification score, concentration risk.
"""
from __future__ import annotations
import math
from typing import Dict, List, Tuple

from engines.portfolio_optimizer.calculators.base import AbstractOptimizationCalculator
from engines.portfolio_optimizer.data_models import OptimizationConfig


class CorrelationAnalyzer(AbstractOptimizationCalculator):
    """
    Diversification score = (effective_N / N) × 100
      effective_N = 1 / Σ w_i²  (inverse HHI)
    Concentration risk = HHI × 100  (HHI = Σ w_i²)
    """

    def analyze(
        self,
        weights: Dict[str, float],
        price_history: Dict[str, List[float]],
        cfg: OptimizationConfig,
    ) -> Tuple[Dict[str, Dict[str, float]], float, float, float]:
        """
        Returns:
          corr_matrix: Dict[ticker, Dict[ticker, float]]
          diversification_score: float  (0~100)
          concentration_risk: float     (HHI × 100)
          mean_correlation: float
        """
        tickers = list(weights.keys())
        n = len(tickers)
        if n == 0:
            return {}, 0.0, 100.0, 1.0

        # ── Returns ───────────────────────────────────────────────────
        returns: Dict[str, List[float]] = {}
        for t in tickers:
            prices = price_history.get(t, [])
            if len(prices) >= 2:
                returns[t] = [(prices[i] / prices[i - 1]) - 1.0 for i in range(1, len(prices))]
            else:
                returns[t] = [0.0] * max(cfg.corr_min_history, 20)

        # ── Pearson correlation ───────────────────────────────────────
        def pearson(ra: List[float], rb: List[float]) -> float:
            m = min(len(ra), len(rb), 252)
            if m < 2:
                return 0.0
            a, b = ra[-m:], rb[-m:]
            ma = sum(a) / m
            mb = sum(b) / m
            num = sum((a[i] - ma) * (b[i] - mb) for i in range(m))
            da = math.sqrt(sum((x - ma) ** 2 for x in a))
            db = math.sqrt(sum((x - mb) ** 2 for x in b))
            return num / (da * db) if da * db > 1e-12 else 0.0

        corr: Dict[str, Dict[str, float]] = {}
        off_diag: List[float] = []
        for i, ti in enumerate(tickers):
            corr[ti] = {}
            for j, tj in enumerate(tickers):
                if i == j:
                    corr[ti][tj] = 1.0
                elif tj in corr and ti in corr[tj]:
                    corr[ti][tj] = corr[tj][ti]
                else:
                    c = pearson(returns[ti], returns[tj])
                    corr[ti][tj] = round(c, 4)
                    off_diag.append(abs(c))

        mean_corr = sum(off_diag) / len(off_diag) if off_diag else 0.0

        # ── Diversification score (effective N / N) ───────────────────
        hhi = sum(w ** 2 for w in weights.values())
        eff_n = 1.0 / hhi if hhi > 1e-12 else float(n)
        div_score = self.clamp((eff_n / n) * 100.0, 0.0, 100.0) if n > 0 else 0.0

        # ── Concentration risk ────────────────────────────────────────
        concentration_risk = self.clamp(hhi * 100.0, 0.0, 100.0)

        return corr, round(div_score, 2), round(concentration_risk, 2), round(mean_corr, 4)
