"""
engines/rotation/calculators/lifecycle_calculator.py
Lifecycle Calculator — 6-stage state machine for Rotation lifecycle.
"""
from __future__ import annotations
import math
from typing import List, Tuple
from engines.rotation.calculators.base import AbstractRotationCalculator
from engines.rotation.data_models import RotationConfig, RotationStage


class LifecycleCalculator(AbstractRotationCalculator):
    """
    SRP: Determines RotationStage from score history.
    State Machine:
      EMERGING  → score low (<45), short history (<5 days above threshold)
      BUILDING  → score mid (45-62), 5-15 active days
      CONFIRMED → score solid (>=62), 15+ days
      MATURE    → score peaked (>=75), plateau or slight decline
      WEAKENING → score dropping from recent peak
      REVERSING → score very low (<30)
    """

    def _active_days(self, history: List[float], threshold: float) -> int:
        """Count consecutive days at end of history where score >= threshold."""
        count = 0
        for s in reversed(history):
            if s >= threshold:
                count += 1
            else:
                break
        return count

    def _recent_peak(self, history: List[float], window: int = 10) -> float:
        """Max score over recent window."""
        if not history:
            return 0.0
        return max(history[-window:])

    def calculate(
        self,
        current_score: float,
        history: List[float],
        previous_stage: str,
        cfg: RotationConfig,
    ) -> Tuple[RotationStage, int, int, float]:
        """
        Returns:
            stage            : RotationStage
            persistence_days : consecutive days above threshold
            persistence_weeks: persistence_days // 5
            stability        : 0~100 (inverse of score variance)
        """
        active_days = self._active_days(history + [current_score],
                                         cfg.persistence_score_threshold)
        recent_peak = self._recent_peak(history + [current_score])

        # Stability = inverse of recent score variance
        if len(history) >= 5:
            recent = (history + [current_score])[-10:]
            std    = self.std_dev(recent)
            stability = self.clamp(100.0 - self.normalize(std, 0.0, 20.0))
        else:
            stability = 50.0

        # State machine
        if current_score < cfg.reversing_threshold:
            stage = RotationStage.REVERSING

        elif previous_stage in ("Mature", "Confirmed", "Weakening") and \
                current_score < recent_peak - cfg.weakening_drop:
            stage = RotationStage.WEAKENING

        elif current_score >= cfg.mature_min_score and active_days >= cfg.confirmed_min_days:
            # Plateau or slight decline from very high level = MATURE
            if len(history) >= 3:
                slope = self.linear_slope(history[-5:] + [current_score], 5)
                stage = RotationStage.MATURE if slope <= 0.5 else RotationStage.CONFIRMED
            else:
                stage = RotationStage.MATURE

        elif current_score >= cfg.confirmed_min_score and active_days >= cfg.confirmed_min_days:
            stage = RotationStage.CONFIRMED

        elif current_score >= cfg.building_max_score or \
                (current_score >= cfg.emerging_max_score and active_days >= cfg.emerging_max_days):
            stage = RotationStage.BUILDING

        else:
            stage = RotationStage.EMERGING

        persistence_weeks = active_days // 5
        return stage, active_days, persistence_weeks, round(stability, 2)
