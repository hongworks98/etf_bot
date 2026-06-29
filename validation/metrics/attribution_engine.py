"""
validation/metrics/attribution_engine.py
Engine별 Alpha 기여도 계산 (simplified OLS)
"""
from __future__ import annotations
import math
from typing import List
from validation.data_models import (
    DecisionRecord, AttributionResult, EngineAttribution
)

ENGINES = ["macro","breadth","rs","rotation","portfolio","risk"]

def _mean(xs): return sum(xs)/len(xs) if xs else 0.0
def _cov(xs, ys):
    if len(xs) < 2: return 0.0
    mx, my = _mean(xs), _mean(ys)
    return sum((x-mx)*(y-my) for x,y in zip(xs,ys)) / (len(xs)-1)
def _var(xs):
    if len(xs) < 2: return 0.0
    m = _mean(xs)
    return sum((x-m)**2 for x in xs) / (len(xs)-1)
def _corr(xs, ys):
    v = math.sqrt(_var(xs)*_var(ys))
    return _cov(xs,ys)/v if v > 1e-9 else 0.0


class AttributionEngine:
    """
    Regresses actual_return on each engine's signal to estimate beta.
    attribution_i = beta_i × mean(signal_i)
    """

    ENGINE_FIELDS = {
        "Macro":      "macro_score",
        "Breadth":    "breadth_score",
        "Relative Strength": "rs_score",
        "Rotation":   "rotation_score",
        "Portfolio":  "portfolio_score",
        "Risk":       "risk_score",
    }

    def attribute(self, records: List[DecisionRecord]) -> AttributionResult:
        if not records:
            return self._empty()

        actual = [r.actual_return for r in records]
        attributions = []

        for engine, field in self.ENGINE_FIELDS.items():
            signals = [getattr(r, field, 50.0) for r in records]
            beta = _cov(signals, actual) / _var(signals) if _var(signals) > 1e-9 else 0.0
            corr = _corr(signals, actual)
            accuracy = sum(
                1 for r, s in zip(records, signals)
                if (r.actual_return > 0) == (s > 50)
            ) / len(records) * 100

            attributions.append(EngineAttribution(
                engine=engine,
                beta_coefficient=round(beta, 6),
                contribution_pct=0.0,   # filled below
                signal_accuracy=round(accuracy, 2),
                avg_signal=round(_mean(signals), 2),
                correlation_with_return=round(corr, 4),
            ))

        # Normalise contribution_pct
        total_abs = sum(abs(a.beta_coefficient) for a in attributions) or 1.0
        for a in attributions:
            a.contribution_pct = round(abs(a.beta_coefficient) / total_abs * 100, 2)

        # R² (mean engine score vs actual)
        all_signals = [_mean([getattr(r, f, 50.0) for f in self.ENGINE_FIELDS.values()])
                       for r in records]
        r2 = _corr(all_signals, actual) ** 2

        total_alpha = sum(a.beta_coefficient * a.avg_signal/100 for a in attributions)
        best  = max(attributions, key=lambda a: a.contribution_pct).engine
        worst = min(attributions, key=lambda a: a.signal_accuracy).engine

        xai = (f"Alpha 기여도 1위: {best} | "
               f"총 Alpha: {total_alpha*100:.2f}bps | R²: {r2:.3f}")

        return AttributionResult(
            engine_attributions=attributions,
            total_alpha=round(total_alpha, 6),
            r_squared=round(r2, 4),
            best_engine=best,
            worst_engine=worst,
            xai_summary=xai,
        )

    @staticmethod
    def _empty() -> AttributionResult:
        return AttributionResult(
            engine_attributions=[], total_alpha=0.0, r_squared=0.0,
            best_engine="N/A", worst_engine="N/A", xai_summary="데이터 없음",
        )
