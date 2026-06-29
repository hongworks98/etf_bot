"""
engines/decision/calculators/hold_score.py
HoldScoreCalculator — 보유 유지 신호 강도 (0~100)

점수가 높을수록 현재 포지션을 그대로 보유하는 것이 유리함을 의미한다.

구성:
  macro_score      × 0.25  → 매크로 지지 지속
  risk_score       × 0.25  → 안전 환경 (높을수록 보유 유리)
  trend_score      × 0.20  → 추세 지속성
  position_health  × 0.15  → 현재 포지션 손익·보유기간 건전성
  portfolio_fit    × 0.15  → 목표 비중과의 적합성

position_health = clamp(50 + pnl_pct × pnl_multiplier, 0, 100)
portfolio_fit   = clamp(100 - |current_w - target_w| × 500, 0, 100)
"""

from __future__ import annotations
from typing import List, Tuple

from engines.decision.data_models import (
    AnalysisResult,
    Contribution,
    DecisionConfig,
    PortfolioState,
)
from engines.decision.calculators.base import AbstractScoreCalculator


class HoldScoreCalculator(AbstractScoreCalculator):
    """
    보유 유지 신호 점수 계산기

    포지션이 없는 종목에 대해서도 호출되지만,
    position_health / portfolio_fit은 보유 중일 때만 의미 있음.
    보유하지 않은 경우 두 요소는 50점(중립)으로 처리.
    """

    def calculate(
        self,
        analysis: AnalysisResult,
        state: PortfolioState,
        config: DecisionConfig,
    ) -> Tuple[float, List[Contribution]]:
        w = config.hold_score_weights
        contributions: List[Contribution] = []

        # 포지션 존재 여부
        position = state.positions.get(analysis.ticker)
        is_held = position is not None

        # 1. 매크로 지지
        c1 = self._make_contribution(
            factor="macro_score",
            raw_value=analysis.macro_score,
            weight=w.get("macro_score", 0.25),
            label_positive="매크로 지지 지속 — 보유 유리",
            label_negative="매크로 악화 — 보유 재검토",
        )
        contributions.append(c1)

        # 2. 리스크 환경 (높을수록 보유 안전)
        c2 = self._make_contribution(
            factor="risk_score",
            raw_value=analysis.risk_score,
            weight=w.get("risk_score", 0.25),
            positive_threshold=55,
            label_positive="리스크 환경 안정 — 안전 보유 가능",
            label_negative="리스크 고조 — 손절 라인 점검 필요",
        )
        contributions.append(c2)

        # 3. 추세 지속성
        c3 = self._make_contribution(
            factor="trend_score",
            raw_value=analysis.trend_score,
            weight=w.get("trend_score", 0.20),
            positive_threshold=50,
            label_positive="상승 추세 지속 중",
            label_negative="추세 약화 감지",
        )
        contributions.append(c3)

        # 4. 포지션 건전성
        if is_held:
            pnl_pct = position.unrealized_pnl_pct
            health_raw = 50.0 + pnl_pct * config.pnl_multiplier
            health_raw = self.clamp(health_raw, 0, 100)
            pnl_label = f"수익률 {pnl_pct:+.1f}%"
            if pnl_pct >= 5:
                health_interp = f"{pnl_label} — 수익 보호 유지"
                h_dir = "↑"
            elif pnl_pct <= -10:
                health_interp = f"{pnl_label} — 손실 심화, 보유 재검토"
                h_dir = "↓"
            else:
                health_interp = f"{pnl_label} — 정상 보유 범위"
                h_dir = "→"
        else:
            health_raw = 50.0
            health_interp = "미보유 — 중립"
            h_dir = "→"

        c4 = Contribution(
            factor="position_health",
            raw_value=health_raw,
            weight=w.get("position_health", 0.15),
            contribution=health_raw * w.get("position_health", 0.15),
            direction=h_dir,
            interpretation=health_interp,
        )
        contributions.append(c4)

        # 5. 목표 비중 적합성
        if is_held:
            current_w = position.weight
            target_w = config.default_position_size
            fit_raw = self.clamp(100.0 - abs(current_w - target_w) * 500, 0, 100)
            diff_pct = (current_w - target_w) * 100
            if abs(diff_pct) <= 2:
                fit_interp = f"비중 {current_w:.1%} — 목표 비중 적합"
                f_dir = "↑"
            elif diff_pct > 2:
                fit_interp = f"비중 {current_w:.1%} — 목표 대비 +{diff_pct:.1f}%p 초과"
                f_dir = "↓"
            else:
                fit_interp = f"비중 {current_w:.1%} — 목표 대비 {diff_pct:.1f}%p 부족"
                f_dir = "→"
        else:
            fit_raw = 50.0
            fit_interp = "미보유 — 중립"
            f_dir = "→"

        c5 = Contribution(
            factor="portfolio_fit",
            raw_value=fit_raw,
            weight=w.get("portfolio_fit", 0.15),
            contribution=fit_raw * w.get("portfolio_fit", 0.15),
            direction=f_dir,
            interpretation=fit_interp,
        )
        contributions.append(c5)

        # 최종 점수
        score = sum(c.contribution for c in contributions)
        return self.clamp(score), contributions
