"""
dss_integration/adapters/base_adapter.py
Abstract Engine Adapter — DIP 준수
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict
from dss_integration.data.base_loader import RawMarketData


class AbstractEngineAdapter(ABC):
    """
    DataLoader 출력 → 각 Engine의 Input 타입으로 변환.
    새 Engine 추가 시 이 클래스를 상속.
    """

    @abstractmethod
    def adapt(
        self,
        raw_data: RawMarketData,
        prev_results: Dict[str, Any],
    ) -> Any:
        """
        raw_data:     DataLoader가 제공한 원시 데이터
        prev_results: 앞선 Engine들의 결과 (순서 보장)
        Returns:      해당 Engine이 기대하는 Input 객체
        """
        ...
