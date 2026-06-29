"""
engines/decision/calculators/opportunity_score.py
OpportunityScoreCalculator — 투자 기회 매력도 (0~100)

"지금 이 ETF가 얼마나 매력적인가?"를 평가.
BuyScore와 달리 현재 국면과의 정합성(macro_align)에 집중.
우선순위(Priority) 계산에 사용.

구성:
  etf_score      × 0.35  → ETF 절대 품질
  macro_align    × 0.25  → 현재 국면 추천 섹터 일치도
  momentum_score × 0.20  → 모멘텀 강도
  rs_score       × 0.20  → 상대강도
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


class OpportunityScoreCalculator(AbstractScoreCalculator):
    """
    투자 기회 매력도 점수 계산기

    여러 ETF를 비교할 때 순위를 매기는 데 사용.
    높은 점수 = 현재 국면에서 가장 매력적인 ETF.
    """

    def calculate(
        self,
        analysis: AnalysisResult,
        state: PortfolioState,
        config: DecisionConfig,
    ) -> Tuple[float, List[Contribution]]:
        w = config.opportunity_score_weights
        contributions: List[Contribution] = []

        # 1. ETF 절대 품질
        c1 = self._make_contribution(
            factor="etf_score",
            raw_value=analysis.etf_score,
            weight=w.get("etf_score", 0.35),
            positive_threshold=60,
            label_positive="ETF 품질 우수 — 모멘텀·샤프·유동성 확인",
            label_negative="ETF 품질 미흡 — 대안 탐색 권장",
        )
        contributions.append(c1)

        # 2. 현재 국면 매크로 정합성 (sector_rank → 점수)
        rank = analysis.sector_rank
        align_scores = config.macro_align_scores
        if rank == 1:
            align_raw = float(align_scores.get("rank_1", 100))
            align_interp = f"현재 국면({analysis.macro_state}) 1순위 추천 섹터 — 최고 정합"
            a_dir = "↑"
        elif rank == 2:
            align_raw = float(align_scores.get("rank_2", 80))
            align_interp = f"현재 국면 2순위 — 높은 정합"
            a_dir = "↑"
        elif rank == 3:
            align_raw = float(align_scores.get("rank_3", 60))
            align_interp = f"현재 국면 3순위 — 보통 정합"
            a_dir = "→"
        elif rank == 4:
            align_raw = float(align_scores.get("rank_4", 40))
            align_interp = f"현재 국면 4순위 — 낮은 정합"
            a_dir = "↓"
        elif rank == 5:
            align_raw = float(align_scores.get("rank_5", 20))
            align_interp = f"현재 국면 5순위 — 부정합"
            a_dir = "↓"
        else:
            align_raw = float(align_scores.get("default", 0))
            align_interp = f"현재 국면 미추천 섹터 — 정합 없음"
            a_dir = "↓"

        c2 = Contribution(
            factor="macro_align",
            raw_value=align_raw,
            weight=w.get("macro_align", 0.25),
            contribution=align_raw * w.get("macro_align", 0.25),
            direction=a_dir,
            interpretation=align_interp,
        )
        contributions.append(c2)

        # 3. 모멘텀
        c3 = self._make_contribution(
            factor="momentum_score",
            raw_value=analysis.momentum_score,
            weight=w.get("momentum_score", 0.20),
            positive_threshold=55,
            label_positive="모멘텀 강세 — 추격 매수 시 유리",
            label_negative="모멘텀 약세 — 진입 타이밍 재검토",
        )
        contributions.append(c3)

        # 4. 상대강도
        c4 = self._make_contribution(
            factor="rs_score",
            raw_value=analysis.rs_score,
            weight=w.get("rs_score", 0.20),
            positive_threshold=55,
            label_positive="섹터 상대강도 우수 — 선도 섹터 확인",
            label_negative="섹터 상대강도 열위 — 순환 시기 고려",
        )
        contributions.append(c4)

        # 최종 점수
        score = sum(c.contribution for c in contributions)
        return self.clamp(score), contributions
