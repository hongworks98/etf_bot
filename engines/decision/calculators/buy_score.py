"""
engines/decision/calculators/buy_score.py
BuyScoreCalculator — 매수 신호 강도 (0~100)

점수가 높을수록 지금 매수하기에 좋은 환경임을 의미한다.

구성:
  macro_score   × 0.30  → 매크로 환경이 매수를 지지하는가?
  trend_score   × 0.20  → 기술적 추세가 상승 방향인가?
  etf_score     × 0.20  → ETF 자체 품질이 우수한가?
  breadth_score × 0.15  → 시장 전반이 강한가?
  rs_score      × 0.15  → 상대강도가 우수한가?
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


class BuyScoreCalculator(AbstractScoreCalculator):
    """
    매수 신호 점수 계산기

    신규 또는 추가 매수 판단의 1차 관문.
    점수가 높을수록 "지금 사라"는 신호가 강하다.
    """

    def calculate(
        self,
        analysis: AnalysisResult,
        state: PortfolioState,
        config: DecisionConfig,
    ) -> Tuple[float, List[Contribution]]:
        w = config.buy_score_weights
        contributions: List[Contribution] = []

        # 1. 매크로 환경
        c1 = self._make_contribution(
            factor="macro_score",
            raw_value=analysis.macro_score,
            weight=w.get("macro_score", 0.30),
            positive_threshold=60,
            label_positive=f"매크로 강세 ({analysis.macro_state}) — 매수 지지",
            label_negative=f"매크로 약세 ({analysis.macro_state}) — 매수 제한",
        )
        contributions.append(c1)

        # 2. 기술적 추세
        c2 = self._make_contribution(
            factor="trend_score",
            raw_value=analysis.trend_score,
            weight=w.get("trend_score", 0.20),
            positive_threshold=55,
            label_positive="상승 추세 확인 — 기술적 진입 적합",
            label_negative="하락 추세 — 기술적 진입 부적합",
        )
        contributions.append(c2)

        # 3. ETF 품질
        c3 = self._make_contribution(
            factor="etf_score",
            raw_value=analysis.etf_score,
            weight=w.get("etf_score", 0.20),
            positive_threshold=60,
            label_positive="ETF 모멘텀·샤프비율 우수",
            label_negative="ETF 품질 미흡 — 대안 탐색 필요",
        )
        contributions.append(c3)

        # 4. 시장 폭
        c4 = self._make_contribution(
            factor="breadth_score",
            raw_value=analysis.breadth_score,
            weight=w.get("breadth_score", 0.15),
            positive_threshold=55,
            label_positive="시장 폭 강세 — 랠리 지속성 지지",
            label_negative="시장 폭 약세 — 좁은 랠리 주의",
        )
        contributions.append(c4)

        # 5. 상대강도
        c5 = self._make_contribution(
            factor="rs_score",
            raw_value=analysis.rs_score,
            weight=w.get("rs_score", 0.15),
            positive_threshold=55,
            label_positive="상대강도 우수 — 섹터 리더십 확인",
            label_negative="상대강도 열위 — 섹터 순환 고려",
        )
        contributions.append(c5)

        # 최종 점수
        score = sum(c.contribution for c in contributions)
        return self.clamp(score), contributions
