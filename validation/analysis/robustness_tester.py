"""
validation/analysis/robustness_tester.py
Threshold 변화에 대한 전략 안정성 검증
"""
from __future__ import annotations
import math
from typing import List
from validation.data_models import (
    DecisionRecord, RobustnessCell, RobustnessResult
)

THRESHOLDS = {
    "BUY_threshold":  50.0,
    "SELL_threshold": 40.0,
    "High_confidence": 70.0,
    "Low_confidence":  30.0,
    "Macro_bullish":   60.0,
}
PERTURBATIONS = [-30.0, -20.0, -10.0, +10.0, +20.0, +30.0]

def _mean(xs): return sum(xs)/len(xs) if xs else 0.0
def _std(xs):
    if len(xs) < 2: return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x-m)**2 for x in xs)/(len(xs)-1))
def _sharpe(rets):
    s = _std(rets)
    return (_mean(rets)/(0.045/252))/s*math.sqrt(252) if s>1e-9 else 0.0


class RobustnessTester:
    """
    Checks whether strategy returns are stable when threshold parameters
    are varied by ±10%~30%. Stable = |Sharpe change| < 10% of base.
    """

    def test(self, records: List[DecisionRecord]) -> RobustnessResult:
        if not records:
            return RobustnessResult(
                cells=[], robustness_score=0.0,
                fragile_params=list(THRESHOLDS), stable_params=[],
                xai_summary="데이터 없음",
            )

        base_rets   = [r.actual_return for r in records]
        base_sharpe = _sharpe(base_rets) or 1e-9

        cells: List[RobustnessCell] = []

        for param, base_val in THRESHOLDS.items():
            for delta_pct in PERTURBATIONS:
                perturbed_val = base_val * (1 + delta_pct/100)
                # Proxy: records that cross the threshold differently
                adj_rets = []
                for r in records:
                    sig = r.confidence
                    was_buy = sig >= base_val
                    now_buy = sig >= perturbed_val
                    if was_buy != now_buy:
                        # Signal flip → return inverted
                        adj_rets.append(-r.actual_return * 0.5)
                    else:
                        adj_rets.append(r.actual_return)

                new_sharpe = _sharpe(adj_rets)
                change_pct = abs(new_sharpe - base_sharpe) / abs(base_sharpe) * 100
                stable     = change_pct < 10.0

                cells.append(RobustnessCell(
                    parameter=param,
                    delta_pct=delta_pct,
                    sharpe_base=round(base_sharpe, 4),
                    sharpe_perturbed=round(new_sharpe, 4),
                    stable=stable,
                ))

        stable_cnt = sum(1 for c in cells if c.stable)
        score = stable_cnt / max(len(cells), 1) * 100

        # Identify fragile vs stable params
        param_stability = {}
        for p in THRESHOLDS:
            p_cells = [c for c in cells if c.parameter == p]
            param_stability[p] = sum(1 for c in p_cells if c.stable) / len(p_cells)

        fragile = [p for p, s in param_stability.items() if s < 0.5]
        stable_params = [p for p, s in param_stability.items() if s >= 0.7]

        xai = (f"안정성 점수: {score:.1f}% | "
               f"취약 파라미터: {', '.join(fragile) or '없음'} | "
               f"안정 파라미터: {', '.join(stable_params) or '없음'}")

        return RobustnessResult(
            cells=cells,
            robustness_score=round(score, 1),
            fragile_params=fragile,
            stable_params=stable_params,
            xai_summary=xai,
        )
