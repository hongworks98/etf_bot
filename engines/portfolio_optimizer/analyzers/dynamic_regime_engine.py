"""
engines/portfolio_optimizer/analyzers/dynamic_regime_engine.py
★ Dynamic Allocation Regime Engine — Aggressive / Balanced / Defensive.
"""
from __future__ import annotations
from engines.portfolio_optimizer.calculators.base import AbstractOptimizationCalculator
from engines.portfolio_optimizer.data_models import (
    AllocationRegime, OptimizationConfig, OptimizationInput,
)


class DynamicRegimeEngine(AbstractOptimizationCalculator):
    """
    Rules (in priority order):
    1. DEFENSIVE if macro_state in defensive_states OR health < defensive_health_max OR vix > defensive_vix_min
    2. AGGRESSIVE if macro_state in aggressive_states AND health > aggressive_health_min AND vix < aggressive_vix_max
    3. BALANCED otherwise
    """

    def detect(
        self,
        inp: OptimizationInput,
        cfg: OptimizationConfig,
    ) -> tuple[AllocationRegime, str]:
        vix    = inp.latest_vix()
        health = inp.market_health_score
        macro  = inp.macro_state

        reasons = []

        # Defensive check (highest priority)
        defensive_triggers = []
        if macro in cfg.defensive_states:
            defensive_triggers.append(f"Macro={macro}")
        if health < cfg.defensive_health_max:
            defensive_triggers.append(f"Health={health:.1f}<{cfg.defensive_health_max}")
        if vix > cfg.defensive_vix_min:
            defensive_triggers.append(f"VIX={vix:.1f}>{cfg.defensive_vix_min}")

        if defensive_triggers:
            explanation = (
                f"DEFENSIVE 체제 선택: {', '.join(defensive_triggers)}. "
                "방어 섹터(XLP, XLU, XLV) 비중 확대, 경기 민감 섹터 축소."
            )
            return AllocationRegime.DEFENSIVE, explanation

        # Aggressive check
        aggressive_ok = macro in cfg.aggressive_states
        health_ok     = health >= cfg.aggressive_health_min
        vix_ok        = vix <= cfg.aggressive_vix_max

        if aggressive_ok and health_ok and vix_ok:
            explanation = (
                f"AGGRESSIVE 체제 선택: Macro={macro}, "
                f"Health={health:.1f}>={cfg.aggressive_health_min}, "
                f"VIX={vix:.1f}<={cfg.aggressive_vix_max}. "
                "경기 민감 섹터(XLK, XLY, XLF) 비중 확대."
            )
            return AllocationRegime.AGGRESSIVE, explanation

        # Balanced default
        miss_reasons = []
        if not aggressive_ok:
            miss_reasons.append(f"Macro={macro} (not aggressive)")
        if not health_ok:
            miss_reasons.append(f"Health={health:.1f}<{cfg.aggressive_health_min}")
        if not vix_ok:
            miss_reasons.append(f"VIX={vix:.1f}>{cfg.aggressive_vix_max}")

        explanation = (
            f"BALANCED 체제 선택: {', '.join(miss_reasons) if miss_reasons else '중립 조건 충족'}. "
            "섹터 간 균형 배분."
        )
        return AllocationRegime.BALANCED, explanation
