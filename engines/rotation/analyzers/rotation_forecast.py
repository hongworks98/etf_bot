"""
engines/rotation/analyzers/rotation_forecast.py
Rotation Forecast Analyzer — forward-looking probability 0~100.
"""
from __future__ import annotations
from engines.rotation.calculators.base import AbstractRotationCalculator
from engines.rotation.data_models import RotationConfig, RotationInput


class RotationForecastAnalyzer(AbstractRotationCalculator):
    """
    SRP: Estimates forward probability of rotation continuation.
    Uses leading indicators: RS acceleration, macro cycle phase,
    breadth trend, capital momentum, VIX trend.
    """

    def _rs_accel_score(self, ticker: str, inp: RotationInput, cfg: RotationConfig) -> float:
        accel = inp.get_rs_acceleration(ticker)
        return self.normalize(accel, cfg.rs_momentum_lo / 10.0, cfg.rs_momentum_hi / 10.0)

    def _macro_cycle_score(self, inp: RotationInput) -> float:
        """Macro direction alignment with cycle phase."""
        direction = inp.macro_direction
        macro_score = inp.macro_score
        if direction == "UP":
            return self.clamp(macro_score + 10.0)
        if direction == "DOWN":
            return self.clamp(macro_score - 20.0)
        return macro_score

    def _breadth_trend_score(self, inp: RotationInput) -> float:
        direction = inp.breadth_trend
        base = inp.breadth_score
        if direction == "UP":
            return self.clamp(base + 10.0)
        if direction == "DOWN":
            return self.clamp(base - 15.0)
        return base

    def _capital_momentum_score(self, ticker: str, capital_flow: float,
                                 inp: RotationInput) -> float:
        """Combine current capital flow with trend direction."""
        flow_trend = inp.aux_data.etf_flow_trend(ticker)
        momentum_boost = 5.0 if flow_trend > 0 else (-5.0 if flow_trend < 0 else 0.0)
        return self.clamp(capital_flow + momentum_boost)

    def _vix_trend_score(self, inp: RotationInput) -> float:
        """Falling VIX → positive for rotation; rising → negative."""
        vix_delta = inp.aux_data.vix_trend()
        if vix_delta < -2.0:
            return 70.0    # VIX falling fast → risk-on
        if vix_delta < 0.0:
            return 60.0    # VIX gently falling
        if vix_delta > 5.0:
            return 25.0    # VIX spiking
        if vix_delta > 2.0:
            return 35.0    # VIX rising
        return 50.0        # stable

    def compute(
        self,
        ticker: str,
        capital_flow_score: float,
        inp: RotationInput,
        cfg: RotationConfig,
    ) -> float:
        """Returns forecast_score 0~100."""
        fw = cfg.forecast_weights
        rs_accel   = self._rs_accel_score(ticker, inp, cfg)
        macro_cyc  = self._macro_cycle_score(inp)
        breadth_tr = self._breadth_trend_score(inp)
        cap_mom    = self._capital_momentum_score(ticker, capital_flow_score, inp)
        vix_tr     = self._vix_trend_score(inp)

        score = (
            rs_accel  * fw.get("rs_acceleration",   0.30) +
            macro_cyc * fw.get("macro_cycle_phase",  0.25) +
            breadth_tr* fw.get("breadth_trend",      0.20) +
            cap_mom   * fw.get("capital_momentum",   0.15) +
            vix_tr    * fw.get("vix_trend",          0.10)
        )
        return self.clamp(score)
