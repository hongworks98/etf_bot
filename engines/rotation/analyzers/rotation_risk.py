"""
engines/rotation/analyzers/rotation_risk.py
Rotation Risk Analyzer — measures risk inherent in acting on this rotation signal.
"""
from __future__ import annotations
from engines.rotation.calculators.base import AbstractRotationCalculator
from engines.rotation.data_models import RotationConfig, RotationInput, RotationStage


class RotationRiskAnalyzer(AbstractRotationCalculator):
    """
    SRP: Computes rotation_risk_score 0~100 (higher = riskier).
    Components:
      vix_risk:           current VIX level
      breadth_divergence: breadth vs price divergence
      macro_misalign:     macro doesn't support rotation
      speed_risk:         rotating too fast = higher risk
      stage_risk:         MATURE/WEAKENING = riskier to enter
    """

    def _vix_risk(self, inp: RotationInput, cfg: RotationConfig) -> float:
        vix = inp.aux_data.latest_vix()
        return self.normalize(vix, cfg.vix_lo, cfg.vix_hi)

    def _breadth_divergence_risk(self, inp: RotationInput, cfg: RotationConfig) -> float:
        """High price + low breadth = divergence risk."""
        breadth = inp.breadth_score
        if inp.breadth_trend == "DOWN" and breadth < 45.0:
            return self.normalize(50.0 - breadth, 0.0, 50.0)
        return self.normalize(50.0 - breadth, -10.0, 40.0)

    def _macro_misalign_risk(
        self, ticker: str, inp: RotationInput, cfg: RotationConfig
    ) -> float:
        """If macro doesn't support this sector, higher risk."""
        expected = cfg.macro_expected_leaders.get(inp.macro_state, [])
        if ticker not in expected and inp.macro_state != "Unknown":
            return 70.0
        return 20.0

    def _speed_risk(self, rotation_score: float, history: list, cfg: RotationConfig) -> float:
        """Fast-moving rotations carry more reversal risk."""
        if not history or len(history) < cfg.speed_lookback:
            return 30.0
        delta = abs(rotation_score - history[-cfg.speed_lookback])
        return self.normalize(delta, 0.0, 30.0)

    def _stage_risk(self, stage: RotationStage) -> float:
        """Late-stage or declining rotation = higher risk to enter."""
        risk_map = {
            RotationStage.EMERGING:  20.0,
            RotationStage.BUILDING:  15.0,
            RotationStage.CONFIRMED: 20.0,
            RotationStage.MATURE:    60.0,
            RotationStage.WEAKENING: 80.0,
            RotationStage.REVERSING: 95.0,
        }
        return risk_map.get(stage, 40.0)

    def compute(
        self,
        ticker: str,
        rotation_score: float,
        history: list,
        stage: RotationStage,
        inp: RotationInput,
        cfg: RotationConfig,
    ) -> float:
        """Returns rotation_risk_score 0~100."""
        rw = cfg.risk_weights
        vix_r   = self._vix_risk(inp, cfg)
        bread_r = self._breadth_divergence_risk(inp, cfg)
        macro_r = self._macro_misalign_risk(ticker, inp, cfg)
        speed_r = self._speed_risk(rotation_score, history, cfg)
        stage_r = self._stage_risk(stage)

        risk = (
            vix_r   * rw.get("vix_risk",           0.30) +
            bread_r * rw.get("breadth_divergence",  0.25) +
            macro_r * rw.get("macro_misalign",      0.20) +
            speed_r * rw.get("speed_risk",          0.15) +
            stage_r * rw.get("stage_risk",          0.10)
        )
        return self.clamp(risk)

    def confidence_from_signals(
        self, ticker: str, rotation_score: float,
        capital_flow_score: float, stage: RotationStage,
        inp: RotationInput, cfg: RotationConfig,
    ) -> float:
        """
        Confidence: how many signals agree? 0~100.
        High confidence when RS, Macro, Breadth, Trend, Flow all align.
        """
        cw = cfg.confidence_weights

        rs_score = inp.get_rs_score(ticker)
        rs_aligned    = 1.0 if rs_score >= 60.0 else (0.5 if rs_score >= 45.0 else 0.0)

        expected = cfg.macro_expected_leaders.get(inp.macro_state, [])
        macro_aligned = 1.0 if ticker in expected else (0.5 if inp.macro_state == "Unknown" else 0.0)

        breadth_aligned = 1.0 if inp.breadth_score >= 60.0 else (0.5 if inp.breadth_score >= 45.0 else 0.0)

        td = inp.trend_data.get(ticker)
        trend_aligned = 1.0 if (td and td.trend_direction == "UP") else (0.5 if not td else 0.0)

        flow_aligned = 1.0 if capital_flow_score >= 60.0 else (0.5 if capital_flow_score >= 45.0 else 0.0)

        confidence = (
            rs_aligned    * cw.get("rs_aligned",      0.25) +
            macro_aligned * cw.get("macro_aligned",   0.25) +
            breadth_aligned * cw.get("breadth_aligned", 0.20) +
            trend_aligned * cw.get("trend_aligned",   0.15) +
            flow_aligned  * cw.get("flow_aligned",    0.15)
        ) * 100.0
        return self.clamp(confidence)
