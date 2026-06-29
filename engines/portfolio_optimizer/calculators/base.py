"""engines/portfolio_optimizer/calculators/base.py"""
from __future__ import annotations
import math
from abc import ABC
from typing import List


class AbstractOptimizationCalculator(ABC):
    @staticmethod
    def clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
        return max(lo, min(hi, v))

    @staticmethod
    def normalize(v: float, lo: float, hi: float) -> float:
        if hi == lo:
            return 50.0
        return AbstractOptimizationCalculator.clamp((v - lo) / (hi - lo) * 100.0, 0.0, 100.0)

    @staticmethod
    def mean(data: List[float]) -> float:
        return sum(data) / len(data) if data else 0.0

    @staticmethod
    def std_dev(data: List[float]) -> float:
        if len(data) < 2:
            return 0.0
        m = sum(data) / len(data)
        return math.sqrt(sum((x - m) ** 2 for x in data) / (len(data) - 1))

    @staticmethod
    def dot(a: List[float], b: List[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    @staticmethod
    def safe_div(a: float, b: float, default: float = 0.0) -> float:
        return a / b if abs(b) > 1e-12 else default
