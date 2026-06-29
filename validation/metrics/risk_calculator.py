"""
validation/metrics/risk_calculator.py
7대 리스크 지표 계산기 (pure Python, no numpy)
"""
from __future__ import annotations
import math
from typing import List
from validation.data_models import RiskMetrics


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0

def _std(xs: List[float]) -> float:
    if len(xs) < 2: return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x-m)**2 for x in xs) / (len(xs)-1))


class RiskCalculator:
    """
    Computes CAGR, Volatility, Sharpe, Sortino, MaxDD, Calmar, Ulcer Index.
    Input: daily portfolio return series (0-indexed, len = N trade days).
    """

    def calculate(
        self,
        daily_returns: List[float],
        risk_free_rate: float = 0.045,
    ) -> RiskMetrics:
        if not daily_returns:
            return self._zero_metrics()

        n = len(daily_returns)
        rf_daily = risk_free_rate / 252

        # ── CAGR ─────────────────────────────────────────────────────
        cum_return = 1.0
        for r in daily_returns:
            cum_return *= (1 + r)
        cagr = cum_return ** (252 / n) - 1.0

        # ── Volatility ───────────────────────────────────────────────
        vol = _std(daily_returns) * math.sqrt(252)

        # ── Sharpe ───────────────────────────────────────────────────
        excess = [r - rf_daily for r in daily_returns]
        sharpe_raw = _std(excess)
        sharpe = (_mean(excess) / sharpe_raw * math.sqrt(252)) if sharpe_raw > 1e-9 else 0.0

        # ── Sortino ──────────────────────────────────────────────────
        neg = [r for r in daily_returns if r < 0]
        down_std = _std(neg) * math.sqrt(252) if len(neg) >= 2 else vol or 1e-9
        sortino = (cagr - risk_free_rate) / down_std if down_std > 1e-9 else 0.0

        # ── Max Drawdown ─────────────────────────────────────────────
        peak = 1.0
        port = 1.0
        max_dd = 0.0
        dd_series = []
        for r in daily_returns:
            port *= (1 + r)
            if port > peak:
                peak = port
            dd = (peak - port) / peak
            dd_series.append(dd)
            if dd > max_dd:
                max_dd = dd

        # ── Calmar ───────────────────────────────────────────────────
        calmar = cagr / max_dd if max_dd > 1e-9 else 0.0

        # ── Ulcer Index ──────────────────────────────────────────────
        ulcer = math.sqrt(_mean([d**2 for d in dd_series])) if dd_series else 0.0

        # ── VaR 95% ──────────────────────────────────────────────────
        sorted_r = sorted(daily_returns)
        var_idx  = max(0, int(len(sorted_r) * 0.05) - 1)
        var_95   = sorted_r[var_idx]

        pos_days = sum(1 for r in daily_returns if r > 0) / n

        return RiskMetrics(
            cagr         = round(cagr, 6),
            volatility   = round(vol, 6),
            sharpe       = round(sharpe, 4),
            sortino      = round(sortino, 4),
            calmar       = round(calmar, 4),
            max_drawdown = round(max_dd, 6),
            ulcer_index  = round(ulcer, 6),
            var_95       = round(var_95, 6),
            best_day     = round(max(daily_returns), 6),
            worst_day    = round(min(daily_returns), 6),
            positive_days = round(pos_days, 4),
        )

    @staticmethod
    def _zero_metrics() -> RiskMetrics:
        return RiskMetrics(
            cagr=0.0, volatility=0.0, sharpe=0.0, sortino=0.0,
            calmar=0.0, max_drawdown=0.0, ulcer_index=0.0,
            var_95=0.0, best_day=0.0, worst_day=0.0, positive_days=0.0,
        )
