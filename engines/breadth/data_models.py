"""
engines/breadth/data_models.py
MarketBreadthEngine — 모든 데이터 모델

설계 원칙:
- 순수 데이터 컨테이너 (로직 없음)
- 모든 점수 0~100, 높을수록 시장 건강
- PortfolioDecisionEngine.AnalysisResult.breadth_score와 직접 호환
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional


# ─────────────────────────────────────────
# Enums
# ─────────────────────────────────────────

class HealthLevel(str, Enum):
    """시장 폭 건강도 4단계"""
    EXCELLENT = "Excellent"   # breadth_score >= 75
    HEALTHY   = "Healthy"     # breadth_score >= 55
    WEAKENING = "Weakening"   # breadth_score >= 35
    CRITICAL  = "Critical"    # breadth_score <  35


class DivergenceType(str, Enum):
    """지수 vs 시장 폭 괴리 유형"""
    BULLISH = "Bullish"   # 지수↓ + 폭↑ → 저점 신호
    BEARISH = "Bearish"   # 지수↑ + 폭↓ → 고점 경고
    NONE    = "None"      # 괴리 없음


class TrendDirection(str, Enum):
    """시장 폭 추세 방향"""
    UP   = "UP"
    FLAT = "FLAT"
    DOWN = "DOWN"


# ─────────────────────────────────────────
# 입력 모델
# ─────────────────────────────────────────

@dataclass
class DailyBreadthData:
    """
    하루치 시장 폭 원시 데이터
    S&P500 구성 종목 기준 집계값
    """
    date: date

    # Advance / Decline
    advances:  int = 0    # 상승 종목 수
    declines:  int = 0    # 하락 종목 수
    unchanged: int = 0    # 보합 종목 수

    # New High / New Low (52주 기준)
    new_highs: int = 0
    new_lows:  int = 0

    # MA 상회 비율 (%)  0~100
    pct_above_20ma:  float = 50.0
    pct_above_50ma:  float = 50.0
    pct_above_200ma: float = 50.0

    # Volume
    advancing_volume: float = 0.0   # 상승 종목 거래량
    declining_volume: float = 0.0   # 하락 종목 거래량
    total_volume:     float = 0.0   # 전체 거래량

    # Index
    index_price:  float = 0.0   # S&P500 지수

    # ── 파생 프로퍼티 ──────────────────────

    @property
    def total_active(self) -> int:
        """보합 제외 활성 종목 수"""
        return self.advances + self.declines

    @property
    def ad_ratio(self) -> float:
        """Advance/Decline Ratio (0~100)"""
        total = self.total_active
        return (self.advances / total * 100) if total > 0 else 50.0

    @property
    def nh_nl_ratio(self) -> float:
        """New High / (New High + New Low) (0~100)"""
        total = self.new_highs + self.new_lows
        return (self.new_highs / total * 100) if total > 0 else 50.0

    @property
    def participation_ratio(self) -> float:
        """Advancing Volume / Total Volume (0~100)"""
        return (self.advancing_volume / self.total_volume * 100) if self.total_volume > 0 else 50.0

    @property
    def net_advance(self) -> int:
        """순 상승 종목 수 (AD Line 누적용)"""
        return self.advances - self.declines


@dataclass
class BreadthConfig:
    """
    Engine 동작 설정 — YAML에서 로드
    """
    # 컴포넌트 가중치
    component_weights: Dict[str, float] = field(default_factory=lambda: {
        "ad_ratio":        0.20,
        "ad_line_trend":   0.10,
        "nh_nl_ratio":     0.15,
        "pct_above_20ma":  0.08,
        "pct_above_50ma":  0.12,
        "pct_above_200ma": 0.18,
        "participation":   0.10,
        "breadth_thrust":  0.07,
    })

    # 정규화 범위
    normalization: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "ad_ratio":        {"lo": 35.0, "hi": 65.0},
        "ad_line_trend":   {"lo": -20.0, "hi": 20.0},
        "nh_nl_ratio":     {"lo": 20.0, "hi": 80.0},
        "pct_above_20ma":  {"lo": 25.0, "hi": 75.0},
        "pct_above_50ma":  {"lo": 25.0, "hi": 75.0},
        "pct_above_200ma": {"lo": 25.0, "hi": 75.0},
        "participation":   {"lo": 35.0, "hi": 65.0},
        "breadth_thrust":  {"lo": 38.0, "hi": 63.0},
    })

    # Health Level 임계값
    health_excellent:  float = 75.0
    health_healthy:    float = 55.0
    health_weakening:  float = 35.0

    # Divergence 파라미터
    divergence_lookback:        int   = 20
    index_move_threshold:       float = 2.0
    breadth_move_threshold:     float = 5.0
    divergence_strong_threshold:float = 50.0

    # Trend 파라미터
    period_1m:              int   = 21
    period_3m:              int   = 63
    period_6m:              int   = 126
    acceleration_weight:    float = 0.3
    slope_normalize_lo:     float = -3.0
    slope_normalize_hi:     float =  3.0

    # Breadth Thrust (Zweig)
    ema_period:         int   = 10
    thrust_signal_hi:   float = 61.5
    thrust_signal_lo:   float = 40.0

    # Confidence
    min_history_days:   int   = 10
    full_history_days:  int   = 63
    variance_penalty:   float = 0.5


@dataclass
class BreadthInput:
    """
    MarketBreadthEngine 입력 데이터
    current: 오늘 데이터
    history: 과거 시계열 (오래된 순 정렬)
    """
    current:          DailyBreadthData
    history:          List[DailyBreadthData] = field(default_factory=list)
    total_components: int = 500   # S&P500 = 500


# ─────────────────────────────────────────
# 출력 모델
# ─────────────────────────────────────────

@dataclass
class ComponentScore:
    """
    Explainable AI — 하나의 지표가 Breadth Score에 기여한 내역
    """
    name:             str    # 지표명
    raw_value:        float  # 원시값 (e.g. 68.5% above 200MA)
    normalized_score: float  # 0~100
    weight:           float  # 가중치
    contribution:     float  # normalized_score × weight
    direction:        str    # "↑" 강세 / "↓" 약세 / "→" 중립
    interpretation:   str    # 사람이 읽을 설명


@dataclass
class TrendAnalysis:
    """
    시장 폭의 시간적 추세
    slope 단위: 점/일 (score points per trading day)
    """
    direction:    TrendDirection
    slope_1m:     float = 0.0   # 21일 선형 기울기
    slope_3m:     float = 0.0   # 63일 선형 기울기
    slope_6m:     float = 0.0   # 126일 선형 기울기
    acceleration: float = 0.0   # slope_1m - slope_3m (빨라지면 양수)
    trend_score:  float = 50.0  # 0~100 (높을수록 상승 추세)

    def summary(self) -> str:
        dir_arrow = {"UP": "↑", "FLAT": "→", "DOWN": "↓"}[self.direction.value]
        return (
            f"{dir_arrow} {self.direction.value} | "
            f"1M:{self.slope_1m:+.2f} 3M:{self.slope_3m:+.2f} 6M:{self.slope_6m:+.2f} | "
            f"Accel:{self.acceleration:+.2f}"
        )


@dataclass
class DivergenceSignal:
    """
    지수 vs 시장 폭 괴리 신호
    """
    type:           DivergenceType
    strength:       float = 0.0    # 0~100 (강할수록 신뢰도 높음)
    lookback_days:  int   = 20
    index_change_pct:   float = 0.0   # 지수 변화율 (%)
    breadth_change_pt:  float = 0.0   # AD Ratio 변화 (pt)
    description:    str   = ""

    @property
    def is_active(self) -> bool:
        return self.type != DivergenceType.NONE

    @property
    def is_strong(self) -> bool:
        return self.strength >= 50.0


@dataclass
class BreadthResult:
    """
    MarketBreadthEngine 최종 출력

    breadth_score → PortfolioDecisionEngine의 AnalysisResult.breadth_score로 공급
    """
    # 핵심 출력
    breadth_score:      float         # 0~100 (AnalysisResult 공급값)
    health_level:       HealthLevel
    trend:              TrendAnalysis
    participation_score: float        # 0~100

    # 분석 결과
    divergence:         DivergenceSignal
    confidence:         float         # 0.0~1.0

    # Explainable AI
    component_scores:   List[ComponentScore] = field(default_factory=list)
    reasons:            List[str] = field(default_factory=list)
    warnings:           List[str] = field(default_factory=list)

    timestamp: datetime = field(default_factory=datetime.now)

    # ── 편의 프로퍼티 ──────────────────────

    @property
    def is_healthy(self) -> bool:
        return self.health_level in (HealthLevel.EXCELLENT, HealthLevel.HEALTHY)

    @property
    def has_bearish_divergence(self) -> bool:
        return self.divergence.type == DivergenceType.BEARISH

    @property
    def has_bullish_divergence(self) -> bool:
        return self.divergence.type == DivergenceType.BULLISH

    def summary(self) -> str:
        div_str = f" [{self.divergence.type.value} Divergence!]" if self.divergence.is_active else ""
        return (
            f"Breadth Score {self.breadth_score:.1f}/100 | "
            f"{self.health_level.value} | "
            f"Trend {self.trend.direction.value} | "
            f"Conf {self.confidence:.0%}"
            f"{div_str}"
        )
