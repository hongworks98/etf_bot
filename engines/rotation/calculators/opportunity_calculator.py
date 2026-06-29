"""
engines/rotation/calculators/opportunity_calculator.py
Opportunity Calculator — scores how valuable it is to rotate INTO this ETF
vs current holdings.
"""
from __future__ import annotations
from typing import Dict
from engines.rotation.calculators.base import AbstractRotationCalculator
from engines.rotation.data_models import CostAnalysis, RotationConfig, RotationInput


class OpportunityCalculator(AbstractRotationCalculator):
    """SRP: Computes opportunity_score and CostAnalysis for each candidate ETF."""

    def calculate(
        self,
        candidate_ticker: str,
        current_holdings: Dict[str, float],   # {ticker: weight}
        rotation_score: float,
        persistence_score: float,
        conviction_score: float,
        inp: RotationInput,
        cfg: RotationConfig,
    ) -> float:
        """
        Opportunity = how much better is this ETF vs best current holding.
        Returns opportunity_score 0~100.
        """
        if not current_holdings:
            # Nothing to compare against — candidate is a pure new addition
            return self.clamp(rotation_score)

        # Best current holding RS score
        best_holding_rs = max(
            inp.get_rs_score(t) for t in current_holdings
        ) if current_holdings else 50.0
        best_holding_persist = max(
            inp.get_persistence_score(t) for t in current_holdings
        ) if current_holdings else 50.0

        candidate_rs   = inp.get_rs_score(candidate_ticker)
        candidate_pers = persistence_score

        rs_gap       = self.clamp(50.0 + (candidate_rs - best_holding_rs))
        pers_gap     = self.clamp(50.0 + (candidate_pers - best_holding_persist))
        conviction_n = self.clamp(conviction_score)

        # Cost adjustment (higher cost → lower opportunity)
        cost_pct     = cfg.default_spread_pct + cfg.slippage_pct
        cost_penalty = self.clamp(100.0 - cost_pct * 10_000.0)

        ow = cfg.opp_weights
        score = (
            rs_gap       * ow.get("rs_gap",         0.40) +
            conviction_n * ow.get("conviction_gap",  0.30) +
            pers_gap     * ow.get("persistence_gap", 0.20) +
            cost_penalty * ow.get("cost_adj",        0.10)
        )
        return self.clamp(score)

    def build_cost_analysis(
        self,
        from_ticker: str,
        to_ticker: str,
        opportunity_score: float,
        current_score: float,
        inp: RotationInput,
        cfg: RotationConfig,
    ) -> CostAnalysis:
        """Compute trade cost and net benefit of rotating from→to."""
        pos_size     = inp.current_holdings.get(from_ticker, 0.10) * inp.portfolio_value
        tx_cost      = pos_size * cfg.default_spread_pct * 2.0     # round-trip
        slippage     = pos_size * cfg.slippage_pct
        tax_impact   = 0.0   # simplified: assume no unrealized gain available
        total_cost   = tx_cost + slippage + tax_impact
        total_pct    = total_cost / pos_size if pos_size > 0 else 0.0

        alpha_daily  = (opportunity_score - current_score) / 100.0 * 0.001  # rough
        net_benefit  = (opportunity_score - current_score) - total_pct * 100.0
        breakeven    = int(total_pct / cfg.daily_alpha_est) if cfg.daily_alpha_est > 0 else 999

        return CostAnalysis(
            from_ticker=from_ticker,
            to_ticker=to_ticker,
            transaction_cost=round(tx_cost, 2),
            slippage_est=round(slippage, 2),
            tax_impact=round(tax_impact, 2),
            total_cost_pct=round(total_pct, 6),
            net_benefit=round(net_benefit, 2),
            breakeven_days=min(breakeven, 9999),
            is_worth_rotating=net_benefit > 0,
        )
