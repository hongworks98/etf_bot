"""Dashboard Orchestrator Adapter"""
from __future__ import annotations
from typing import Any, Dict
from dss_integration.adapters.base_adapter import AbstractEngineAdapter
from dss_integration.data.base_loader import RawMarketData


class DashboardAdapter(AbstractEngineAdapter):
    def adapt(self, raw: RawMarketData, prev: Dict[str, Any]) -> Any:
        return prev
