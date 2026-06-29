"""
validation/health/engine_health_scorer.py
Engine 건강도 점수 — 정확도 × 일관성 × 보정 × 기여도 안정성
"""
from __future__ import annotations
import math
from typing import Dict, List
from validation.data_models import (
    DecisionRecord, AttributionResult,
    EngineHealthScore, HealthGrade
)

def _mean(xs): return sum(xs)/len(xs) if xs else 0.0
def _std(xs):
    if len(xs) < 2: return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x-m)**2 for x in xs)/(len(xs)-1))

WEIGHTS = {"accuracy": 0.40, "consistency": 0.30,
           "calibration": 0.20, "contribution": 0.10}

ENGINE_FIELDS = {
    "Macro":     "macro_score",
    "Breadth":   "breadth_score",
    "RS":        "rs_score",
    "Rotation":  "rotation_score",
    "Portfolio": "portfolio_score",
    "Risk":      "risk_score",
}

def _grade(score: float) -> HealthGrade:
    if score >= 80: return HealthGrade.EXCELLENT
    if score >= 65: return HealthGrade.GOOD
    if score >= 50: return HealthGrade.FAIR
    if score >= 35: return HealthGrade.POOR
    return HealthGrade.CRITICAL

def _trend(scores: List[float]) -> str:
    if len(scores) < 10: return "→"
    first = _mean(scores[:len(scores)//2])
    second = _mean(scores[len(scores)//2:])
    if second - first > 3: return "↑"
    if first - second > 3: return "↓"
    return "→"


class EngineHealthScorer:
    """
    Health_i = 0.40×accuracy + 0.30×consistency + 0.20×calibration + 0.10×contribution
    """

    def score(
        self,
        records: List[DecisionRecord],
        attribution: AttributionResult,
    ) -> Dict[str, EngineHealthScore]:
        results: Dict[str, EngineHealthScore] = {}

        # Build attribution lookup
        attr_map = {a.engine: a for a in attribution.engine_attributions}

        for engine, field in ENGINE_FIELDS.items():
            signals = [getattr(r, field, 50.0) for r in records]

            # Accuracy: % times signal direction correct
            accuracy = sum(
                1 for r, s in zip(records, signals)
                if (r.actual_return > 0) == (s > 50)
            ) / max(len(records), 1) * 100

            # Consistency: 1 - CV (coefficient of variation)
            m = _mean(signals) or 1e-9
            cv = _std(signals) / abs(m)
            consistency = max(0.0, (1 - cv) * 100)

            # Calibration: based on confidence vs accuracy correlation
            # Proxy: 100 - |mean_signal - win_rate*100|
            win_rate = sum(1 for r in records if r.correct) / max(len(records), 1)
            calibration = max(0.0, 100 - abs(_mean(signals) - win_rate * 100))

            # Contribution from attribution
            attr = attr_map.get(engine)
            contribution = attr.contribution_pct if attr else 50.0

            overall = (
                WEIGHTS["accuracy"]     * accuracy +
                WEIGHTS["consistency"]  * consistency +
                WEIGHTS["calibration"]  * calibration +
                WEIGHTS["contribution"] * contribution
            )

            results[engine] = EngineHealthScore(
                engine       = engine,
                accuracy     = round(accuracy, 1),
                consistency  = round(consistency, 1),
                calibration  = round(calibration, 1),
                contribution = round(contribution, 1),
                overall      = round(overall, 1),
                grade        = _grade(overall),
                trend        = _trend(signals),
            )

        return results
