"""Validation Engine Adapter"""
from __future__ import annotations
import random
from typing import Any, Dict
from dss_integration.adapters.base_adapter import AbstractEngineAdapter
from dss_integration.data.base_loader import RawMarketData


class ValidationAdapter(AbstractEngineAdapter):
    def adapt(self, raw: RawMarketData, prev: Dict[str, Any]) -> Any:
        return {"raw": raw, "prev_results": prev}

    @staticmethod
    def build_validation_input(raw: RawMarketData) -> Any:
        """ValidationInput 생성."""
        import sys, os
        sys.path.insert(0, os.path.join(
            os.path.dirname(__file__), '..', '..', '..'))
        from validation.data_models import (
            DecisionRecord, PriceHistory, ValidationInput
        )
        rng = random.Random(55)
        tickers = raw.tickers
        dates = [f"D{i:04d}" for i in range(len(raw.sector_prices.get(tickers[0],[100]*10)))]
        wts = {t: 0.95/len(tickers) for t in tickers}
        records = []
        for i in range(min(200, len(dates)-1)):
            ret = rng.gauss(0.0004, 0.009)
            conf = min(95, max(20, rng.gauss(62, 12)))
            macro = min(100, max(0, rng.gauss(65, 12)))
            records.append(DecisionRecord(
                date=dates[i+1],
                macro_score=round(macro, 1),
                breadth_score=round(min(100,max(0,rng.gauss(60,10))),1),
                rs_score=round(min(100,max(0,rng.gauss(63,11))),1),
                rotation_score=round(min(100,max(0,rng.gauss(58,12))),1),
                portfolio_score=round(min(100,max(0,rng.gauss(65,10))),1),
                risk_score=round(min(100,max(0,rng.gauss(35,12))),1),
                confidence=round(conf,1),
                action="BUY" if macro>55 else "HOLD",
                weights=wts,
                actual_return=round(ret,6),
                correct=(ret>0)==(macro>55),
            ))
        ph = PriceHistory(dates=dates, prices=raw.sector_prices)
        return ValidationInput(
            decision_records=records,
            price_history=ph,
            benchmark_prices=raw.benchmark_prices,
            initial_capital=100_000.0,
            risk_free_rate=0.045,
        )
