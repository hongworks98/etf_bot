"""Relative Strength Engine Adapter"""
from __future__ import annotations
import random
from typing import Any, Dict
from dss_integration.adapters.base_adapter import AbstractEngineAdapter
from dss_integration.data.base_loader import RawMarketData


class RSAdapter(AbstractEngineAdapter):
    def adapt(self, raw: RawMarketData, prev: Dict[str, Any]) -> Any:
        return raw

    @staticmethod
    def synthetic_result(raw: RawMarketData) -> Any:
        from types import SimpleNamespace
        rng = random.Random(7)
        sector_results = {}
        for t in raw.tickers:
            prices = raw.sector_prices.get(t, [100.0, 101.0])
            # RS = recent return vs universe average
            ret = (prices[-1] / prices[-min(20, len(prices))] - 1) * 100
            rs = max(0.0, min(100.0, 50 + ret * 10))
            sector_results[t] = SimpleNamespace(rs_score=round(rs, 1), persistence_score=60.0)
        avg_rs = sum(s.rs_score for s in sector_results.values()) / max(len(sector_results), 1)
        return SimpleNamespace(
            sector_results=sector_results,
            avg_rs_score=round(avg_rs, 1),
        )
