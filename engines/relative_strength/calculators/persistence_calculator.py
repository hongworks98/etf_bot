"""
engines/relative_strength/calculators/persistence_calculator.py
Persistence Calculator — measures how consistently ETF outperforms SPY week-over-week.
"""
from __future__ import annotations

from typing import List, Tuple

from engines.relative_strength.calculators.base import AbstractRSCalculator
from engines.relative_strength.data_models import PriceHistory, RSConfig, RSContribution


class PersistenceCalculator(AbstractRSCalculator):
    """
    SRP: Responsible solely for RS persistence measurement.
    Method:
      1. Compute weekly RS = ETF_weekly_return - SPY_weekly_return over last 52 weeks
      2. positive_pct = count(weekly_rs > 0) / total × 100
      3. streak      = consecutive positive-RS weeks counting backward from now
      4. streak_bonus = normalize(streak, 0, 20) → 0~100
      5. persistence_score = positive_pct×w1 + streak_bonus×w2
    """

    def _weekly_relative_returns(
        self, etf: PriceHistory, spy: PriceHistory, weeks: int
    ) -> List[float]:
        """List of (ETF_weekly_ret - SPY_weekly_ret) for the last `weeks` weeks."""
        etf_weekly = etf.rolling_returns(window=5)
        spy_weekly = spy.rolling_returns(window=5)
        n = min(len(etf_weekly), len(spy_weekly), weeks)
        if n <= 0:
            return []
        etf_w = etf_weekly[-n:]
        spy_w = spy_weekly[-n:]
        return [e - s for e, s in zip(etf_w, spy_w)]

    def _streak(self, weekly_rs: List[float]) -> int:
        """Count consecutive positive RS weeks from the most recent."""
        count = 0
        for rs in reversed(weekly_rs):
            if rs > 0:
                count += 1
            else:
                break
        return count

    def calculate(
        self,
        etf: PriceHistory,
        spy: PriceHistory,
        config: RSConfig,
    ) -> Tuple[float, List[RSContribution]]:
        """
        Returns:
            persistence_score : 0~100
            contributions     : XAI breakdown
        """
        weekly_rs = self._weekly_relative_returns(etf, spy, config.weekly_period)
        total = len(weekly_rs)

        if total == 0:
            return 50.0, []

        positive_count = sum(1 for r in weekly_rs if r > 0)
        positive_pct   = positive_count / total * 100.0
        streak         = self._streak(weekly_rs)
        streak_bonus   = self.normalize(streak, config.streak_normalize_lo, config.streak_normalize_hi)

        w_pct    = config.persistence_pos_pct_weight
        w_streak = config.persistence_streak_weight
        persistence_score = self.clamp(positive_pct * w_pct + streak_bonus * w_streak)

        contributions = [
            self.make_contribution(
                factor="persistence_positive_pct",
                raw_value=positive_pct,
                weight=w_pct,
                normalized_value=positive_pct,  # already 0~100
                positive_threshold=60.0,
                negative_threshold=40.0,
                pos_msg=f"Outperformed SPY {positive_pct:.0f}% of weeks ({total}W sample)",
                neg_msg=f"Only outperformed SPY {positive_pct:.0f}% of weeks — weak persistence",
                neu_msg=f"Mixed persistence: outperformed {positive_pct:.0f}% of weeks",
            ),
            self.make_contribution(
                factor="persistence_streak",
                raw_value=float(streak),
                weight=w_streak,
                normalized_value=streak_bonus,
                positive_threshold=50.0,
                negative_threshold=20.0,
                pos_msg=f"On a {streak}-week consecutive outperformance streak",
                neg_msg=f"Only {streak} consecutive positive-RS weeks",
                neu_msg=f"{streak}-week outperformance streak",
            ),
        ]
        return persistence_score, contributions
