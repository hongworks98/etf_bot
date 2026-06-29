"""
dss_integration/data/base_loader.py
Abstract DataLoader — OCP 준수
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class RawMarketData:
    """
    DataLoader가 반환하는 원시 시장 데이터.
    Engine들은 이 구조에서 필요한 데이터를 가져간다.
    """
    market_date:   str
    tickers:       List[str]
    # 가격 이력: ticker → price list (시간순)
    sector_prices: Dict[str, List[float]] = field(default_factory=dict)
    # 벤치마크 가격
    benchmark_prices: Dict[str, List[float]] = field(default_factory=dict)
    # 매크로 지표
    macro_indicators: Dict[str, float] = field(default_factory=dict)
    # 시장 폭 지표
    breadth_indicators: Dict[str, float] = field(default_factory=dict)
    # 기타
    vix:           float = 18.5
    rate_10y:      float = 4.2
    dollar_index:  float = 103.0
    oil_price:     float = 78.0
    gold_price:    float = 1950.0


class AbstractDataLoader(ABC):
    """
    DataLoader 인터페이스.
    Live / Synthetic / CSV 등 다양한 구현체로 교체 가능.
    """

    @abstractmethod
    def load(self) -> RawMarketData:
        """시장 데이터를 로드하여 RawMarketData로 반환."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """데이터 소스 접속 가능 여부."""
        ...
