"""
engines/portfolio_optimizer/calculators/position_sizing_calculator.py
Converts weight fractions to $ position values and estimated share counts.
"""
from __future__ import annotations
from typing import Dict, List, Tuple

from engines.portfolio_optimizer.calculators.base import AbstractOptimizationCalculator
from engines.portfolio_optimizer.data_models import OptimizationConfig


class PositionSizingCalculator(AbstractOptimizationCalculator):
    """SRP: converts weights -> dollar amounts + share estimates."""

    def calculate(
        self,
        weights: Dict[str, float],
        portfolio_value: float,
        price_history: Dict[str, List[float]],
        cfg: OptimizationConfig,
    ) -> Dict[str, Tuple[float, float]]:
        """Returns Dict[ticker, (position_value, shares_estimate)]"""
        result: Dict[str, Tuple[float, float]] = {}
        for ticker, w in weights.items():
            pos_value = portfolio_value * w
            prices = price_history.get(ticker, [])
            last_price = prices[-1] if prices else cfg.price_fallback
            if last_price <= 0:
                last_price = cfg.price_fallback
            shares = pos_value / last_price
            result[ticker] = (round(pos_value, 2), round(shares, 4))
        return result
