"""
engines/rotation/calculators/conviction_calculator.py
Conviction Engine — the core of RotationSignalEngine.
Conviction Score 0~100 with 5-level classification.
"""
from __future__ import annotations
from engines.rotation.calculators.base import AbstractRotationCalculator
from engines.rotation.data_models import (
    ConvictionLevel, RotationConfig, RotationStage, RotationTiming,
)


class ConvictionCalculator(AbstractRotationCalculator):
    """
    SRP: Computes conviction_score and ConvictionLevel.
    Inputs: rotation_score, confidence, lifecycle stage, opportunity, timing.
    """

    def calculate(
        self,
        rotation_score: float,
        confidence: float,
        stage: RotationStage,
        opportunity_score: float,
        timing: RotationTiming,
        cfg: RotationConfig,
    ) -> tuple[float, ConvictionLevel]:
        """
        Returns:
            conviction_score : 0~100
            conviction_level : ConvictionLevel enum
        """
        lifecycle_bonus = cfg.lifecycle_bonus.get(stage.value, 50.0)
        timing_factor   = cfg.timing_scores.get(timing.value, 20.0)

        cw = cfg.conviction_weights
        raw = (
            rotation_score   * cw.get("rotation_score", 0.30) +
            confidence       * cw.get("confidence",     0.25) +
            lifecycle_bonus  * cw.get("lifecycle",      0.20) +
            opportunity_score* cw.get("opportunity",    0.15) +
            timing_factor    * cw.get("timing",         0.10)
        )
        conviction_score = self.clamp(raw)

        if conviction_score >= cfg.immediate_threshold:
            level = ConvictionLevel.IMMEDIATE_ROTATION
        elif conviction_score >= cfg.gradual_threshold:
            level = ConvictionLevel.GRADUAL_ROTATION
        elif conviction_score >= cfg.watchlist_threshold:
            level = ConvictionLevel.WATCHLIST
        elif conviction_score >= cfg.observe_threshold:
            level = ConvictionLevel.OBSERVE
        else:
            level = ConvictionLevel.NO_ROTATION

        return round(conviction_score, 2), level
