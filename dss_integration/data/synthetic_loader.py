"""
dss_integration/data/synthetic_loader.py
SyntheticDataLoader — 데모/테스트용 합성 데이터 생성
실제 시장 데이터 없이도 전체 파이프라인을 실행할 수 있음.
"""
from __future__ import annotations
import random
from datetime import date
from typing import List

from dss_integration.data.base_loader import AbstractDataLoader, RawMarketData
from dss_integration.config.settings import (
    SECTOR_TICKERS, BENCHMARK_TICKERS,
    SYNTHETIC_PRICE_BARS, SYNTHETIC_RANDOM_SEED,
)


class SyntheticDataLoader(AbstractDataLoader):
    """
    합성 시장 데이터를 생성하는 DataLoader.
    seed를 고정하여 재현 가능한 결과를 보장한다.
    """

    def __init__(self, seed: int = SYNTHETIC_RANDOM_SEED):
        self._rng = random.Random(seed)

    def load(self) -> RawMarketData:
        n = SYNTHETIC_PRICE_BARS
        today = date.today().isoformat()

        # 섹터 ETF 가격 생성
        sector_prices = {}
        for ticker in SECTOR_TICKERS:
            drift = self._rng.gauss(0.0004, 0.0001)
            vol   = self._rng.gauss(0.012,  0.002)
            sector_prices[ticker] = self._gen_prices(n, drift=drift, vol=vol)

        # 벤치마크 가격
        bench = {}
        for t in BENCHMARK_TICKERS:
            drift = 0.0003 if t == "SPY" else 0.0005
            bench[t] = self._gen_prices(n, drift=drift, vol=0.011)

        # 매크로 지표 (0~100 점수로 정규화)
        macro_ind = {
            "gdp_growth":       self._rng.gauss(65, 10),
            "unemployment":     self._rng.gauss(55, 10),
            "inflation":        self._rng.gauss(50, 12),
            "consumer_conf":    self._rng.gauss(62, 10),
            "ism_mfg":          self._rng.gauss(58, 8),
            "yield_curve":      self._rng.gauss(60, 12),
        }
        macro_ind = {k: max(0.0, min(100.0, v)) for k, v in macro_ind.items()}

        # 시장 폭 지표
        breadth_ind = {
            "advance_decline": self._rng.gauss(63, 10),
            "new_highs_lows":  self._rng.gauss(58, 12),
            "above_ma200":     self._rng.gauss(65, 10),
            "mcclellan_osc":   self._rng.gauss(55, 15),
        }
        breadth_ind = {k: max(0.0, min(100.0, v)) for k, v in breadth_ind.items()}

        return RawMarketData(
            market_date      = today,
            tickers          = SECTOR_TICKERS,
            sector_prices    = sector_prices,
            benchmark_prices = bench,
            macro_indicators = macro_ind,
            breadth_indicators = breadth_ind,
            vix          = round(self._rng.gauss(18.5, 4), 1),
            rate_10y     = round(self._rng.gauss(4.2, 0.3), 2),
            dollar_index = round(self._rng.gauss(103.0, 2), 1),
            oil_price    = round(self._rng.gauss(78.0, 5), 1),
            gold_price   = round(self._rng.gauss(1950.0, 50), 0),
        )

    def is_available(self) -> bool:
        return True  # 항상 사용 가능

    def _gen_prices(
        self, n: int, start: float = 100.0,
        drift: float = 0.0004, vol: float = 0.012,
    ) -> List[float]:
        p = [start]
        for _ in range(n):
            p.append(round(p[-1] * (1 + self._rng.gauss(drift, vol)), 4))
        return p
