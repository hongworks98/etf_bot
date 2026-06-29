"""
engines/portfolio_optimizer/calculators/cash_calculator.py
Recommends cash weight based on macro regime, VIX, health, breadth.
"""
from __future__ import annotations
from engines.portfolio_optimizer.calculators.base import AbstractOptimizationCalculator
from engines.portfolio_optimizer.data_models import OptimizationConfig, OptimizationInput


class CashCalculator(AbstractOptimizationCalculator):
    """
    SRP: only computes cash recommendation.
    Formula:
      cash = base_cash
      + vix_cash_add   if VIX > vix_high
      + macro_cash_add if macro is defensive
      + health_cash_add if health < health_low
      + breadth_cash_add if breadth < breadth_low
      clamped to [cash_min, cash_max]
    """

    def calculate(self, inp: OptimizationInput, cfg: OptimizationConfig) -> float:
        cash = cfg.base_cash
        reasons = []

        vix = inp.latest_vix()
        if vix > cfg.vix_high:
            cash += cfg.vix_cash_add
            reasons.append(f"VIX={vix:.1f}>{cfg.vix_high}")

        if inp.macro_state in cfg.defensive_states:
            cash += cfg.macro_cash_add
            reasons.append(f"Macro={inp.macro_state} (defensive)")

        if inp.market_health_score < cfg.health_low:
            cash += cfg.health_cash_add
            reasons.append(f"Health={inp.market_health_score:.1f}<{cfg.health_low}")

        if inp.breadth_score < cfg.breadth_low:
            cash += cfg.breadth_cash_add
            reasons.append(f"Breadth={inp.breadth_score:.1f}<{cfg.breadth_low}")

        return self.clamp(cash, cfg.cash_min, cfg.cash_max)
