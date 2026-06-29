"""
engines/breadth/calculators/base.py
AbstractBreadthCalculator — 모든 Breadth Calculator의 공통 인터페이스

SOLID:
- 단일 책임: 하나의 시장 폭 지표만 계산
- 의존성 역전: Engine은 ABC에 의존, 구체 Calculator에 의존하지 않음
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List

from engines.breadth.data_models import BreadthConfig, BreadthInput, ComponentScore


class AbstractBreadthCalculator(ABC):
    """
    Breadth Calculator 인터페이스

    Returns:
        List[ComponentScore]: 이 Calculator가 책임지는 1개 이상의 지표 점수
    """

    @abstractmethod
    def calculate(
        self,
        inp: BreadthInput,
        config: BreadthConfig,
    ) -> List[ComponentScore]:
        ...

    # ── 공통 유틸 ──────────────────────────

    @staticmethod
    def normalize(value: float, lo: float, hi: float) -> float:
        """
        [lo, hi] 범위의 raw value를 0~100 점수로 변환.
        lo 이하 → 0, hi 이상 → 100.
        """
        if hi == lo:
            return 50.0
        clamped = max(lo, min(hi, value))
        return (clamped - lo) / (hi - lo) * 100.0

    @staticmethod
    def ema(values: List[float], period: int) -> float:
        """
        지수 이동평균(EMA) 계산.
        데이터 부족 시 단순 평균 반환.
        """
        if not values:
            return 50.0
        if len(values) < period:
            return sum(values) / len(values)
        k = 2.0 / (period + 1)
        result = values[0]
        for v in values[1:]:
            result = v * k + result * (1 - k)
        return result

    @staticmethod
    def _direction(score: float, threshold: float = 60.0) -> str:
        """점수 기반 방향 표시"""
        if score >= threshold + 5:
            return "↑"
        elif score <= threshold - 15:
            return "↓"
        return "→"

    @staticmethod
    def _make_score(
        name: str,
        raw_value: float,
        normalized: float,
        weight: float,
        positive_label: str = "",
        negative_label: str = "",
        neutral_label: str = "",
    ) -> ComponentScore:
        """ComponentScore 생성 헬퍼"""
        direction = "↑" if normalized >= 65 else ("↓" if normalized <= 35 else "→")
        if normalized >= 65:
            interp = positive_label or f"{name} 강세"
        elif normalized <= 35:
            interp = negative_label or f"{name} 약세"
        else:
            interp = neutral_label or f"{name} 중립"

        return ComponentScore(
            name=name,
            raw_value=raw_value,
            normalized_score=normalized,
            weight=weight,
            contribution=normalized * weight,
            direction=direction,
            interpretation=interp,
        )
