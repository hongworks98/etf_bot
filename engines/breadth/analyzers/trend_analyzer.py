"""
engines/breadth/analyzers/trend_analyzer.py
TrendAnalyzer — 시장 폭의 시간적 추세 분석

1개월 / 3개월 / 6개월 기울기 + 가속도를 계산.

기울기 계산: 선형 회귀 (OLS)
  slope = Cov(x, y) / Var(x)  [단위: 점/일]

가속도 = slope_1m - slope_3m
  > 0: 최근 1개월 기울기 > 3개월 평균 → 폭 개선 가속 중
  < 0: 최근 기울기 < 3개월 평균 → 폭 개선 감속/악화 중

TrendDirection 결정:
  slope_1m > +threshold → UP
  slope_1m < -threshold → DOWN
  else → FLAT
"""

from __future__ import annotations
import statistics
from typing import List

from engines.breadth.data_models import (
    BreadthConfig,
    BreadthInput,
    TrendAnalysis,
    TrendDirection,
)


class TrendAnalyzer:
    """
    시장 폭 추세 분석기 (독립 Analyzer — Calculator 아님)
    """

    def analyze(
        self,
        inp: BreadthInput,
        config: BreadthConfig,
        breadth_scores: List[float],  # 과거 → 현재 순 점수 시계열
    ) -> TrendAnalysis:
        """
        Args:
            breadth_scores: 과거 날짜부터 현재까지의 breadth_score 리스트

        Returns:
            TrendAnalysis with slope/acceleration/direction
        """
        n = len(breadth_scores)

        slope_1m = self._linear_slope(breadth_scores, config.period_1m)
        slope_3m = self._linear_slope(breadth_scores, config.period_3m)
        slope_6m = self._linear_slope(breadth_scores, config.period_6m)

        acceleration = slope_1m - slope_3m

        # Trend Direction (1개월 기울기 기준)
        slope_threshold = 0.3  # 점/일
        if slope_1m > slope_threshold:
            direction = TrendDirection.UP
        elif slope_1m < -slope_threshold:
            direction = TrendDirection.DOWN
        else:
            direction = TrendDirection.FLAT

        # Trend Score (0~100)
        # slope_1m를 정규화 + 가속도 보너스
        lo = config.slope_normalize_lo  # -3.0
        hi = config.slope_normalize_hi  #  3.0
        slope_score = self._normalize(slope_1m, lo, hi)
        accel_bonus = acceleration * config.acceleration_weight  # 기본 0.3
        trend_score = max(0.0, min(100.0, slope_score + accel_bonus * 2))

        return TrendAnalysis(
            direction=direction,
            slope_1m=round(slope_1m, 3),
            slope_3m=round(slope_3m, 3),
            slope_6m=round(slope_6m, 3),
            acceleration=round(acceleration, 3),
            trend_score=round(trend_score, 2),
        )

    # ── 내부 유틸 ──────────────────────────────

    @staticmethod
    def _linear_slope(data: List[float], period: int) -> float:
        """
        최근 N일의 선형 회귀 기울기를 반환.
        데이터가 부족하면 가능한 만큼 사용.

        OLS slope = Cov(x,y) / Var(x)
        x = [0, 1, 2, ..., n-1], y = data[-n:]
        """
        if not data:
            return 0.0

        window = min(period, len(data))
        y = data[-window:]
        n = len(y)
        if n < 2:
            return 0.0

        x = list(range(n))
        x_mean = (n - 1) / 2.0
        y_mean = sum(y) / n

        cov_xy = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        var_x  = sum((x[i] - x_mean) ** 2 for i in range(n))

        return cov_xy / var_x if var_x != 0 else 0.0

    @staticmethod
    def _normalize(value: float, lo: float, hi: float) -> float:
        if hi == lo:
            return 50.0
        clamped = max(lo, min(hi, value))
        return (clamped - lo) / (hi - lo) * 100.0
