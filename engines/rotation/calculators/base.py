"""engines/rotation/calculators/base.py — Abstract base for all Rotation calculators."""
from __future__ import annotations
import math
from abc import ABC
from typing import List


class AbstractRotationCalculator(ABC):
    """
    SOLID base: SRP per subclass, OCP via extension, DIP for engine injection.
    """

    @staticmethod
    def normalize(value: float, lo: float, hi: float) -> float:
        if hi == lo:
            return 50.0
        return max(0.0, min(100.0, (value - lo) / (hi - lo) * 100.0))

    @staticmethod
    def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
        return max(lo, min(hi, value))

    @staticmethod
    def std_dev(data: List[float]) -> float:
        n = len(data)
        if n < 2:
            return 0.0
        mean = sum(data) / n
        return math.sqrt(sum((x - mean) ** 2 for x in data) / n)

    @staticmethod
    def linear_slope(data: List[float], period: int) -> float:
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
