"""
validation/analysis/monte_carlo_validator.py
Monte Carlo Validation — 500회 부트스트랩 → p-value
"""
from __future__ import annotations
import math, random
from typing import List
from validation.data_models import MCValidationResult

_rng = random.Random(42)

def _mean(xs): return sum(xs)/len(xs) if xs else 0.0
def _std(xs):
    if len(xs) < 2: return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x-m)**2 for x in xs)/(len(xs)-1))
def _sharpe(rets, rf=0.045/252):
    s = _std(rets)
    return (_mean(rets)-rf)/s*math.sqrt(252) if s>1e-9 else 0.0
def _cagr(rets):
    if not rets: return 0.0
    c = 1.0
    for r in rets: c *= (1+r)
    return c**(252/len(rets)) - 1.0
def _percentile(xs, p):
    s = sorted(xs); idx = max(0, int(len(s)*p/100)-1)
    return s[idx]


class MCValidator:
    """
    Bootstrap: sample with replacement from actual returns, compute Sharpe.
    p-value = fraction of simulations that beat actual strategy Sharpe.
    """
    N_SIMS = 500

    def validate(self, actual_returns: List[float]) -> MCValidationResult:
        if len(actual_returns) < 5:
            return self._empty()

        actual_sharpe = _sharpe(actual_returns)
        actual_cagr   = _cagr(actual_returns)
        n = len(actual_returns)

        sim_sharpes = []
        sim_cagrs   = []
        for _ in range(self.N_SIMS):
            sample = [_rng.choice(actual_returns) for _ in range(n)]
            sim_sharpes.append(_sharpe(sample))
            sim_cagrs.append(_cagr(sample))

        p_value = sum(1 for s in sim_sharpes if s >= actual_sharpe) / self.N_SIMS

        xai = (
            f"실제 Sharpe {actual_sharpe:.3f} | "
            f"시뮬 중앙값 {_percentile(sim_sharpes,50):.3f} | "
            f"p-value {p_value:.3f} | "
            f"{'★ 통계적 유의 (p<0.05)' if p_value < 0.05 else '통계적 비유의'}"
        )

        return MCValidationResult(
            n_simulations   = self.N_SIMS,
            strategy_sharpe = round(actual_sharpe, 4),
            sim_sharpe_p5   = round(_percentile(sim_sharpes, 5), 4),
            sim_sharpe_p50  = round(_percentile(sim_sharpes, 50), 4),
            sim_sharpe_p95  = round(_percentile(sim_sharpes, 95), 4),
            p_value         = round(p_value, 4),
            significant     = p_value < 0.05,
            strategy_cagr   = round(actual_cagr, 6),
            sim_cagr_p5     = round(_percentile(sim_cagrs, 5), 6),
            sim_cagr_p50    = round(_percentile(sim_cagrs, 50), 6),
            sim_cagr_p95    = round(_percentile(sim_cagrs, 95), 6),
            xai_summary     = xai,
        )

    @staticmethod
    def _empty() -> MCValidationResult:
        return MCValidationResult(
            n_simulations=0, strategy_sharpe=0.0,
            sim_sharpe_p5=0.0, sim_sharpe_p50=0.0, sim_sharpe_p95=0.0,
            p_value=1.0, significant=False,
            strategy_cagr=0.0, sim_cagr_p5=0.0, sim_cagr_p50=0.0, sim_cagr_p95=0.0,
            xai_summary="데이터 부족",
        )
