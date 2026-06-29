"""
validation/analysis/sensitivity_analyzer.py
Weight 변경 영향 민감도 분석 — ±10/20% 그리드 탐색
"""
from __future__ import annotations
import math
from typing import List
from validation.data_models import (
    DecisionRecord, SensitivityCell, SensitivityResult
)

ENGINES = {
    "Macro":     "macro_score",
    "Breadth":   "breadth_score",
    "RS":        "rs_score",
    "Rotation":  "rotation_score",
    "Portfolio": "portfolio_score",
}
DELTAS = [-20.0, -10.0, 0.0, +10.0, +20.0]

def _mean(xs): return sum(xs)/len(xs) if xs else 0.0
def _std(xs):
    if len(xs) < 2: return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x-m)**2 for x in xs) / (len(xs)-1))

def _sharpe(rets, rf=0.045/252):
    s = _std(rets)
    return (_mean(rets)-rf)/s*math.sqrt(252) if s > 1e-9 else 0.0


class SensitivityAnalyzer:
    """
    For each engine, perturbs its score by ±delta% and re-evaluates
    how the aggregate confidence (proxy for return) changes.
    """

    def analyze(self, records: List[DecisionRecord]) -> SensitivityResult:
        if not records:
            return SensitivityResult(
                grid=[], most_sensitive_engine="N/A",
                least_sensitive_engine="N/A", max_sharpe_engine="N/A",
                xai_summary="데이터 없음",
            )

        base_rets = [r.actual_return for r in records]
        base_sharpe = _sharpe(base_rets)
        base_ret    = _mean(base_rets)
        base_vol    = _std(base_rets)

        grid: List[SensitivityCell] = []
        # sensitivity = max |Sharpe change| across delta grid, per engine
        engine_sensitivity = {}

        for engine, field in ENGINES.items():
            max_abs_delta = 0.0
            best_sharpe_delta = 0.0

            for delta_pct in DELTAS:
                # Perturb: add delta to each signal, re-compute proxy return
                # Proxy: weight signal toward actual_return via correlation
                perturbed_rets = []
                for r in records:
                    base_sig  = getattr(r, field, 50.0)
                    perturbed = min(100.0, max(0.0, base_sig * (1 + delta_pct/100)))
                    # Scaled contribution change
                    sig_adj   = (perturbed - base_sig) / 100.0 * 0.01
                    perturbed_rets.append(r.actual_return + sig_adj)

                new_sharpe = _sharpe(perturbed_rets)
                new_ret    = _mean(perturbed_rets)
                new_vol    = _std(perturbed_rets)

                sharpe_change = new_sharpe - base_sharpe
                ret_change    = new_ret    - base_ret
                risk_change   = new_vol    - base_vol

                if abs(sharpe_change) > max_abs_delta:
                    max_abs_delta = abs(sharpe_change)
                if sharpe_change > best_sharpe_delta:
                    best_sharpe_delta = sharpe_change

                grid.append(SensitivityCell(
                    engine=engine, delta_pct=delta_pct,
                    sharpe_change=round(sharpe_change, 4),
                    return_change=round(ret_change, 6),
                    risk_change  =round(risk_change, 6),
                ))

            engine_sensitivity[engine] = (max_abs_delta, best_sharpe_delta)

        most_sensitive  = max(engine_sensitivity, key=lambda e: engine_sensitivity[e][0])
        least_sensitive = min(engine_sensitivity, key=lambda e: engine_sensitivity[e][0])
        max_sharpe_eng  = max(engine_sensitivity, key=lambda e: engine_sensitivity[e][1])

        xai = (f"가장 민감: {most_sensitive} | "
               f"가장 안정: {least_sensitive} | "
               f"Sharpe 최대 개선 Engine: {max_sharpe_eng}")

        return SensitivityResult(
            grid=grid,
            most_sensitive_engine=most_sensitive,
            least_sensitive_engine=least_sensitive,
            max_sharpe_engine=max_sharpe_eng,
            xai_summary=xai,
        )
