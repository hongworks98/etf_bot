"""Portfolio Decision Engine Adapter"""
from __future__ import annotations
from typing import Any, Dict
from dss_integration.adapters.base_adapter import AbstractEngineAdapter
from dss_integration.data.base_loader import RawMarketData


class PortfolioAdapter(AbstractEngineAdapter):
    def adapt(self, raw: RawMarketData, prev: Dict[str, Any]) -> Any:
        return {k: prev.get(k) for k in
                ["macro_result","breadth_result","rs_result","rotation_result"]}

    @staticmethod
    def synthetic_result(raw: RawMarketData, prev: Dict[str, Any]) -> Any:
        from types import SimpleNamespace
        macro = prev.get("macro_result")
        macro_score = getattr(macro, "macro_score", 65.0)
        dec_score = round(min(95.0, max(20.0, macro_score * 0.95 + 5)), 1)
        action = "BUY" if dec_score > 60 else ("SELL" if dec_score < 40 else "HOLD")
        return SimpleNamespace(decision_score=dec_score, action=action)
