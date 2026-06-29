"""
Macro Engine Adapter
RawMarketData → macro engine input (또는 synthetic result)
"""
from __future__ import annotations
from typing import Any, Dict
from dss_integration.adapters.base_adapter import AbstractEngineAdapter
from dss_integration.data.base_loader import RawMarketData
import random


class MacroAdapter(AbstractEngineAdapter):
    """
    매크로 엔진 입력 준비.
    실제 MacroEngine이 없을 경우 synthetic result를 생성.
    """

    def adapt(self, raw: RawMarketData, prev: Dict[str, Any]) -> Any:
        return raw  # 매크로 엔진은 RawMarketData 직접 수신

    @staticmethod
    def synthetic_result(raw: RawMarketData) -> Any:
        """MacroEngine이 없을 때 사용하는 합성 결과."""
        from types import SimpleNamespace
        ind = raw.macro_indicators
        score = sum(ind.values()) / max(len(ind), 1)
        score = max(0.0, min(100.0, score))
        state = "Expansion" if score > 60 else ("Slowdown" if score > 45 else "Recession")
        direction = "UP" if score > 55 else ("DOWN" if score < 40 else "NEUTRAL")
        return SimpleNamespace(
            macro_score=round(score, 1),
            macro_state=state,
            macro_direction=direction,
        )
