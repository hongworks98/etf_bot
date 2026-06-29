"""
engines/rotation/calculators/capital_flow_calculator.py
Capital Flow Calculator — Volume MFI + Volume Trend + ETF Fund Flow.
"""
from __future__ import annotations
from typing import List, Tuple
from engines.rotation.calculators.base import AbstractRotationCalculator
from engines.rotation.data_models import RotationConfig, RotationInput


class CapitalFlowCalculator(AbstractRotationCalculator):
    """SRP: Responsible solely for capital flow signal computation."""

    def _mfi_score(self, prices: List[float], volumes: List[float],
                   period: int, lo: float, hi: float) -> float:
        """Simplified Money Flow Index using close as typical price proxy."""
        n = min(len(prices), len(volumes), period + 1)
        if n < 2:
            return 50.0
        p = prices[-n:]
        v = volumes[-n:]
        pos_flow = 0.0
        neg_flow = 0.0
        for i in range(1, n):
            money_flow = p[i] * v[i]
            if p[i] > p[i - 1]:
                pos_flow += money_flow
            elif p[i] < p[i - 1]:
                neg_flow += money_flow
        if neg_flow == 0:
            raw_mfi = 100.0
        else:
            mfr = pos_flow / neg_flow
            raw_mfi = 100.0 - 100.0 / (1.0 + mfr)
        return self.normalize(raw_mfi, lo, hi)

    def _volume_trend_score(
        self, volumes: List[float],
        short_w: int, long_w: int,
        ratio_lo: float, ratio_hi: float,
    ) -> float:
        """Recent volume relative to baseline — rising volume = higher score."""
        if len(volumes) < long_w:
            return 50.0
        recent_avg  = sum(volumes[-short_w:]) / max(short_w, 1) if len(volumes) >= short_w else volumes[-1]
        baseline    = sum(volumes[-long_w:]) / long_w
        if baseline == 0:
            return 50.0
        ratio = recent_avg / baseline
        return self.normalize(ratio, ratio_lo, ratio_hi)

    def _etf_flow_score(self, ticker: str, inp: RotationInput, cfg: RotationConfig) -> float:
        """ETF fund flow trend → 0~100. Positive flow = capital inflow."""
        flow_trend = inp.aux_data.etf_flow_trend(ticker)
        if flow_trend == 0:
            return 50.0
        return self.clamp(50.0 + flow_trend / abs(flow_trend) * 25.0)   # +25 or -25 from neutral

    def calculate(
        self,
        ticker: str,
        inp: RotationInput,
        cfg: RotationConfig,
    ) -> float:
        """Returns capital_flow_score (0~100)."""
        # Price and volume series
        sector_ph = inp.sectors.get(ticker)
        prices  = getattr(sector_ph, "prices",  []) if sector_ph else []
        volumes = inp.sector_volumes.get(ticker, getattr(sector_ph, "volumes", []) if sector_ph else [])

        mfi    = self._mfi_score(prices, volumes, cfg.mfi_period, cfg.mfi_lo, cfg.mfi_hi)
        vol_tr = self._volume_trend_score(volumes, cfg.vol_window_short, cfg.vol_window_long,
                                           cfg.vol_ratio_lo, cfg.vol_ratio_hi)
        flow   = self._etf_flow_score(ticker, inp, cfg)

        fw = cfg.flow_weights
        score = (mfi   * fw.get("mfi",      0.35) +
                 vol_tr * fw.get("volume",   0.35) +
                 flow   * fw.get("etf_flow", 0.30))
        return self.clamp(score)
