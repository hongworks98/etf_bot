"""
validation/backtesting/benchmark_comparator.py
Benchmark Comparison — SPY / QQQ vs Strategy
"""
from __future__ import annotations
import math
from typing import List, Dict
from validation.data_models import BacktestResult, BenchmarkResult

def _mean(xs): return sum(xs)/len(xs) if xs else 0.0
def _var(xs):
    if len(xs) < 2: return 0.0
    m = _mean(xs)
    return sum((x-m)**2 for x in xs) / (len(xs)-1)
def _cov(xs,ys):
    if len(xs) < 2: return 0.0
    mx,my = _mean(xs),_mean(ys)
    return sum((x-mx)*(y-my) for x,y in zip(xs,ys))/(len(xs)-1)
def _std(xs): return math.sqrt(_var(xs)) if _var(xs)>0 else 0.0


class BenchmarkComparator:
    """
    Computes alpha, beta, information ratio, tracking error vs each benchmark.
    """

    def compare(
        self,
        strategy_returns: List[float],
        benchmark_prices: Dict[str, List[float]],
    ) -> List[BenchmarkResult]:
        results = []
        for bench_id, prices in benchmark_prices.items():
            bench_rets = [(prices[i]/prices[i-1])-1.0
                          for i in range(1, len(prices))]
            results.append(self._compare_one(bench_id, strategy_returns, bench_rets))
        return results

    def _compare_one(
        self,
        bench_id: str,
        strat: List[float],
        bench: List[float],
    ) -> BenchmarkResult:
        n = min(len(strat), len(bench))
        if n < 5:
            return BenchmarkResult(
                benchmark_id=bench_id, benchmark_return=0.0, strategy_return=0.0,
                alpha=0.0, beta=1.0, information_ratio=0.0,
                tracking_error=0.0, win_rate_vs_bench=0.0, correlation=0.0,
            )

        s = strat[:n]
        b = bench[:n]

        strat_total = sum(s)
        bench_total = sum(b)
        beta  = _cov(s, b) / _var(b) if _var(b) > 1e-9 else 1.0
        alpha = strat_total - beta * bench_total

        diff  = [si - bi for si, bi in zip(s, b)]
        te    = _std(diff) * math.sqrt(252)
        ir    = (_mean(diff) * 252 / te) if te > 1e-9 else 0.0

        # Correlation
        vs = _var(s); vb = _var(b)
        corr = _cov(s,b) / math.sqrt(vs*vb) if vs*vb > 1e-9 else 0.0

        win_rate = sum(1 for si,bi in zip(s,b) if si > bi) / n

        return BenchmarkResult(
            benchmark_id       = bench_id,
            benchmark_return   = round(bench_total, 6),
            strategy_return    = round(strat_total, 6),
            alpha              = round(alpha, 6),
            beta               = round(beta, 4),
            information_ratio  = round(ir, 4),
            tracking_error     = round(te, 6),
            win_rate_vs_bench  = round(win_rate, 4),
            correlation        = round(corr, 4),
        )
