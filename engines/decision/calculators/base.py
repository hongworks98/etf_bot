"""
engines/decision/calculators/base.py
AbstractScoreCalculator — SOLID: Interface Segregation + Liskov

모든 점수 Calculator는 이 추상 클래스를 구현한다.
Engine은 구체 구현이 아닌 이 ABC에 의존한다 (Dependency Inversion).
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Tuple

from engines.decision.data_models import (
    AnalysisResult,
    Contribution,
    DecisionConfig,
    PortfolioState,
)


class AbstractScoreCalculator(ABC):
    """
    점수 Calculator 인터페이스

    Returns:
        (score, contributions)
        score        : 0~100 float
        contributions: 각 지표의 기여 내역 (Explainable AI)
    """

    @abstractmethod
    def calculate(
        self,
        analysis: AnalysisResult,
        state: PortfolioState,
        config: DecisionConfig,
    ) -> Tuple[float, List[Contribution]]:
        ...

    # ── 공통 유틸 ─────────────────────────────

    @staticmethod
    def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
        return max(lo, min(hi, value))

    @staticmethod
    def _make_contribution(
        factor: str,
        raw_value: float,
        weight: float,
        positive_threshold: float = 60.0,
        label_positive: str = "",
        label_negative: str = "",
    ) -> Contribution:
        """Contribution 객체 생성 헬퍼"""
        contribution = raw_value * weight
        if raw_value >= positive_threshold + 10:
            direction = "↑"
            interp = label_positive or f"{factor} 강세"
        elif raw_value <= positive_threshold - 10:
            direction = "↓"
            interp = label_negative or f"{factor} 약세"
        else:
            direction = "→"
            interp = f"{factor} 중립"
        return Contribution(
            factor=factor,
            raw_value=raw_value,
            weight=weight,
            contribution=contribution,
            direction=direction,
            interpretation=interp,
        )
