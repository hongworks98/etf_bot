"""
engines/breadth/analyzers/divergence_detector.py
DivergenceDetector — 지수 vs 시장 폭 괴리 탐지 (지표 10)

Bearish Divergence:
  S&P500 지수 상승 중 (index_change > +2%)
  Breadth(AD Ratio) 하락 중 (breadth_change < -5pt)
  → 지수는 오르나 내부 건강이 악화 → 조정 경고

Bullish Divergence:
  S&P500 지수 하락 중 (index_change < -2%)
  Breadth(AD Ratio) 상승 중 (breadth_change > +5pt)
  → 지수는 내리나 내부 건강이 개선 → 반등 신호

강도(Strength):
  |지수 변화 %| × |폭 변화 pt| / 10
  → 0~100 (클수록 신뢰도 높은 신호)
"""

from __future__ import annotations

from engines.breadth.data_models import (
    BreadthConfig,
    BreadthInput,
    DivergenceSignal,
    DivergenceType,
)


class DivergenceDetector:
    """
    지수 vs 시장 폭 괴리 신호 탐지기
    """

    def detect(
        self,
        inp: BreadthInput,
        config: BreadthConfig,
    ) -> DivergenceSignal:
        """
        Returns:
            DivergenceSignal (type=NONE if no divergence)
        """
        lookback = config.divergence_lookback  # 기본 20일
        idx_thr  = config.index_move_threshold    # 기본 2.0%
        bth_thr  = config.breadth_move_threshold  # 기본 5.0pt

        # 데이터 부족 → 판단 불가
        if len(inp.history) < lookback:
            return DivergenceSignal(
                type=DivergenceType.NONE,
                description="데이터 부족 — 괴리 탐지 불가",
            )

        # N일 전 데이터
        past = inp.history[-lookback]
        current = inp.current

        # 지수 변화율 (%)
        if past.index_price > 0:
            index_change_pct = (current.index_price - past.index_price) / past.index_price * 100
        else:
            return DivergenceSignal(type=DivergenceType.NONE, description="지수 데이터 없음")

        # 시장 폭 변화 (AD Ratio pt)
        breadth_change_pt = current.ad_ratio - past.ad_ratio

        # 강도 계산
        strength = min(abs(index_change_pct) * abs(breadth_change_pt) / 10.0 * 10, 100.0)

        # ── Bearish Divergence ───────────────────────
        if index_change_pct > idx_thr and breadth_change_pt < -bth_thr:
            return DivergenceSignal(
                type=DivergenceType.BEARISH,
                strength=round(strength, 1),
                lookback_days=lookback,
                index_change_pct=round(index_change_pct, 2),
                breadth_change_pt=round(breadth_change_pt, 2),
                description=(
                    f"Bearish Divergence: 지수 +{index_change_pct:.1f}% 상승 중 / "
                    f"AD Ratio {breadth_change_pt:.1f}pt 하락 — "
                    f"{'강력 경고' if strength >= config.divergence_strong_threshold else '주의 관찰 필요'}"
                ),
            )

        # ── Bullish Divergence ───────────────────────
        if index_change_pct < -idx_thr and breadth_change_pt > bth_thr:
            return DivergenceSignal(
                type=DivergenceType.BULLISH,
                strength=round(strength, 1),
                lookback_days=lookback,
                index_change_pct=round(index_change_pct, 2),
                breadth_change_pt=round(breadth_change_pt, 2),
                description=(
                    f"Bullish Divergence: 지수 {index_change_pct:.1f}% 하락 중 / "
                    f"AD Ratio +{breadth_change_pt:.1f}pt 상승 — "
                    f"{'강력 반등 신호' if strength >= config.divergence_strong_threshold else '반등 가능성 탐지'}"
                ),
            )

        # ── No Divergence ────────────────────────────
        return DivergenceSignal(
            type=DivergenceType.NONE,
            strength=0.0,
            lookback_days=lookback,
            index_change_pct=round(index_change_pct, 2),
            breadth_change_pt=round(breadth_change_pt, 2),
            description=(
                f"괴리 없음: 지수 {index_change_pct:+.1f}% / "
                f"AD Ratio {breadth_change_pt:+.1f}pt — 방향 일치"
            ),
        )
