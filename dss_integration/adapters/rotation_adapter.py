"""Rotation Signal Engine Adapter"""
from __future__ import annotations
from typing import Any, Dict
from dss_integration.adapters.base_adapter import AbstractEngineAdapter
from dss_integration.data.base_loader import RawMarketData


class RotationAdapter(AbstractEngineAdapter):
    def adapt(self, raw: RawMarketData, prev: Dict[str, Any]) -> Any:
        return {"raw": raw, "rs_result": prev.get("rs_result")}

    @staticmethod
    def synthetic_result(raw: RawMarketData, rs_result: Any) -> Any:
        from types import SimpleNamespace
        sector_results = {}
        dominant = None
        best_score = 0.0
        for t in raw.tickers:
            rs_entry = getattr(rs_result, "sector_results", {}).get(t)
            rs_score = getattr(rs_entry, "rs_score", 50.0) if rs_entry else 50.0
            rot_score = min(100.0, rs_score * 0.9)
            conv_score = rot_score * 0.85
            if rot_score > best_score:
                best_score = rot_score
                dominant = t

            class _Stage:
                value = "Confirmed"
            class _Timing:
                value = "THIS_WEEK"

            sector_results[t] = SimpleNamespace(
                rotation_score=round(rot_score, 1),
                conviction_score=round(conv_score, 1),
                stage=_Stage(),
                timing=_Timing(),
            )
        return SimpleNamespace(
            sector_results=sector_results,
            market_rotation_active=True,
            rotation_forecast=72.0,
            dominant_rotation=dominant or "XLK",
            rotation_directions=[],
        )
