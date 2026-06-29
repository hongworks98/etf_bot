"""
engines/rotation/analyzers/rotation_timing.py
Rotation Timing Analyzer — recommends NOW / THIS_WEEK / THIS_MONTH / WAIT.
"""
from __future__ import annotations
from engines.rotation.data_models import (
    ConvictionLevel, RotationConfig, RotationStage, RotationTiming,
)

_STAGE_ORDER = {
    RotationStage.EMERGING:  0,
    RotationStage.BUILDING:  1,
    RotationStage.CONFIRMED: 2,
    RotationStage.MATURE:    3,
    RotationStage.WEAKENING: 4,
    RotationStage.REVERSING: 5,
}


class RotationTimingAnalyzer:
    """
    SRP: Determines optimal action timing from conviction, stage, and forecast.
    Rules (priority order):
      NOW        : conviction >= 75 AND stage >= CONFIRMED AND not WEAKENING/REVERSING
      THIS_WEEK  : conviction >= 60 AND stage >= BUILDING
      THIS_MONTH : forecast >= 60 (even if conviction is lower)
      WAIT       : everything else
    """

    def determine(
        self,
        conviction_score: float,
        conviction_level: ConvictionLevel,
        stage: RotationStage,
        forecast: float,
        is_false_rotation: bool,
        cfg: RotationConfig,
    ) -> RotationTiming:
        if is_false_rotation:
            return RotationTiming.WAIT

        stage_rank = _STAGE_ORDER.get(stage, 0)
        confirmed_rank = _STAGE_ORDER[RotationStage.CONFIRMED]
        building_rank  = _STAGE_ORDER[RotationStage.BUILDING]

        is_declining = stage in {RotationStage.WEAKENING, RotationStage.REVERSING}

        if (conviction_score >= cfg.now_min_conviction and
                stage_rank >= confirmed_rank and not is_declining):
            return RotationTiming.NOW

        if (conviction_score >= cfg.this_week_min_conviction and
                stage_rank >= building_rank and not is_declining):
            return RotationTiming.THIS_WEEK

        if forecast >= cfg.this_month_min_forecast and not is_declining:
            return RotationTiming.THIS_MONTH

        return RotationTiming.WAIT
