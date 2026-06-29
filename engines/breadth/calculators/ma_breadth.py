"""
engines/breadth/calculators/ma_breadth.py
MABreadthCalculator — 지표 4, 5, 6

% Stocks Above MA (이동평균 상회 비율)

4. % Above 20MA  → 단기 강도 (모멘텀)
5. % Above 50MA  → 중기 강도 (추세 확인)
6. % Above 200MA → 장기 강도 (핵심 — 강세/약세 시장 구분선)

해석 기준 (공통):
- 75% 이상: 과열 (단기 조정 가능성)
- 60~75%:   건강한 강세
- 40~60%:   중립
- 25~40%:   약세
- 25% 이하:  극단적 약세

% Above 200MA가 가장 중요:
- 50% 이상: 강세장
- 50% 이하: 약세장으로 전환 중
"""

from __future__ import annotations
from typing import List

from engines.breadth.data_models import BreadthConfig, BreadthInput, ComponentScore
from engines.breadth.calculators.base import AbstractBreadthCalculator


class MABreadthCalculator(AbstractBreadthCalculator):
    """
    이동평균 상회 비율 3개 지표 계산기.
    각각 독립적인 ComponentScore를 반환.
    """

    def calculate(
        self,
        inp: BreadthInput,
        config: BreadthConfig,
    ) -> List[ComponentScore]:
        scores: List[ComponentScore] = []
        cur = inp.current

        # ── 4. % Above 20MA (단기) ─────────────────
        norm_20 = config.normalization.get("pct_above_20ma", {"lo": 25.0, "hi": 75.0})
        score_20 = self.normalize(cur.pct_above_20ma, norm_20["lo"], norm_20["hi"])
        w_20 = config.component_weights.get("pct_above_20ma", 0.08)

        scores.append(self._make_score(
            name="pct_above_20ma",
            raw_value=round(cur.pct_above_20ma, 1),
            normalized=round(score_20, 2),
            weight=w_20,
            positive_label=f"{cur.pct_above_20ma:.1f}% 종목이 20MA 상회 — 단기 모멘텀 강세",
            negative_label=f"{cur.pct_above_20ma:.1f}% 종목이 20MA 상회 — 단기 모멘텀 약세",
            neutral_label=f"{cur.pct_above_20ma:.1f}% 종목이 20MA 상회 — 단기 중립",
        ))

        # ── 5. % Above 50MA (중기) ─────────────────
        norm_50 = config.normalization.get("pct_above_50ma", {"lo": 25.0, "hi": 75.0})
        score_50 = self.normalize(cur.pct_above_50ma, norm_50["lo"], norm_50["hi"])
        w_50 = config.component_weights.get("pct_above_50ma", 0.12)

        scores.append(self._make_score(
            name="pct_above_50ma",
            raw_value=round(cur.pct_above_50ma, 1),
            normalized=round(score_50, 2),
            weight=w_50,
            positive_label=f"{cur.pct_above_50ma:.1f}% 종목이 50MA 상회 — 중기 추세 건강",
            negative_label=f"{cur.pct_above_50ma:.1f}% 종목이 50MA 하회 → 중기 추세 약화",
            neutral_label=f"{cur.pct_above_50ma:.1f}% 종목이 50MA 상회 — 중기 중립",
        ))

        # ── 6. % Above 200MA (장기, 핵심) ────────────
        norm_200 = config.normalization.get("pct_above_200ma", {"lo": 25.0, "hi": 75.0})
        score_200 = self.normalize(cur.pct_above_200ma, norm_200["lo"], norm_200["hi"])
        w_200 = config.component_weights.get("pct_above_200ma", 0.18)

        if cur.pct_above_200ma >= 60:
            long_label = f"{cur.pct_above_200ma:.1f}% 종목이 200MA 상회 — 강세장 확인"
        elif cur.pct_above_200ma >= 50:
            long_label = f"{cur.pct_above_200ma:.1f}% 종목이 200MA 상회 — 강세장 유지 중"
        elif cur.pct_above_200ma >= 40:
            long_label = f"{cur.pct_above_200ma:.1f}% 종목이 200MA 상회 — 약세장 진입 경계"
        else:
            long_label = f"{cur.pct_above_200ma:.1f}% 종목이 200MA 상회 — 약세장 확인"

        scores.append(self._make_score(
            name="pct_above_200ma",
            raw_value=round(cur.pct_above_200ma, 1),
            normalized=round(score_200, 2),
            weight=w_200,
            positive_label=long_label,
            negative_label=long_label,
            neutral_label=long_label,
        ))

        return scores
