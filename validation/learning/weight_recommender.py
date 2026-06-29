"""
validation/learning/weight_recommender.py
★★★★★ Adaptive Weight Recommendation Engine

경고: 이 모듈은 추천(Recommendation)만 한다.
      어떠한 경우에도 자동으로 Weight를 변경하지 않는다.
      Weight 변경은 반드시 사용자가 직접 수행해야 한다.
"""
from __future__ import annotations
from typing import Dict, List
from validation.data_models import (
    SensitivityResult, EngineHealthScore,
    WeightRecommendation
)

# 현재 기본 Weight (ConfidenceDecomposer와 동일)
DEFAULT_WEIGHTS = {
    "Macro":     25.0,
    "Breadth":   20.0,
    "RS":        22.0,
    "Rotation":  18.0,
    "Portfolio": 10.0,
    "Risk":       5.0,
}

MAX_DELTA = 5.0  # 최대 추천 변경폭 (포인트)


class WeightRecommender:
    """
    ★★★★★ RECOMMENDATION ONLY — 절대 자동 적용 금지 ★★★★★

    민감도 분석 + Engine 건강도를 결합하여 최적 Weight 후보를 추천한다.
    추천 이유와 예상 효과를 반드시 함께 제시한다.
    """

    def recommend(
        self,
        sensitivity:   SensitivityResult,
        health:        Dict[str, EngineHealthScore],
        current_weights: Dict[str, float] = None,
    ) -> List[WeightRecommendation]:
        """
        ★★★★★ 절대 자동 적용 금지 ★★★★★
        Returns a list of weight adjustment RECOMMENDATIONS.
        The caller MUST NOT apply these automatically.
        """
        current = current_weights or dict(DEFAULT_WEIGHTS)
        recommendations: List[WeightRecommendation] = []

        # Sensitivity: engines with positive upside → increase weight
        # Health: engines with poor health → reduce weight

        # Build sensitivity map: max Sharpe gain per engine
        sens_map: Dict[str, float] = {}
        for cell in sensitivity.grid:
            if cell.delta_pct > 0:
                prev = sens_map.get(cell.engine, 0.0)
                sens_map[cell.engine] = max(prev, cell.sharpe_change)

        for engine, curr_w in current.items():
            h = health.get(engine)
            if h is None:
                continue

            health_score = h.overall
            sens_upside  = sens_map.get(engine, 0.0)

            # Decision logic (RECOMMEND ONLY):
            if health_score >= 70 and sens_upside > 0.05:
                # Healthy + positive sensitivity → recommend increase
                delta = min(MAX_DELTA, sens_upside * 10)
                new_w = curr_w + delta
                reason = (
                    f"{engine} Engine 건강도 {health_score:.0f}/100 (우수) + "
                    f"민감도 분석에서 Weight +{sens_upside:.3f} Sharpe 개선 확인"
                )
                exp_sharpe = round(sens_upside * delta / MAX_DELTA, 4)
                exp_ret    = round(exp_sharpe * 0.005, 4)
                caveat     = "시장 체제 변화 시 재검토 필요. 반드시 백테스트 후 적용할 것."
                conf       = "High" if health_score >= 80 else "Medium"

            elif health_score < 50:
                # Poor health → recommend decrease
                delta = -min(MAX_DELTA, (50 - health_score) / 10)
                new_w = max(1.0, curr_w + delta)
                delta = new_w - curr_w
                reason = (
                    f"{engine} Engine 건강도 {health_score:.0f}/100 (저조) — "
                    f"정확도 {h.accuracy:.0f}%, 보정 오류 {100-h.calibration:.0f}pt 감지"
                )
                exp_sharpe = round(delta * (-0.01), 4)
                exp_ret    = round(exp_sharpe * 0.003, 4)
                caveat     = "Engine 진단 결과가 일시적 노이즈일 수 있음. 복수 기간 확인 후 결정."
                conf       = "Medium" if health_score >= 35 else "Low"

            else:
                # Healthy enough + no strong signal → no recommendation
                continue

            if abs(delta) < 0.5:
                continue  # 변화가 너무 작으면 추천하지 않음

            recommendations.append(WeightRecommendation(
                engine             = engine,
                current_weight     = round(curr_w, 2),
                recommended_weight = round(new_w, 2),
                delta              = round(delta, 2),
                reason             = reason,
                expected_sharpe_delta = exp_sharpe,
                expected_return_delta = exp_ret,
                confidence_level   = conf,
                caveat             = caveat,
            ))

        # Sort: largest expected Sharpe improvement first
        recommendations.sort(key=lambda r: -abs(r.expected_sharpe_delta))
        return recommendations
