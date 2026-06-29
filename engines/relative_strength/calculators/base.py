"""
engines/relative_strength/calculators/base.py
Abstract base class for all RS calculators — SOLID / DIP
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from engines.relative_strength.data_models import (
    PriceHistory, RSConfig, RSContribution,
)


class AbstractRSCalculator(ABC):
    """
    SRP : each subclass has exactly one computational responsibility.
    OCP : extend by adding new subclasses, never by modifying this base.
    LSP : all subclasses are interchangeable in the engine.
    DIP : engine depends on this ABC, not on concrete calculators.
    """

    # ── utility ────────────────────────────────────────────────────

    @staticmethod
    def normalize(value: float, lo: float, hi: float) -> float:
        """Linear normalisation to 0~100.  Clamped at both ends."""
        if hi == lo:
            return 50.0
        raw = (value - lo) / (hi - lo) * 100.0
        return max(0.0, min(100.0, raw))

    @staticmethod
    def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
        return max(lo, min(hi, value))

    @staticmethod
    def linear_slope(data: List[float], period: int) -> float:
        """OLS linear regression slope over the last `period` points."""
        window = min(period, len(data))
        if window < 2:
            return 0.0
        y = data[-window:]
        n = len(y)
        x_mean = (n - 1) / 2.0
        y_mean = sum(y) / n
        cov_xy = sum((i - x_mean) * (y[i] - y_mean) for i in range(n))
        var_x  = sum((i - x_mean) ** 2 for i in range(n))
        return cov_xy / var_x if var_x != 0 else 0.0

    @staticmethod
    def make_contribution(
        factor: str,
        raw_value: float,
        weight: float,
        normalized_value: float,
        positive_threshold: float = 55.0,
        negative_threshold: float = 45.0,
        pos_msg: str = "Positive",
        neg_msg: str = "Negative",
        neu_msg: str = "Neutral",
    ) -> RSContribution:
        contribution = weight * normalized_value
        if normalized_value >= positive_threshold:
            direction, interpretation = "↑", pos_msg
        elif normalized_value <= negative_threshold:
            direction, interpretation = "↓", neg_msg
        else:
            direction, interpretation = "→", neu_msg
        return RSContribution(
            factor=factor,
            raw_value=round(raw_value, 4),
            weight=weight,
            contribution=round(contribution, 4),
            direction=direction,
            interpretation=interpretation,
        )
