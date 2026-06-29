"""
engines/breadth/calculators/participation.py
ParticipationCalculator — 지표 7

Market Participation Score
= Advancing Volume / Total Volume × 100

단순 AD Ratio(종목 수)와 달리 **거래량 가중**으로
"얼마나 많은 자금이 상승에 참여하는가?"를 측정.

해석:
- 65% 이상: 강한 상승 참여 — 상승 신뢰도 높음
- 50%:      균형
- 35% 이하: 하락에 거래량 집중 → 매도 압력 강함

보조 지표: 거래량 자체 수준도 체크
(평균 대비 낮은 거래량 상승 = 신뢰도 낮음)
"""

from __future__ import annotations
from typing import List

from engines.breadth.data_models import BreadthConfig, BreadthInput, ComponentScore
from engines.breadth.calculators.base import AbstractBreadthCalculator


class ParticipationCalculator(AbstractBreadthCalculator):
    """거래량 기반 시장 참여도 계산기"""

    def calculate(
        self,
        inp: BreadthInput,
        config: BreadthConfig,
    ) -> List[ComponentScore]:

        cur = inp.current
        raw_participation = cur.participation_ratio  # 0~100 (property)

        # 거래량 자체 수준 체크 (히스토리 있을 때)
        volume_bonus = 0.0
        if inp.history:
            avg_volume = sum(d.total_volume for d in inp.history) / len(inp.history)
            if avg_volume > 0 and cur.total_volume > 0:
                volume_ratio = cur.total_volume / avg_volume
                # 평균 대비 120% 이상 거래량이면 신뢰도 보너스 (+5점)
                # 평균 대비 80% 이하이면 신뢰도 페널티 (-5점)
                if volume_ratio >= 1.2:
                    volume_bonus = 5.0
                elif volume_ratio <= 0.8:
                    volume_bonus = -5.0

        # 정규화
        norm_cfg = config.normalization.get("participation", {"lo": 35.0, "hi": 65.0})
        base_score = self.normalize(raw_participation, norm_cfg["lo"], norm_cfg["hi"])
        score = max(0.0, min(100.0, base_score + volume_bonus))

        w = config.component_weights.get("participation", 0.10)

        # 설명 생성
        if raw_participation >= 60:
            label = f"상승 거래량 {raw_participation:.1f}% — 강한 매수 참여"
        elif raw_participation >= 50:
            label = f"상승 거래량 {raw_participation:.1f}% — 균형 상태"
        elif raw_participation >= 40:
            label = f"상승 거래량 {raw_participation:.1f}% — 매도 우위 시작"
        else:
            label = f"상승 거래량 {raw_participation:.1f}% — 강한 매도 압력"

        if volume_bonus > 0:
            label += " (고거래량 상승 — 신뢰도 ↑)"
        elif volume_bonus < 0:
            label += " (저거래량 — 신뢰도 ↓)"

        return [self._make_score(
            name="participation",
            raw_value=round(raw_participation, 2),
            normalized=round(score, 2),
            weight=w,
            positive_label=label,
            negative_label=label,
            neutral_label=label,
        )]
