"""
engines/relative_strength/analyzers/rotation_readiness.py
Rotation Readiness Analyzer — 0~100 score for how ready a sector is to rotate into.
"""
from __future__ import annotations

from engines.relative_strength.calculators.base import AbstractRSCalculator
from engines.relative_strength.data_models import RSConfig, RSRankInfo, RSTrend


class RotationReadinessAnalyzer(AbstractRSCalculator):
    """
    SRP: Responsible solely for computing rotation readiness.
    Formula:
      rank_momentum  = normalize(rank_change, -5, 5)
      trend_accel    = normalize(acceleration, -2, 2)
      persistence_d  = normalize(persistence_delta, -10, 10)
      breadth_bonus  = (breadth_score - 50) * breadth_sensitivity
      result         = weighted sum, clamped 0~100
    """

    def compute(
        self,
        rank_info: RSRankInfo,
        trend: RSTrend,
        persistence_score: float,
        previous_persistence: float,
        breadth_score: float,
        config: RSConfig,
    ) -> float:
        """
        Args:
            rank_info            : current RSRankInfo
            trend                : RSTrend with acceleration
            persistence_score    : current 0~100
            previous_persistence : last period's persistence score (0 if none)
            breadth_score        : from BreadthResult (0~100)
            config               : RSConfig
        Returns:
            rotation_readiness : 0~100
        """
        rw = config.rr_weights

        # 1. Rank momentum (higher rank_change = improving rank = positive)
        rank_momentum = self.normalize(
            rank_info.rank_change,
            config.rr_rank_mom_lo,
            config.rr_rank_mom_hi,
        )

        # 2. Trend acceleration
        trend_accel = self.normalize(
            trend.acceleration,
            config.rr_accel_lo,
            config.rr_accel_hi,
        )

        # 3. Persistence delta (this period vs last)
        persistence_delta = persistence_score - previous_persistence
        persist_d = self.normalize(
            persistence_delta,
            config.rr_persist_lo,
            config.rr_persist_hi,
        )

        # 4. Breadth bonus/penalty — centred at 50
        breadth_bonus = (breadth_score - 50.0) * config.breadth_sensitivity

        raw = (
            rank_momentum * rw.get("rank_momentum", 0.35) +
            trend_accel   * rw.get("trend_accel",   0.30) +
            persist_d     * rw.get("persistence_d", 0.20) +
            breadth_bonus * rw.get("breadth_bonus", 0.15)   # already scaled
        )
        return self.clamp(raw)
