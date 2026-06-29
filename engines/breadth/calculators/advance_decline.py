"""
engines/breadth/calculators/advance_decline.py
AdvanceDeclineCalculator — 지표 1, 2

1. AD Ratio (10일 EMA)
   = Advances / (Advances + Declines) × 100
   → 10일 EMA로 스무딩 → 단기 시장 폭 강도

2. AD Line Trend
   = 누적 순 상승 종목 수의 기울기
   → 시장 폭의 방향성 (지수와 괴리 여부 탐지 기초)
"""

from __future__ import annotations
from typing import List

from engines.breadth.data_models import BreadthConfig, BreadthInput, ComponentScore
from engines.breadth.calculators.base import AbstractBreadthCalculator


class AdvanceDeclineCalculator(AbstractBreadthCalculator):
    """
    Advance/Decline 기반 2개 지표 계산.

    AD Ratio: 단기(10일) 시장 내부 강도
    AD Line:  중·장기 방향성 (누적 폭 추이)
    """

    def calculate(
        self,
        inp: BreadthInput,
        config: BreadthConfig,
    ) -> List[ComponentScore]:
        scores: List[ComponentScore] = []

        # ── 1. AD Ratio (10일 EMA) ─────────────────────

        # 역사 데이터에서 AD Ratio 시계열 추출
        all_data = inp.history + [inp.current]  # 과거 → 현재 순
        ad_ratios = [d.ad_ratio for d in all_data]

        ema_period = config.ema_period  # 기본 10
        current_ema = self.ema(ad_ratios, ema_period)

        norm_cfg = config.normalization.get("ad_ratio", {"lo": 35.0, "hi": 65.0})
        ad_score = self.normalize(current_ema, norm_cfg["lo"], norm_cfg["hi"])
        w_ad = config.component_weights.get("ad_ratio", 0.20)

        scores.append(self._make_score(
            name="ad_ratio",
            raw_value=round(current_ema, 2),
            normalized=round(ad_score, 2),
            weight=w_ad,
            positive_label=f"AD Ratio {current_ema:.1f}% (EMA{ema_period}) — 상승 종목 우위, 폭 건강",
            negative_label=f"AD Ratio {current_ema:.1f}% (EMA{ema_period}) — 하락 종목 우위, 폭 약화",
            neutral_label=f"AD Ratio {current_ema:.1f}% (EMA{ema_period}) — 균형 상태",
        ))

        # ── 2. AD Line Trend (누적 기울기) ────────────────

        if len(inp.history) >= 5:
            # 누적 AD Line 계산
            ad_line = []
            cumulative = 0
            for d in all_data:
                cumulative += d.net_advance
                ad_line.append(cumulative)

            # 최근 21일(1개월) 기울기 추정
            window = min(21, len(ad_line))
            recent = ad_line[-window:]
            if window >= 2:
                # 단순 기울기: (끝 - 시작) / 기간
                ad_slope = (recent[-1] - recent[0]) / (window - 1)
            else:
                ad_slope = 0.0

            # 기울기 정규화 (총 종목 수 스케일 보정)
            scale = max(inp.total_components * 0.1, 1.0)  # 50 (S&P500 기준)
            ad_slope_normalized = ad_slope / scale  # -1~+1 범위로 압축

            norm_cfg2 = config.normalization.get("ad_line_trend", {"lo": -20.0, "hi": 20.0})
            scaled_slope = ad_slope_normalized * 20  # -20~+20 범위로 매핑
            ad_line_score = self.normalize(scaled_slope, norm_cfg2["lo"], norm_cfg2["hi"])
        else:
            ad_slope = 0.0
            ad_line_score = 50.0  # 데이터 부족 → 중립

        w_adl = config.component_weights.get("ad_line_trend", 0.10)
        scores.append(self._make_score(
            name="ad_line_trend",
            raw_value=round(ad_slope, 1),
            normalized=round(ad_line_score, 2),
            weight=w_adl,
            positive_label=f"AD Line 상승 추세 (기울기 {ad_slope:+.0f}종목/일) — 내부 건강",
            negative_label=f"AD Line 하락 추세 (기울기 {ad_slope:+.0f}종목/일) — 내부 약화",
            neutral_label=f"AD Line 횡보 (기울기 {ad_slope:+.0f}종목/일) — 방향성 불명확",
        ))

        return scores
