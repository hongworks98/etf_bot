"""
engines/breadth/calculators/breadth_thrust.py
BreadthThrustCalculator — 지표 8

Zweig Breadth Thrust (Martin Zweig, 1986)

원리:
  10일 기간 동안 AD Ratio의 EMA가
  40% 미만 → 61.5% 초과로 급등하면
  강세장 초기 신호 (역사적으로 매우 희귀하고 신뢰도 높음)

구현:
  현재 10일 EMA를 기준으로
  - EMA > 61.5%:  Thrust 발동 → 100점
  - EMA > 55%:    잠재적 강세 → 75점
  - EMA 40~55%:   중립 → 선형 보간
  - EMA < 40%:    극단적 약세 → 0~10점

추가: 10일 전 EMA와 비교해 실제 Thrust 여부 탐지
  10일 전 EMA < 40% AND 현재 EMA > 61.5% → True Thrust
"""

from __future__ import annotations
from typing import List

from engines.breadth.data_models import BreadthConfig, BreadthInput, ComponentScore
from engines.breadth.calculators.base import AbstractBreadthCalculator


class BreadthThrustCalculator(AbstractBreadthCalculator):
    """Zweig Breadth Thrust 계산기"""

    def calculate(
        self,
        inp: BreadthInput,
        config: BreadthConfig,
    ) -> List[ComponentScore]:

        all_data = inp.history + [inp.current]
        ad_ratios = [d.ad_ratio for d in all_data]

        ema_period = config.ema_period  # 10
        thrust_hi  = config.thrust_signal_hi   # 61.5
        thrust_lo  = config.thrust_signal_lo   # 40.0

        # 현재 10일 EMA
        current_ema = self.ema(ad_ratios, ema_period)

        # 10일 전 EMA (True Thrust 탐지용)
        lookback = config.thrust_signal_hi  # YAML의 breadth_thrust.thrust_lookback 대신 ema_period 활용
        # lookback은 ema_period와 동일하게 사용
        true_thrust = False
        if len(ad_ratios) >= ema_period * 2:
            past_ratios = ad_ratios[:-ema_period]  # ema_period일 전까지
            past_ema = self.ema(past_ratios, ema_period)
            true_thrust = (past_ema < thrust_lo) and (current_ema > thrust_hi)

        # 점수 계산
        norm_cfg = config.normalization.get("breadth_thrust", {"lo": 38.0, "hi": 63.0})
        score = self.normalize(current_ema, norm_cfg["lo"], norm_cfg["hi"])

        w = config.component_weights.get("breadth_thrust", 0.07)

        # 해석
        if true_thrust:
            label = (
                f"Zweig Breadth Thrust 발동! EMA {current_ema:.1f}% "
                f"(이전 {past_ema:.1f}% → {current_ema:.1f}%) — 강세장 초기 강력 신호"
            )
            score = 100.0  # True Thrust = 만점
        elif current_ema > thrust_hi:
            label = f"Thrust EMA {current_ema:.1f}% — 과매수 진입, 강세 모멘텀 확인"
        elif current_ema > 55:
            label = f"Thrust EMA {current_ema:.1f}% — 잠재적 강세 신호 형성 중"
        elif current_ema > thrust_lo:
            label = f"Thrust EMA {current_ema:.1f}% — 중립 구간"
        else:
            label = f"Thrust EMA {current_ema:.1f}% — 과매도 구간 (반등 잠재력)"

        return [self._make_score(
            name="breadth_thrust",
            raw_value=round(current_ema, 2),
            normalized=round(score, 2),
            weight=w,
            positive_label=label,
            negative_label=label,
            neutral_label=label,
        )]
