"""
dss_integration/data/live_loader.py
LiveDataLoader — FRED + Alpha Vantage 실시간 데이터
- FRED: 매크로 지표, VIX, 금리, 유가, 금값, 달러
- Alpha Vantage: 섹터 ETF 가격 (24시간 캐시로 API 한도 보호)
- 실패 시 각 항목별 합성 데이터로 폴백
"""
from __future__ import annotations
import os, time, logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests

from dss_integration.data.base_loader import AbstractDataLoader, RawMarketData
from dss_integration.config.settings import SECTOR_TICKERS, BENCHMARK_TICKERS

log = logging.getLogger("LiveDataLoader")

# ── 24시간 가격 캐시 (Alpha Vantage 25req/day 한도 보호) ──────────────
_price_cache: Dict[str, List[float]] = {}
_price_cache_ts: float = 0.0
PRICE_CACHE_TTL = 86400  # 24 hours

# ── FRED 시리즈 ID ────────────────────────────────────────────────────
FRED_SERIES = {
    "gdp_growth":    "A191RL1Q225SBEA",  # 실질 GDP 성장률 (QoQ%)
    "unemployment":  "UNRATE",            # 실업률 (%)
    "inflation":     "CPIAUCSL",          # CPI (YoY% 계산)
    "consumer_conf": "UMCSENT",           # 미시간대 소비자심리 (0-100)
    "yield_curve":   "T10Y2Y",            # 10Y-2Y 스프레드
    "vix":           "VIXCLS",            # VIX
    "rate_10y":      "DGS10",             # 10년물 금리 (%)
    "oil_price":     "DCOILWTICO",        # WTI 원유 ($/배럴)
    "gold_price":    "GOLDAMGBD228NLBM",  # 런던 금 고시가 ($/온스)
    "dollar_index":  "DTWEXBGS",          # 달러 인덱스
    "ism_mfg":       "MANEMP",            # 제조업 고용 (ISM 대용)
}


