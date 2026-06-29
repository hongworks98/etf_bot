"""Breadth Engine Adapter"""
from __future__ import annotations
from typing import Any, Dict
from dss_integration.adapters.base_adapter import AbstractEngineAdapter
from dss_integration.data.base_loader import RawMarketData


class BreadthAdapter(AbstractEngineAdapter):
    def adapt(self, raw: RawMarketData, prev: Dict[str, Any]) -> Any:
        return raw

    @staticmethod
    def synthetic_result(raw: RawMarketData) -> Any:
        from types import SimpleNamespace
        ind = raw.breadth_indicators
        score = sum(ind.values()) / max(len(ind), 1)
        score = max(0.0, min(100.0, score))
        health = "Healthy" if score > 60 else ("Neutral" if score > 45 else "Weak")
        return SimpleNamespace(
            breadth_score=round(score, 1),
            breadth_health=health,
            breadth_trend="UP" if score > 55 else "DOWN",
        )
