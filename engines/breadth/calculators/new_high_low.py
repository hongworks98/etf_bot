"""
engines/breadth/calculators/new_high_low.py
NewHighLowCalculator — 지표 3

New High / New Low Ratio
= New_Highs / (New_Highs + New_Lows) × 100

해석:
- 80% 이상: 신고가 압도 → 강세 확인
- 20% 이하: 신저가 압도 → 약세 확인
- 50% 기준: 팽팽한 균형

10일 EMA로 스무딩하여 단기 노이즈 제거
"""

from __future__ import annotations
from typing import List

from engines.breadth.data_models import BreadthConfig, BreadthInput, ComponentScore
from engines.breadth.calculators.base import AbstractBreadthCalculator


class NewHighLowCalculator(AbstractBreadthCalculator):
    """52주 New High/Low 비율 계산기"""

    def calculate(
        self,
        inp: BreadthInput,
        config: BreadthConfig,
    ) -> List[ComponentScore]:

        all_data = inp.history + [inp.current]

        # NH/NL 시계열 (10일 EMA 스무딩)
        nh_nl_series = [d.nh_nl_ratio for d in all_data]
        ema_period = config.ema_period
        nh_nl_ema = self.ema(nh_nl_series, ema_period)

        # 현재 원시값 (오늘)
        raw_nh_nl = inp.current.nh_nl_ratio

        norm_cfg = config.normalization.get("nh_nl_ratio", {"lo": 20.0, "hi": 80.0})
        score = self.normalize(nh_nl_ema, norm_cfg["lo"], norm_cfg["hi"])

        w = config.component_weights.get("nh_nl_ratio", 0.15)

        # 절대 수치 추가 설명
        nh = inp.current.new_highs
        nl = inp.current.new_lows
        detail = f"NH {nh} / NL {nl}"

        return [self._make_score(
            name="nh_nl_ratio",
            raw_value=round(nh_nl_ema, 2),
            normalized=round(score, 2),
            weight=w,
            positive_label=f"NH/NL {nh_nl_ema:.1f}% ({detail}) — 신고가 우위, 추세 강화",
            negative_label=f"NH/NL {nh_nl_ema:.1f}% ({detail}) — 신저가 우위, 추세 약화",
            neutral_label=f"NH/NL {nh_nl_ema:.1f}% ({detail}) — 균형 상태",
        )]
