"""
engines/decision/calculators/exit_score.py
ExitScoreCalculator — 매도/청산 신호 강도 (0~100)

점수가 높을수록 지금 팔아야 한다는 신호가 강하다.
모든 구성 요소는 "위험/부정 방향"으로 설계 (역방향 매핑).

구성:
  risk_danger        = (100 - risk_score)   × 0.30
  trend_danger       = (100 - trend_score)  × 0.25
  macro_danger       = (100 - macro_score)  × 0.20
  drawdown_danger    = max(0, -pnl_pct × 3) × 0.15
  overweight_danger  = max(0, (w-max) × 500)× 0.10
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


class ExitScoreCalculator(AbstractScoreCalculator):
    """
    매도/청산 신호 점수 계산기

    ExitScore가 높을수록 빠져나가야 할 이유가 많음.
    DecisionMatrix에서 임계값 초과 시 TRIM 또는 SELL 결정.
    """

    def calculate(
        self,
        analysis: AnalysisResult,
        state: PortfolioState,
        config: DecisionConfig,
    ) -> Tuple[float, List[Contribution]]:
        w = config.exit_score_weights
        contributions: List[Contribution] = []
        position = state.positions.get(analysis.ticker)

        # 1. 리스크 위험도 (risk_score가 낮을수록 위험)
        risk_danger = 100.0 - analysis.risk_score
        c1 = Contribution(
            factor="risk_danger",
            raw_value=risk_danger,
            weight=w.get("risk_danger", 0.30),
            contribution=risk_danger * w.get("risk_danger", 0.30),
            direction="↑" if risk_danger > 60 else ("→" if risk_danger > 40 else "↓"),
            interpretation=(
                f"리스크 위험 {risk_danger:.0f}/100 — "
                + ("즉각 대응 필요" if risk_danger > 70
                   else "모니터링 강화" if risk_danger > 50
                   else "안전 범위")
            ),
        )
        contributions.append(c1)

        # 2. 추세 위험도 (trend_score가 낮을수록 위험)
        trend_danger = 100.0 - analysis.trend_score
        c2 = Contribution(
            factor="trend_danger",
            raw_value=trend_danger,
            weight=w.get("trend_danger", 0.25),
            contribution=trend_danger * w.get("trend_danger", 0.25),
            direction="↑" if trend_danger > 60 else ("→" if trend_danger > 40 else "↓"),
            interpretation=(
                f"추세 하락 강도 {trend_danger:.0f}/100 — "
                + ("하락 추세 진입" if trend_danger > 65
                   else "추세 약화 중" if trend_danger > 50
                   else "추세 건전")
            ),
        )
        contributions.append(c2)

        # 3. 매크로 위험도
        macro_danger = 100.0 - analysis.macro_score
        c3 = Contribution(
            factor="macro_danger",
            raw_value=macro_danger,
            weight=w.get("macro_danger", 0.20),
            contribution=macro_danger * w.get("macro_danger", 0.20),
            direction="↑" if macro_danger > 60 else ("→" if macro_danger > 40 else "↓"),
            interpretation=(
                f"매크로 역풍 {macro_danger:.0f}/100 — "
                + ("국면 전환 경고" if macro_danger > 65
                   else "부분 악화" if macro_danger > 50
                   else "매크로 안정")
            ),
        )
        contributions.append(c3)

        # 4. 손실 심화 위험 (보유 중일 때만 의미 있음)
        if position is not None:
            pnl_pct = position.unrealized_pnl_pct
            drawdown_raw = self.clamp(max(0.0, -pnl_pct * 3), 0, 100)
            if pnl_pct < -15:
                dd_dir, dd_interp = "↑", f"손실 {pnl_pct:.1f}% — 손절 기준 초과"
            elif pnl_pct < -5:
                dd_dir, dd_interp = "↑", f"손실 {pnl_pct:.1f}% — 손절 기준 접근"
            elif pnl_pct < 0:
                dd_dir, dd_interp = "→", f"소폭 손실 {pnl_pct:.1f}%"
            else:
                dd_dir, dd_interp = "↓", f"수익 {pnl_pct:+.1f}% — 손절 불필요"
        else:
            drawdown_raw = 0.0
            dd_dir, dd_interp = "↓", "미보유 — 손절 해당 없음"

        c4 = Contribution(
            factor="drawdown_danger",
            raw_value=drawdown_raw,
            weight=w.get("drawdown_danger", 0.15),
            contribution=drawdown_raw * w.get("drawdown_danger", 0.15),
            direction=dd_dir,
            interpretation=dd_interp,
        )
        contributions.append(c4)

        # 5. 비중 초과 패널티
        if position is not None:
            current_w = position.weight
            max_w = config.max_position_size
            overweight_raw = self.clamp(
                max(0.0, (current_w - max_w) * 500), 0, 100
            )
            if current_w > max_w:
                ow_dir = "↑"
                ow_interp = f"비중 {current_w:.1%} — 최대 {max_w:.0%} 초과, 리밸런싱 필요"
            else:
                ow_dir = "↓"
                ow_interp = f"비중 {current_w:.1%} — 한도 이내"
        else:
            overweight_raw = 0.0
            ow_dir, ow_interp = "↓", "미보유 — 비중 초과 없음"

        c5 = Contribution(
            factor="overweight_danger",
            raw_value=overweight_raw,
            weight=w.get("overweight_danger", 0.10),
            contribution=overweight_raw * w.get("overweight_danger", 0.10),
            direction=ow_dir,
            interpretation=ow_interp,
        )
        contributions.append(c5)

        # 최종 점수 (높을수록 매도 신호 강함)
        score = sum(c.contribution for c in contributions)
        return self.clamp(score), contributions
