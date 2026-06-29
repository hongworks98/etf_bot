"""
engines/rotation/analyzers/false_rotation_detector.py
False Rotation Detector — filters out temporary spikes misread as rotation.
"""
from __future__ import annotations
import math
from typing import List, Tuple
from engines.rotation.calculators.base import AbstractRotationCalculator
from engines.rotation.data_models import RotationConfig, RotationInput


class FalseRotationDetector(AbstractRotationCalculator):
    """
    SRP: Detects and flags false rotation signals.
    Rules:
      1. Rapid spike: score changed > 2σ in N days without breadth confirmation.
      2. Volume spike: volume > 3× baseline without follow-through.
      3. Insufficient persistence: score above threshold for < min_days.
    """

    def _score_spike(
        self, current_score: float, history: List[float], cfg: RotationConfig
    ) -> bool:
        """True if score jumped sharply in the last spike_change_days."""
        if len(history) < cfg.spike_window_days:
            return False
        std = self.std_dev(history[-cfg.spike_window_days:])
        if len(history) >= cfg.spike_change_days:
            change = abs(current_score - history[-cfg.spike_change_days])
        else:
            change = 0.0
        if std == 0:
            # constant history → any movement is an infinite-sigma spike
            return change > 5.0
        if len(history) >= cfg.spike_change_days:
            change = abs(current_score - history[-cfg.spike_change_days])
            return change > cfg.spike_sigma * std
        return False

    def _volume_spike_no_followthrough(
        self, volumes: List[float], cfg: RotationConfig
    ) -> bool:
        """True if there was a volume spike but it was not sustained."""
        if len(volumes) < cfg.vol_window_long + cfg.volume_follow_days:
            return False
        baseline = sum(volumes[-cfg.vol_window_long:-cfg.volume_follow_days]) / cfg.vol_window_long
        if baseline == 0:
            return False
        # Check if any day in follow window had spike
        spike_days = [v for v in volumes[-cfg.volume_follow_days:] if v > baseline * cfg.volume_spike_ratio]
        if not spike_days:
            return False
        # Check if volume returned to normal after spike
        most_recent = volumes[-1]
        return most_recent < baseline * 1.2   # returned to ~normal

    def _insufficient_persistence(self, persistence_days: int, cfg: RotationConfig) -> bool:
        return persistence_days < cfg.min_persistence_days

    def detect(
        self,
        ticker: str,
        current_score: float,
        history: List[float],
        persistence_days: int,
        inp: RotationInput,
        cfg: RotationConfig,
    ) -> Tuple[bool, str]:
        """
        Returns:
            is_false_rotation : bool
            reason            : explanation string (empty if not false)
        """
        # Rule 1: persistence check (most common false signal)
        if self._insufficient_persistence(persistence_days, cfg):
            return True, (
                f"Insufficient persistence: only {persistence_days} days "
                f"(min={cfg.min_persistence_days})"
            )

        # Rule 2: breadth-unconfirmed spike
        if self._score_spike(current_score, history, cfg):
            breadth_ok = inp.breadth_score >= 50.0
            if not breadth_ok:
                return True, (
                    "Rapid score spike without market breadth confirmation "
                    f"(breadth={inp.breadth_score:.1f})"
                )

        # Rule 3: volume spike with no follow-through
        sector_ph = inp.sectors.get(ticker)
        volumes   = inp.sector_volumes.get(ticker,
                        getattr(sector_ph, "volumes", []) if sector_ph else [])
        if self._volume_spike_no_followthrough(volumes, cfg):
            return True, "Volume spike without follow-through — likely event-driven, not rotation"

        return False, ""
