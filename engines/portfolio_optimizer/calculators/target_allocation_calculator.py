"""
engines/portfolio_optimizer/calculators/target_allocation_calculator.py
Converts signal scores + regime template → constrained target weights.
"""
from __future__ import annotations
from typing import Dict, List, Tuple

from engines.portfolio_optimizer.calculators.base import AbstractOptimizationCalculator
from engines.portfolio_optimizer.data_models import (
    AllocationRegime, OptimizationConfig, OptimizationInput,
)


class TargetAllocationCalculator(AbstractOptimizationCalculator):
    """
    4-step allocation:
    1. Compute signal_score per ETF (0~100)
    2. Get regime base weight from template
    3. Apply signal adjustment (±max_adj % of base)
    4. Constrain + renormalize to (1 − cash_pct)
    """

    def calculate(
        self,
        tickers: List[str],
        inp: OptimizationInput,
        regime: AllocationRegime,
        cash_pct: float,
        cfg: OptimizationConfig,
    ) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, float]]:
        """
        Returns:
          target_weights: Dict[str, float]  (sum ≈ 1 - cash_pct)
          signal_scores:  Dict[str, float]
          base_weights:   Dict[str, float]
        """
        template = cfg.regime_templates.get(regime.value, {})
        cyclical  = set(cfg.sector_categories.get("cyclical", []))
        defensive = set(cfg.sector_categories.get("defensive", []))

        signal_scores: Dict[str, float] = {}
        base_weights: Dict[str, float]  = {}
        raw_weights: Dict[str, float]   = {}

        for t in tickers:
            # ── Signal score ──────────────────────────────────────────
            rs       = inp.get_rs_score(t)
            rotation = inp.get_rotation_score(t)
            conv     = inp.get_conviction_score(t)
            breadth  = inp.breadth_score

            # Macro alignment score
            leaders = cfg.expected_leaders.get(inp.macro_state, [])
            if t in leaders:
                macro_s = cfg.aligned_strong if rs >= 60 else cfg.aligned_neutral
            elif inp.macro_state in ("Unknown",):
                macro_s = cfg.unknown_macro
            else:
                macro_s = cfg.misaligned_strong if rs >= 60 else cfg.misaligned_neutral

            sig = (
                rs       * cfg.w_rs       +
                rotation * cfg.w_rotation +
                conv     * cfg.w_conviction +
                macro_s  * cfg.w_macro    +
                breadth  * cfg.w_breadth
            )
            signal_scores[t] = self.clamp(sig, 0.0, 100.0)

            # ── Base weight from regime template ──────────────────────
            if t in template:
                base = template[t]
            elif t in cyclical:
                base = template.get("default_cyclical", 0.08)
            elif t in defensive:
                base = template.get("default_defensive", 0.08)
            else:
                base = template.get("default_unknown", 0.08)
            base_weights[t] = base

            # ── Signal adjustment ─────────────────────────────────────
            adj_factor = (signal_scores[t] - 50.0) / 50.0 * cfg.max_signal_adj_pct
            raw_weights[t] = max(0.0, base * (1.0 + adj_factor))

        # ── Constraint: clamp each weight ─────────────────────────────
        clamped = {
            t: self.clamp(raw_weights[t], cfg.min_weight, cfg.max_weight)
            for t in tickers
        }

        # ── Normalize to (1 - cash_pct) ───────────────────────────────
        total = sum(clamped.values())
        invest_budget = 1.0 - cash_pct
        if total > 1e-9:
            target_weights = {
                t: round(clamped[t] / total * invest_budget, 6)
                for t in tickers
            }
        else:
            eq = invest_budget / len(tickers) if tickers else 0.0
            target_weights = {t: round(eq, 6) for t in tickers}

        return target_weights, signal_scores, base_weights
