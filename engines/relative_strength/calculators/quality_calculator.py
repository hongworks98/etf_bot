"""
engines/relative_strength/calculators/quality_calculator.py
Quality Calculator — measures signal quality of RS (consistency, vol, participation).
"""
from __future__ import annotations

import math
from typing import List, Tuple

from engines.relative_strength.calculators.base import AbstractRSCalculator
from engines.relative_strength.data_models import (
    PriceHistory, RSConfig, RSContribution, RSQuality,
)


class QualityCalculator(AbstractRSCalculator):
    """
    SRP: Responsible solely for RS quality assessment.
    Components:
      consistency   = 100 - normalize(std(TF_rs_scores), 0, 30)
      volatility    = normalize(SPY_vol / ETF_vol, 0.5, 2.0)
      participation = normalize(adv_vol_ratio_on_up_days, 0.4, 0.7)
      quality_score = weighted composite
    """

    def _consistency(self, tf_rs_scores: List[float], config: RSConfig) -> float:
        """Lower spread across timeframes = more consistent = higher score."""
        if len(tf_rs_scores) < 2:
            return 50.0
        mean = sum(tf_rs_scores) / len(tf_rs_scores)
        variance = sum((s - mean) ** 2 for s in tf_rs_scores) / len(tf_rs_scores)
        std_dev = math.sqrt(variance)
        # Higher std → lower score
        return self.clamp(100.0 - self.normalize(std_dev,
                                                  config.consistency_normalize_lo,
                                                  config.consistency_normalize_hi))

    def _volatility_ratio(self, etf: PriceHistory, spy: PriceHistory, config: RSConfig) -> float:
        """ETF less volatile than SPY → higher quality score.
        ratio = SPY_vol / ETF_vol.  Higher ratio = ETF calmer relative to SPY.
        """
        etf_vol = etf.volatility()
        spy_vol = spy.volatility()
        if etf_vol == 0:
            return 50.0
        ratio = spy_vol / etf_vol
        return self.normalize(ratio, config.volatility_normalize_lo, config.volatility_normalize_hi)

    def _participation(self, etf: PriceHistory, spy: PriceHistory, config: RSConfig) -> float:
        """Volume participation on days when ETF outperforms SPY.
        adv_vol_ratio = ETF_vol on up-days / total ETF_vol (proxy for conviction).
        Requires at least daily prices & volumes.
        """
        if not etf.volumes or not spy.prices or len(etf.prices) < 2:
            return 50.0

        n = min(len(etf.prices), len(spy.prices), len(etf.volumes), 63)
        etf_prices = etf.prices[-n:]
        spy_prices = spy.prices[-n:]
        etf_vols   = etf.volumes[-n:]

        up_vol = 0.0
        total_vol = sum(etf_vols) or 1.0

        for i in range(1, n):
            spy_base = spy_prices[i - 1]
            etf_base = etf_prices[i - 1]
            if spy_base == 0 or etf_base == 0:
                continue
            etf_ret = (etf_prices[i] / etf_base) - 1.0
            spy_ret = (spy_prices[i] / spy_base) - 1.0
            if etf_ret > spy_ret:         # ETF outperformed SPY today
                up_vol += etf_vols[i]

        ratio = up_vol / total_vol if total_vol > 0 else 0.5
        return self.normalize(ratio, config.participation_normalize_lo, config.participation_normalize_hi)

    def calculate(
        self,
        etf: PriceHistory,
        spy: PriceHistory,
        tf_rs_scores: List[float],
        persistence_score: float,
        config: RSConfig,
    ) -> Tuple[RSQuality, List[RSContribution]]:
        """
        Returns:
            quality     : RSQuality dataclass
            contributions : XAI breakdown
        """
        consistency   = self._consistency(tf_rs_scores, config)
        volatility    = self._volatility_ratio(etf, spy, config)
        participation = self._participation(etf, spy, config)

        qw = config.quality_weights
        quality_score = self.clamp(
            consistency   * qw.get("consistency",   0.30) +
            volatility    * qw.get("volatility",    0.25) +
            participation * qw.get("participation", 0.20) +
            persistence_score * qw.get("persistence", 0.25)
        )

        quality = RSQuality(
            consistency=round(consistency, 2),
            volatility=round(volatility, 2),
            participation=round(participation, 2),
            persistence=round(persistence_score, 2),
            quality_score=round(quality_score, 2),
        )

        contributions = [
            self.make_contribution(
                factor="quality_consistency",
                raw_value=round(consistency, 2),
                weight=qw.get("consistency", 0.30),
                normalized_value=consistency,
                pos_msg="RS consistent across all timeframes",
                neg_msg="RS diverges significantly across timeframes",
                neu_msg="RS moderately consistent across timeframes",
            ),
            self.make_contribution(
                factor="quality_volatility",
                raw_value=round(volatility, 2),
                weight=qw.get("volatility", 0.25),
                normalized_value=volatility,
                pos_msg="ETF has lower volatility than SPY",
                neg_msg="ETF is more volatile than SPY",
                neu_msg="ETF volatility similar to SPY",
            ),
            self.make_contribution(
                factor="quality_participation",
                raw_value=round(participation, 2),
                weight=qw.get("participation", 0.20),
                normalized_value=participation,
                pos_msg="Strong volume on outperformance days",
                neg_msg="Weak volume on outperformance days",
                neu_msg="Average volume on outperformance days",
            ),
            self.make_contribution(
                factor="quality_persistence",
                raw_value=round(persistence_score, 2),
                weight=qw.get("persistence", 0.25),
                normalized_value=persistence_score,
                pos_msg="High weekly persistence supports quality",
                neg_msg="Low weekly persistence weakens quality",
                neu_msg="Moderate weekly persistence",
            ),
        ]
        return quality, contributions
