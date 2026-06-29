"""
engines/relative_strength/calculators/multi_timeframe.py
Multi-Timeframe RS Calculator — computes RS score per period then composites.
"""
from __future__ import annotations

from typing import List, Tuple

from engines.relative_strength.calculators.base import AbstractRSCalculator
from engines.relative_strength.data_models import (
    PriceHistory, RSConfig, RSContribution, RSTimeframe,
)

_PERIODS = ["1M", "3M", "6M", "12M"]


class MultiTimeframeCalculator(AbstractRSCalculator):
    """
    SRP: Responsible solely for multi-timeframe RS computation.
    For each period: relative_return = ETF_return - SPY_return
                     rs_score_tf = normalize(relative_return, lo, hi)
    composite_rs = weighted sum of rs_score_tf values.
    """

    def calculate(
        self,
        etf: PriceHistory,
        spy: PriceHistory,
        config: RSConfig,
    ) -> Tuple[float, List[RSTimeframe], List[RSContribution]]:
        """
        Returns:
            composite_rs   : 0~100
            timeframes     : per-period breakdown
            contributions  : XAI contributions
        """
        timeframes: List[RSTimeframe] = []
        contributions: List[RSContribution] = []
        composite = 0.0

        for period in _PERIODS:
            weight = config.timeframe_weights.get(period, 0.0)
            if weight == 0.0:
                continue

            etf_ret = etf.total_return(period)
            spy_ret = spy.total_return(period)
            rel_ret = etf_ret - spy_ret
            rs_score_tf = self.normalize(rel_ret, config.tf_normalize_lo, config.tf_normalize_hi)

            timeframes.append(RSTimeframe(
                period=period,
                etf_return=round(etf_ret, 4),
                spy_return=round(spy_ret, 4),
                relative_return=round(rel_ret, 4),
                rs_score=round(rs_score_tf, 2),
            ))

            composite += weight * rs_score_tf
            contributions.append(self.make_contribution(
                factor=f"rs_{period.lower()}",
                raw_value=rel_ret,
                weight=weight,
                normalized_value=rs_score_tf,
                pos_msg=f"{period} outperforming SPY by {rel_ret:+.1f}%",
                neg_msg=f"{period} underperforming SPY by {rel_ret:+.1f}%",
                neu_msg=f"{period} tracking SPY closely ({rel_ret:+.1f}%)",
            ))

        composite = self.clamp(composite)
        return composite, timeframes, contributions
