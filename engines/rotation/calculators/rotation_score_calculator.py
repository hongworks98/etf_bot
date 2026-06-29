"""
engines/rotation/calculators/rotation_score_calculator.py
Rotation Score Calculator — 6-component weighted composite (0~100).
"""
from __future__ import annotations
from typing import List, Tuple
from engines.rotation.calculators.base import AbstractRotationCalculator
from engines.rotation.data_models import RotationAttribution, RotationConfig, RotationInput


class RotationScoreCalculator(AbstractRotationCalculator):
    """
    SRP: Computes only the rotation_score for a single ETF.
    Inputs: RS momentum, Macro alignment, Breadth support,
            Capital flow (pre-computed), Trend strength, Risk inverse.
    """

    def _macro_align_score(self, ticker: str, inp: RotationInput, cfg: RotationConfig) -> float:
        """Returns 0~100 macro alignment score."""
        expected = cfg.macro_expected_leaders.get(inp.macro_state, [])
        is_expected = ticker in expected
        rs_score = inp.get_rs_score(ticker)
        is_strong = rs_score >= 60.0

        if is_expected and is_strong:
            return cfg.macro_expected_and_strong
        if is_expected and not is_strong:
            return cfg.macro_expected_and_neutral
        if not is_expected and is_strong:
            return cfg.macro_unexpected_strong
        if not is_expected and not is_strong:
            return cfg.macro_unexpected_neutral
        return cfg.macro_unknown

    def _breadth_support(self, inp: RotationInput, cfg: RotationConfig) -> float:
        """Returns 0~100 breadth support score."""
        raw = (inp.breadth_score - 50.0) * cfg.breadth_scale + 50.0
        return self.clamp(raw)

    def _trend_strength(self, ticker: str, inp: RotationInput, cfg: RotationConfig) -> float:
        td = inp.trend_data.get(ticker)
        if td is None:
            return 50.0
        score = td.trend_score
        if not td.above_200ma:
            score *= cfg.below_200ma_penalty
        return self.clamp(score)

    def calculate(
        self,
        ticker: str,
        inp: RotationInput,
        capital_flow_score: float,
        risk_score: float,
        cfg: RotationConfig,
    ) -> Tuple[float, List[RotationAttribution]]:
        """
        Returns:
            rotation_score : 0~100
            attribution    : per-factor contribution list
        """
        rank_change = inp.get_rs_rank_change(ticker)
        acceleration = inp.get_rs_acceleration(ticker)
        rs_momentum_raw = float(rank_change) * (1.0 + abs(acceleration) * 10.0)
        rs_momentum = self.normalize(rs_momentum_raw, cfg.rs_momentum_lo, cfg.rs_momentum_hi)

        macro_align   = self._macro_align_score(ticker, inp, cfg)
        breadth_supp  = self._breadth_support(inp, cfg)
        trend_str     = self._trend_strength(ticker, inp, cfg)
        risk_inv      = self.clamp(100.0 - risk_score)

        raw_contributions = {
            "Relative Strength": rs_momentum    * cfg.rs_weight,
            "Macro Regime":      macro_align    * cfg.macro_weight,
            "Market Breadth":    breadth_supp   * cfg.breadth_weight,
            "Capital Flow":      capital_flow_score * cfg.flow_weight,
            "Trend":             trend_str      * cfg.trend_weight,
            "Risk/VIX":          risk_inv       * cfg.risk_weight,
        }
        rotation_score = self.clamp(sum(raw_contributions.values()))
        total = sum(raw_contributions.values()) or 1.0

        attributions: List[RotationAttribution] = []
        for factor, contrib in raw_contributions.items():
            pct = contrib / total * 100.0
            norm_val = contrib / (cfg.rs_weight if factor == "Relative Strength" else
                       cfg.macro_weight if factor == "Macro Regime" else
                       cfg.breadth_weight if factor == "Market Breadth" else
                       cfg.flow_weight if factor == "Capital Flow" else
                       cfg.trend_weight if factor == "Trend" else cfg.risk_weight)
            direction = "↑" if norm_val >= 55.0 else ("↓" if norm_val <= 45.0 else "→")
            attributions.append(RotationAttribution(
                factor=factor,
                score_contribution=round(contrib, 3),
                pct_contribution=round(pct, 1),
                direction=direction,
                interpretation=f"{factor}: normalized={norm_val:.1f}, contributes {pct:.1f}% of rotation signal",
            ))

        return rotation_score, attributions
