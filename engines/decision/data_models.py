"""
engines/decision/data_models.py
PortfolioDecisionEngine — 모든 데이터 모델 (dataclass + enum)

설계 원칙:
- 모든 점수는 0~100 (높을수록 긍정적)
- 기존 Analysis Engine 출력물을 절대 수정하지 않음
- 이 파일은 순수 데이터 컨테이너만 포함 (로직 없음)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class Action(str, Enum):
    """포트폴리오 결정 행동"""
    BUY  = "BUY"   # 신규 매수
    ADD  = "ADD"   # 추가 매수 (기존 보유)
    HOLD = "HOLD"  # 보유 유지
    TRIM = "TRIM"  # 부분 매도
    SELL = "SELL"  # 전량 매도
    WAIT = "WAIT"  # 관망 (미보유)


class RiskLevel(str, Enum):
    """포트폴리오 리스크 수준"""
    GREEN  = "GREEN"   # 안전
    YELLOW = "YELLOW"  # 주의
    ORANGE = "ORANGE"  # 경고
    RED    = "RED"     # 위험


# ─────────────────────────────────────────────
# 입력 모델
# ─────────────────────────────────────────────

@dataclass
class Position:
    """현재 보유 포지션 정보"""
    ticker: str
    weight: float                  # 포트폴리오 내 비중 (0~1)
    entry_price: float             # 평균 매수가
    current_price: float           # 현재가
    unrealized_pnl_pct: float      # 미실현 손익률 (%)
    days_held: int                 # 보유 일수
    sector: str = ""               # 섹터명


@dataclass
class RiskMetrics:
    """포트폴리오 전체 리스크 지표"""
    portfolio_beta: float = 1.0          # 시장 대비 베타
    portfolio_volatility: float = 0.15   # 연환산 변동성
    max_drawdown_pct: float = 0.0        # 최대낙폭 (%)
    var_95: float = 0.0                  # 95% VaR
    concentration_risk: float = 0.0     # 집중도 리스크 (0~100)


@dataclass
class PortfolioState:
    """현재 포트폴리오 전체 상태"""
    cash_pct: float                                    # 현금 비중 (0~1)
    positions: Dict[str, Position] = field(default_factory=dict)
    sector_exposure: Dict[str, float] = field(default_factory=dict)  # 섹터별 비중
    risk_metrics: RiskMetrics = field(default_factory=RiskMetrics)
    total_value_krw: float = 1_000_000.0              # 포트폴리오 총액 (원)
    target_positions: int = 10                         # 목표 보유 종목 수


@dataclass
class AnalysisResult:
    """
    Analysis Layer 출력 — 10개 Engine의 통합 결과
    (기존 Engine 수정 없이 이 dataclass로 래핑)

    모든 점수: 0~100, 높을수록 긍정적
    """
    ticker: str

    # 핵심 점수 (0~100)
    macro_score:    float = 50.0   # 매크로 환경 지수 (MacroStateEngine)
    risk_score:     float = 50.0   # 리스크 안전도 (RiskEngine, 높=안전)
    trend_score:    float = 50.0   # 기술적 추세 강도 (TrendEngine)
    breadth_score:  float = 50.0   # 시장 폭 강도 (BreadthEngine)
    rs_score:       float = 50.0   # 상대강도 (RSEngine)
    etf_score:      float = 50.0   # ETF 종합 품질 (ETFRankingEngine)
    momentum_score: float = 50.0   # 모멘텀 (MomentumEngine)

    # 메타 정보
    macro_state:      str = "Unknown"   # Recovery/Expansion/Overheating/...
    macro_direction:  str = "FLAT"      # UP / FLAT / DOWN
    sector_rank:      int = 5           # 현재 국면 섹터 추천 순위 (1=최고)
    risk_level:       str = "YELLOW"    # GREEN/YELLOW/ORANGE/RED

    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ThresholdConfig:
    """의사결정 임계값"""
    strong_buy:          float = 75.0
    buy:                 float = 60.0
    add:                 float = 55.0
    hold_min:            float = 45.0
    trim:                float = 60.0
    sell:                float = 75.0
    risk_override_sell:  float = 85.0
    risk_override_trim:  float = 70.0


@dataclass
class DecisionConfig:
    """
    Engine 동작 설정 — YAML에서 로드
    모든 가중치는 합이 1.0이어야 함
    """
    # 점수별 가중치
    buy_score_weights: Dict[str, float] = field(default_factory=lambda: {
        "macro_score": 0.30, "trend_score": 0.20, "etf_score": 0.20,
        "breadth_score": 0.15, "rs_score": 0.15
    })
    hold_score_weights: Dict[str, float] = field(default_factory=lambda: {
        "macro_score": 0.25, "risk_score": 0.25, "trend_score": 0.20,
        "position_health": 0.15, "portfolio_fit": 0.15
    })
    exit_score_weights: Dict[str, float] = field(default_factory=lambda: {
        "risk_danger": 0.30, "trend_danger": 0.25, "macro_danger": 0.20,
        "drawdown_danger": 0.15, "overweight_danger": 0.10
    })
    opportunity_score_weights: Dict[str, float] = field(default_factory=lambda: {
        "etf_score": 0.35, "macro_align": 0.25,
        "momentum_score": 0.20, "rs_score": 0.20
    })

    # 임계값
    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)

    # 포트폴리오 제약
    max_position_size:       float = 0.30
    max_sector_exposure:     float = 0.40
    default_position_size:   float = 0.10
    min_position_size:       float = 0.03
    max_portfolio_positions: int   = 10
    min_cash_pct:            float = 0.05

    # Position Health 파라미터
    pnl_multiplier:  float = 2.0
    max_pnl_effect:  float = 40.0

    # Macro Align 점수 매핑
    macro_align_scores: Dict[str, int] = field(default_factory=lambda: {
        "rank_1": 100, "rank_2": 80, "rank_3": 60,
        "rank_4": 40, "rank_5": 20, "default": 0
    })

    # 신뢰도 파라미터
    confidence_max_std: float = 30.0
    confidence_min_std: float = 5.0

    # Priority 기준
    priority_map: Dict[str, int] = field(default_factory=lambda: {
        "BUY": 1, "ADD": 2, "SELL": 3, "TRIM": 4, "HOLD": 5, "WAIT": 9
    })


# ─────────────────────────────────────────────
# 출력 모델
# ─────────────────────────────────────────────

@dataclass
class Contribution:
    """
    Explainable AI — 하나의 지표가 점수에 기여한 내역
    예: macro_score (72점, 가중치 30%) → 기여 21.6점 → 매수 지지 ↑
    """
    factor: str            # 지표명 (e.g. "macro_score")
    raw_value: float       # 원본 점수 (0~100)
    weight: float          # 적용 가중치 (0~1)
    contribution: float    # 실제 기여 점수 (raw_value × weight)
    direction: str         # "↑" 긍정 / "↓" 부정 / "→" 중립
    interpretation: str    # 사람이 읽을 설명 (e.g. "매크로 강세 — 매수 지지")


@dataclass
class ActionScore:
    """4가지 신호 점수 + 기여 내역"""
    buy_score:         float  # 0~100
    hold_score:        float  # 0~100
    exit_score:        float  # 0~100 (높을수록 매도 신호)
    opportunity_score: float  # 0~100

    # Explainability: 각 점수의 기여 내역
    buy_contributions:  List[Contribution] = field(default_factory=list)
    hold_contributions: List[Contribution] = field(default_factory=list)
    exit_contributions: List[Contribution] = field(default_factory=list)
    opp_contributions:  List[Contribution] = field(default_factory=list)


@dataclass
class DecisionResult:
    """
    PortfolioDecisionEngine 최종 출력
    하나의 ETF에 대한 완전한 투자 결정
    """
    ticker: str
    action: Action

    # 우선순위 & 신뢰도
    priority:   int    # 1=최우선 (BUY), 9=최하위 (WAIT)
    confidence: float  # 0.0~1.0 (신호 일치도)

    # 비중 변화
    current_weight: float   # 현재 포트폴리오 내 비중 (0~1)
    target_weight:  float   # 목표 비중 (0~1)
    delta_weight:   float   # 변화량 (+ 매수, - 매도)

    # 점수 상세
    action_score: ActionScore

    # 리스크
    risk_level: RiskLevel

    # 설명
    reasons:  List[str]   # 결정 근거 (3~5개)
    warnings: List[str]   # 주의사항 (0~3개)

    timestamp: datetime = field(default_factory=datetime.now)

    # ── 편의 프로퍼티 ──────────────────────────

    @property
    def buy_score(self) -> float:
        return self.action_score.buy_score

    @property
    def hold_score(self) -> float:
        return self.action_score.hold_score

    @property
    def exit_score(self) -> float:
        return self.action_score.exit_score

    @property
    def opportunity_score(self) -> float:
        return self.action_score.opportunity_score

    @property
    def is_actionable(self) -> bool:
        """BUY/ADD/SELL/TRIM 중 하나면 True"""
        return self.action in (Action.BUY, Action.ADD, Action.SELL, Action.TRIM)

    def summary(self) -> str:
        """한 줄 요약"""
        arrow = "▲" if self.delta_weight > 0 else ("▼" if self.delta_weight < 0 else "—")
        return (
            f"[{self.action.value}] {self.ticker} | "
            f"신뢰도 {self.confidence:.0%} | "
            f"비중 {self.current_weight:.1%}→{self.target_weight:.1%} {arrow}{abs(self.delta_weight):.1%} | "
            f"리스크 {self.risk_level.value}"
        )
