"""
validation/backtesting/walk_forward.py
Walk-Forward Validation — 미래 데이터 방지
IS: 252bars, OOS: 63bars, Step: 21bars
"""
from __future__ import annotations
import math
from typing import List
from validation.data_models import (
    DecisionRecord, PriceHistory,
    WalkForwardWindow, WalkForwardResult
)

IS_BARS  = 252
OOS_BARS =  63
STEP     =  21

def _mean(xs): return sum(xs)/len(xs) if xs else 0.0
def _std(xs):
    if len(xs) < 2: return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x-m)**2 for x in xs) / (len(xs)-1))


def _sharpe(returns: List[float], rf_daily: float = 0.045/252) -> float:
    if len(returns) < 5:
        return 0.0
    excess = [r - rf_daily for r in returns]
    s = _std(excess)
    return (_mean(excess) / s * math.sqrt(252)) if s > 1e-9 else 0.0


class WalkForwardValidator:
    """
    Splits records into rolling IS/OOS windows.
    Each OOS window only uses information from IS window.
    """

    def validate(
        self,
        records: List[DecisionRecord],
    ) -> WalkForwardResult:
        n = len(records)
        if n < IS_BARS + OOS_BARS:
            # Not enough data — return degenerate result
            return WalkForwardResult(
                windows=[], avg_oos_sharpe=0.0, avg_degradation=0.0,
                stability_score=0.0, oos_consistent=False,
            )

        windows: List[WalkForwardWindow] = []
        start = 0
        wid   = 0

        while start + IS_BARS + OOS_BARS <= n:
            is_slice  = records[start : start + IS_BARS]
            oos_slice = records[start + IS_BARS : start + IS_BARS + OOS_BARS]

            is_rets   = [r.actual_return for r in is_slice]
            oos_rets  = [r.actual_return for r in oos_slice]

            is_sharpe  = _sharpe(is_rets)
            oos_sharpe = _sharpe(oos_rets)
            oos_ret    = sum(oos_rets)

            degradation = (oos_sharpe / is_sharpe) if abs(is_sharpe) > 1e-6 else 0.0

            windows.append(WalkForwardWindow(
                window_id   = wid,
                is_start    = start,
                is_end      = start + IS_BARS - 1,
                oos_start   = start + IS_BARS,
                oos_end     = start + IS_BARS + OOS_BARS - 1,
                is_sharpe   = round(is_sharpe, 4),
                oos_sharpe  = round(oos_sharpe, 4),
                oos_return  = round(oos_ret, 6),
                degradation = round(degradation, 4),
            ))
            start += STEP
            wid   += 1

        avg_oos  = _mean([w.oos_sharpe for w in windows])
        avg_deg  = _mean([w.degradation for w in windows])
        pct_pos  = sum(1 for w in windows if w.oos_sharpe > 0) / max(len(windows), 1)
        stab     = pct_pos * 100

        return WalkForwardResult(
            windows        = windows,
            avg_oos_sharpe = round(avg_oos, 4),
            avg_degradation= round(avg_deg, 4),
            stability_score= round(stab, 1),
            oos_consistent = pct_pos >= 0.70,
        )