class LiveDataLoader(AbstractDataLoader):
    """
    FRED + Alpha Vantage 기반 실시간 DataLoader.
    API 키는 환경변수 or st.secrets에서 읽는다.
    """

    def __init__(
        self,
        fred_key: str = "",
        av_key: str = "",
    ):
        self._fred_key = fred_key or os.environ.get("FRED_API_KEY", "")
        self._av_key   = av_key   or os.environ.get("ALPHA_VANTAGE_API_KEY", "")

    # ── Public ────────────────────────────────────────────────────────

    def is_available(self) -> bool:
        return bool(self._fred_key or self._av_key)

    def load(self) -> RawMarketData:
        log.info("LiveDataLoader: 실시간 데이터 로드 시작")

        # 1. FRED 매크로 데이터
        fred_raw = self._fetch_fred_all()

        # 2. 매크로 지표 정규화 (0~100)
        macro_ind = self._normalize_macro(fred_raw)

        # 3. 시장 폭 지표 (가격 데이터로 계산)
        prices = self._fetch_av_prices()
        breadth_ind = self._calc_breadth(prices)

        log.info(f"LiveDataLoader: 완료 — macro={len(macro_ind)}, tickers={len(prices)}")

        return RawMarketData(
            market_date      = date.today().isoformat(),
            tickers          = SECTOR_TICKERS,
            sector_prices    = {t: prices.get(t, self._fallback_prices()) for t in SECTOR_TICKERS},
            benchmark_prices = {t: prices.get(t, self._fallback_prices()) for t in BENCHMARK_TICKERS},
            macro_indicators = macro_ind,
            breadth_indicators = breadth_ind,
            vix          = fred_raw.get("vix",          18.5),
            rate_10y     = fred_raw.get("rate_10y",      4.2),
            dollar_index = fred_raw.get("dollar_index", 103.0),
            oil_price    = fred_raw.get("oil_price",     78.0),
            gold_price   = fred_raw.get("gold_price",  1950.0),
        )

    # ── FRED ──────────────────────────────────────────────────────────

    def _fetch_fred_all(self) -> Dict[str, float]:
        result: Dict[str, float] = {}
        if not self._fred_key:
            log.warning("FRED_API_KEY 없음 — 매크로 데이터 합성값 사용")
            return result

        for key, series_id in FRED_SERIES.items():
            val = self._fetch_fred_series(series_id)
            if val is not None:
                result[key] = val

        # CPI는 YoY% 변화율로 변환
        if "inflation" in result:
            yoy = self._fetch_fred_yoy("CPIAUCSL")
            if yoy is not None:
                result["inflation"] = yoy

        return result

    def _fetch_fred_series(self, series_id: str) -> Optional[float]:
        """FRED 시리즈 최신값 1개 반환."""
        try:
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {
                "series_id":    series_id,
                "api_key":      self._fred_key,
                "file_type":    "json",
                "sort_order":   "desc",
                "limit":        1,
                "observation_start": (datetime.today() - timedelta(days=400)).strftime("%Y-%m-%d"),
            }
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            obs = resp.json().get("observations", [])
            for o in obs:
                if o.get("value") not in (".", "", None):
                    return float(o["value"])
        except Exception as e:
            log.warning(f"FRED {series_id} 오류: {e}")
        return None

    def _fetch_fred_yoy(self, series_id: str) -> Optional[float]:
        """12개월 YoY% 계산."""
        try:
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {
                "series_id":  series_id,
                "api_key":    self._fred_key,
                "file_type":  "json",
                "sort_order": "desc",
                "limit":      14,
            }
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            obs = [o for o in resp.json().get("observations", [])
                   if o.get("value") not in (".", "", None)]
            if len(obs) >= 13:
                latest = float(obs[0]["value"])
                year_ago = float(obs[12]["value"])
                return round((latest - year_ago) / year_ago * 100, 2)
        except Exception as e:
            log.warning(f"FRED YoY 계산 오류: {e}")
        return None

    # ── Alpha Vantage 가격 ────────────────────────────────────────────

    def _fetch_av_prices(self) -> Dict[str, List[float]]:
        global _price_cache, _price_cache_ts

        # 24시간 캐시 유효하면 그대로 반환
        if _price_cache and (time.time() - _price_cache_ts) < PRICE_CACHE_TTL:
            log.info("LiveDataLoader: 가격 캐시 사용 (24h TTL)")
            return _price_cache

        if not self._av_key:
            log.warning("ALPHA_VANTAGE_API_KEY 없음 — 가격 합성값 사용")
            return {}

        prices: Dict[str, List[float]] = {}
        all_tickers = SECTOR_TICKERS + BENCHMARK_TICKERS

        for ticker in all_tickers:
            closes = self._fetch_av_daily(ticker)
            if closes:
                prices[ticker] = closes
            time.sleep(0.5)  # API 속도 제한 준수

        if prices:
            _price_cache    = prices
            _price_cache_ts = time.time()
            log.info(f"LiveDataLoader: {len(prices)}개 티커 가격 로드 완료")

        return prices

    def _fetch_av_daily(self, ticker: str) -> List[float]:
        """Alpha Vantage TIME_SERIES_DAILY → 종가 리스트 (오래된 순)."""
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                "function":   "TIME_SERIES_DAILY",
                "symbol":     ticker,
                "outputsize": "compact",   # 최근 100일
                "apikey":     self._av_key,
            }
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            ts = data.get("Time Series (Daily)", {})
            if not ts:
                log.warning(f"AV {ticker}: 데이터 없음 — {list(data.keys())}")
                return []

            # 날짜 오름차순 정렬
            closes = [
                float(v["4. close"])
                for _, v in sorted(ts.items())
            ]
            return closes

        except Exception as e:
            log.warning(f"AV {ticker} 오류: {e}")
            return []

    # ── 정규화 (0~100) ────────────────────────────────────────────────

    def _normalize_macro(self, raw: Dict[str, float]) -> Dict[str, float]:
        def clamp(v: float) -> float:
            return max(0.0, min(100.0, v))

        indicators: Dict[str, float] = {}

        # GDP 성장률: -4% → 0, 0% → 50, +4% → 100
        if "gdp_growth" in raw:
            indicators["gdp_growth"] = clamp(50 + raw["gdp_growth"] * 12.5)
        else:
            indicators["gdp_growth"] = 55.0

        # 실업률: 10% → 0, 5% → 50, 2% → 100 (역방향)
        if "unemployment" in raw:
            indicators["unemployment"] = clamp(100 - (raw["unemployment"] - 2) * 14.3)
        else:
            indicators["unemployment"] = 60.0

        # CPI YoY%: 0% → 70, 2% → 80, 5% → 40, 9% → 0
        if "inflation" in raw:
            v = raw["inflation"]
            indicators["inflation"] = clamp(80 - max(0, v - 2) * 10)
        else:
            indicators["inflation"] = 50.0

        # 소비자심리 (50~110 → 0~100)
        if "consumer_conf" in raw:
            indicators["consumer_conf"] = clamp((raw["consumer_conf"] - 50) / 60 * 100)
        else:
            indicators["consumer_conf"] = 60.0

        # ISM 대용 (제조업 고용 역정규화)
        if "ism_mfg" in raw:
            v = raw["ism_mfg"]
            indicators["ism_mfg"] = clamp((v - 10000) / 2000 * 10 + 55)
        else:
            indicators["ism_mfg"] = 55.0

        # 수익률 곡선: -2 → 0, 0 → 50, +2 → 100
        if "yield_curve" in raw:
            indicators["yield_curve"] = clamp(50 + raw["yield_curve"] * 25)
        else:
            indicators["yield_curve"] = 55.0

        return indicators

    # ── 시장 폭 지표 계산 ─────────────────────────────────────────────

    def _calc_breadth(self, prices: Dict[str, List[float]]) -> Dict[str, float]:
        if not prices:
            return {
                "advance_decline": 55.0,
                "new_highs_lows":  50.0,
                "above_ma200":     60.0,
                "mcclellan_osc":   50.0,
            }

        vals = list(prices.values())
        n_tickers = len(vals)

        # 오늘 상승 비율
        up = sum(1 for p in vals if len(p) >= 2 and p[-1] > p[-2])
        advance_decline = round(up / n_tickers * 100, 1)

        # 52주 신고가 비율
        highs = 0
        for p in vals:
            if len(p) >= 252:
                if p[-1] >= max(p[-252:]) * 0.98:
                    highs += 1
            elif p and p[-1] >= max(p) * 0.98:
                highs += 1
        new_highs_lows = round(highs / n_tickers * 100, 1)

        # 200일 MA 위 비율
        above_ma = 0
        for p in vals:
            if len(p) >= 200:
                ma200 = sum(p[-200:]) / 200
                if p[-1] > ma200:
                    above_ma += 1
            elif p:
                ma = sum(p) / len(p)
                if p[-1] > ma:
                    above_ma += 1
        above_ma200 = round(above_ma / n_tickers * 100, 1)

        # McClellan Oscillator (단순화 — 5일 vs 20일 이동평균 비율)
        daily_advances = []
        n_days = min(20, min(len(p) for p in vals))
        for i in range(-n_days, 0):
            day_up = sum(1 for p in vals if len(p) >= abs(i) + 1 and p[i] > p[i-1])
            daily_advances.append(day_up / n_tickers * 100)

        if len(daily_advances) >= 10:
            ema5  = sum(daily_advances[-5:]) / 5
            ema10 = sum(daily_advances[-10:]) / 10
            mcclellan = max(0.0, min(100.0, 50 + (ema5 - ema10) * 2))
        else:
            mcclellan = 50.0

        return {
            "advance_decline": advance_decline,
            "new_highs_lows":  new_highs_lows,
            "above_ma200":     above_ma200,
            "mcclellan_osc":   round(mcclellan, 1),
        }

    # ── 합성 폴백 ─────────────────────────────────────────────────────

    @staticmethod
    def _fallback_prices(n: int = 100) -> List[float]:
        """API 실패 시 단순 가격 생성 (seed 없이 — 매번 다름)."""
        import random
        p = [100.0]
        for _ in range(n):
            p.append(round(p[-1] * (1 + random.gauss(0.0003, 0.012)), 4))
        return p
