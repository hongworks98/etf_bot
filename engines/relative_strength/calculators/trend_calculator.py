"""
engines/relative_strength/calculators/trend_calculator.py
RS Trend Calculator — slope + acceleration of relative strength over time.
"""
from __future__ import annotations

from typing import List, Tuple

from engines.relative_strength.calculators.base import AbstractRSCalculator
from engines.relative_strength.data_models import (
    PriceHistory, RSConfig, RSContribution, RSTrend, RSTrendDir,
)


class RSTrendCalculator(AbstractRSCalculator):
    """
    SRP: Responsible solely for RS trend/slope/acceleration.
    Method:
      1. Build daily RS series = ETF_price / SPY_price  (ratio)
      2. OLS slope over 1M window  → slope_1m
      3. OLS slope over 3M window  → slope_3m
      4. acceleration = slope_1m - slope_3m
      5. trend_score  = normalize(slope, lo, hi) blended with acceleration
    """

    def _rs_ratio_series(self, etf: PriceHistory, spy: PriceHistory) -> List[float]:
        """Daily ETF/SPY price ratio series (older first)."""
        n = min(len(etf.prices), len(spy.prices))
        ratios: List[float] = []
        for i in range(n):
            ratios.append(etf.prices[-n + i] / spy.prices[-n + i]
                          if spy.prices[-n + i] != 0 else 1.0)
        return ratios

    def calculate(
        self,
        etf: PriceHistory,
        spy: PriceHistory,
        config: RSConfig,
    ) -> Tuple[RSTrend, List[RSContribution]]:
        ratios = self._rs_ratio_series(etf, spy)

        slope_1m = self.linear_slope(ratios, config.slope_window_1m)
        slope_3m = self.linear_slope(ratios, config.slope_window_3m)
        acceleration = slope_1m - slope_3m

        # Composite slope: blend dominant (3M) with acceleration
        blend_slope = slope_1m * (1 - config.acceleration_weight) + acceleration * config.acceleration_weight
        norm_slope  = self.normalize(blend_slope, config.slope_normalize_lo, config.slope_normalize_hi)
        trend_score = self.clamp(norm_slope)

        # Direction
        if slope_1m >= config.direction_rising_threshold:
            direction = RSTrendDir.RISING
        elif slope_1m <= config.direction_falling_threshold:
            direction = RSTrendDir.FALLING
        else:
            direction = RSTrendDir.FLAT

        trend = RSTrend(
            direction=direction,
            slope=round(blend_slope, 6),
            acceleration=round(acceleration, 6),
            trend_score=round(trend_score, 2),
            slope_1m=round(slope_1m, 6),
            slope_3m=round(slope_3m, 6),
        )

        contributions = [
            self.make_contribution(
                factor="rs_slope_1m",
                raw_value=slope_1m,
                weight=0.70,
                normalized_value=self.normalize(slope_1m, config.slope_normalize_lo, config.slope_normalize_hi),
                pos_msg=f"Short-term RS slope rising ({slope_1m:+.4f}/day)",
                neg_msg=f"Short-term RS slope falling ({slope_1m:+.4f}/day)",
                neu_msg=f"Short-term RS slope flat ({slope_1m:+.4f}/day)",
            ),
            self.make_contribution(
                factor="rs_acceleration",
                raw_value=acceleration,
                weight=0.30,
                normalized_value=self.normalize(acceleration, config.slope_normalize_lo, config.slope_normalize_hi),
                pos_msg=f"RS momentum accelerating ({acceleration:+.4f})",
                neg_msg=f"RS momentum decelerating ({acceleration:+.4f})",
                neu_msg=f"RS momentum stable ({acceleration:+.4f})",
            ),
        ]
        return trend, contributions
