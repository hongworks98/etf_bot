"""
engines/portfolio_optimizer/analyzers/monte_carlo_simulator.py
Monte Carlo simulation: N paths × T days using historical return distribution.
"""
from __future__ import annotations
import math
import random
from typing import Dict, List, Optional

from engines.portfolio_optimizer.calculators.base import AbstractOptimizationCalculator
from engines.portfolio_optimizer.data_models import MonteCarloResult, OptimizationConfig


class MonteCarloSimulator(AbstractOptimizationCalculator):
    """
    Simplified MC (no Cholesky for portability — independent normal draws).
    Each simulation:
      for t in range(n_days):
        r_i ~ N(mu_i, sigma_i)
        portfolio_r = Σ w_i × r_i
      final_value = Π (1 + portfolio_r_t)
    """

    def simulate(
        self,
        weights: Dict[str, float],
        price_history: Dict[str, List[float]],
        cfg: OptimizationConfig,
        seed: Optional[int] = 42,
    ) -> Optional[MonteCarloResult]:
        tickers = [t for t in weights if weights[t] > 0]
        if not tickers:
            return None

        # Build per-ETF return stats
        mus: List[float]    = []
        sigmas: List[float] = []
        ws: List[float]     = []

        for t in tickers:
            prices = price_history.get(t, [])
            if len(prices) >= cfg.mc_min_history:
                rets = [(prices[i]/prices[i-1]) - 1.0 for i in range(1, len(prices))]
            else:
                rets = [0.0004]  # fallback: ~10% annual

            mu    = sum(rets) / len(rets)
            var   = sum((r - mu)**2 for r in rets) / max(len(rets)-1, 1)
            sigma = math.sqrt(var)
            mus.append(mu)
            sigmas.append(max(sigma, 0.003))  # floor 0.3%/day
            ws.append(weights[t])

        n_sims = cfg.mc_n_simulations
        n_days = cfg.mc_n_days
        rng    = random.Random(seed)

        final_vals: List[float] = []
        for _ in range(n_sims):
            port_val = 1.0
            for _ in range(n_days):
                # Box-Muller for normal draws
                port_r = 0.0
                for i in range(len(tickers)):
                    u1 = max(rng.random(), 1e-15)
                    u2 = rng.random()
                    z  = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
                    r  = mus[i] + sigmas[i] * z
                    port_r += ws[i] * r
                port_val *= (1.0 + port_r)
            final_vals.append(port_val)

        final_vals.sort()
        n = len(final_vals)

        def pct(p: float) -> float:
            idx = int(p / 100 * n)
            return final_vals[min(idx, n-1)]

        var_5  = pct(5)  - 1.0
        below5 = [v - 1.0 for v in final_vals if v <= pct(5)]
        cvar   = sum(below5) / len(below5) if below5 else var_5

        # Annualized stats
        mu_port    = sum(m * w for m, w in zip(mus, ws))
        sigma_port = math.sqrt(sum(s**2 * w**2 for s, w in zip(sigmas, ws)))

        return MonteCarloResult(
            n_simulations=n_sims,
            n_days=n_days,
            p5 =round(pct(5),  4),
            p25=round(pct(25), 4),
            p50=round(pct(50), 4),
            p75=round(pct(75), 4),
            p95=round(pct(95), 4),
            var_5pct =round(var_5, 4),
            cvar_5pct=round(cvar, 4),
            expected_annual_return=round(mu_port * 252, 4),
            expected_annual_vol   =round(sigma_port * math.sqrt(252), 4),
        )
