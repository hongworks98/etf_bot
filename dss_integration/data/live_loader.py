"""
dss_integration/data/live_loader.py
LiveDataLoader — FRED + yfinance 실시간 데이터
- FRED: 매크로 지표, VIX, 금리, 유가, 금값, 달러
- yfinance: 섹터 ETF 가격 (24시간 캐시, 속도 제한 없음)
- Alpha Vantage: yfinance 실패 시 폴백
"""
from __future__ import annotations
import os, time, logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import requests

from dss_integration.data.base_loader import AbstractDataLoader, RawMarketData
from dss_integration.config.settings import SECTOR_TICKERS, BENCHMARK_TICKERS

log = logging.getLogger("LiveDataLoader")

# ── 24시간 가격 캐시 ─────────────────────────────────────────────────
_price_cache: Dict[str, List[float]] = {}
_price_cache_ts: float = 0.0
PRICE_CACHE_TTL = 86400  # 24 hours

# ── FRED 시리즈 ID ────────────────────────────────────────────────────
FRED_SERIES = {
    "gdp_growth":    "A191RL1Q225SBEA",  # 실질 GDP 성장률 (QoQ%)
    "unemployment":  "UNRATE",            # 실업률 (%)
    "inflation":     "CPIAUCSL",          # CPI (YoY% 별도 계산)
    "consumer_conf": "UMCSENT",           # 미시간대 소비자심리
    "yield_curve":   "T10Y2Y",            # 10Y-2Y 스프레드
    "ism_mfg":       "MANEMP",            # 제조업 고용 (ISM 대용)
    "vix":           "VIXCLS",            # VIX
    "rate_10y":      "DGS10",             # 10년물 금리 (%)
    "oil_price":     "DCOILWTICO",        # WTI 원유 ($/배럴)
    "gold_price":    "GOLDPMGBD228NLBM",  # 런던 금 PM 고시가 ($/온스)
    "dollar_index":  "DTWEXBGS",          # 달러 인덱스
}


class LiveDataLoader(AbstractDataLoader):
    """FRED + yfinance 기반 실시간 DataLoader."""

    def __init__(self, fred_key: str = "", av_key: str = ""):
        self._fred_key = fred_key or os.environ.get("FRED_API_KEY", "")
        self._av_key   = av_key   or os.environ.get("ALPHA_VANTAGE_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self._fred_key or self._av_key)

    def load(self) -> RawMarketData:
        log.info("LiveDataLoader: 실시간 데이터 로드 시작")

        fred_raw    = self._fetch_fred_all()
        macro_ind   = self._normalize_macro(fred_raw)
        prices      = self._fetch_prices()
        breadth_ind = self._calc_breadth(prices)

        log.info(f"LiveDataLoader: 완료 — macro={len(macro_ind)}, tickers={len(prices)}")

        return RawMarketData(
            market_date        = date.today().isoformat(),
            tickers            = SECTOR_TICKERS,
            sector_prices      = {t: prices.get(t, self._fallback_prices()) for t in SECTOR_TICKERS},
            benchmark_prices   = {t: prices.get(t, self._fallback_prices()) for t in BENCHMARK_TICKERS},
            macro_indicators   = macro_ind,
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
            log.warning("FRED_API_KEY 없음 — 매크로 합성값 사용")
            return result

        for key, series_id in FRED_SERIES.items():
            val = self._fetch_fred_series(series_id)
            if val is not None:
                result[key] = val

        # CPI → YoY% 변화율 계산
        if "inflation" in result:
            yoy = self._fetch_fred_yoy("CPIAUCSL")
            if yoy is not None:
                result["inflation"] = yoy

        return result

    def _fetch_fred_series(self, series_id: str) -> Optional[float]:
        """FRED 최신값 1개 반환 (observation_start 없이 — 데이터 지연 방지)."""
        try:
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {
                "series_id":  series_id,
                "api_key":    self._fred_key,
                "file_type":  "json",
                "sort_order": "desc",
                "limit":      5,   # 최신 5개 중 유효값 사용
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
                "limit":      15,
            }
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            obs = [o for o in resp.json().get("observations", [])
                   if o.get("value") not in (".", "", None)]
            if len(obs) >= 13:
                latest   = float(obs[0]["value"])
                year_ago = float(obs[12]["value"])
                return round((latest - year_ago) / year_ago * 100, 2)
        except Exception as e:
            log.warning(f"FRED YoY 오류: {e}")
        return None

    # ── 가격 데이터 (yfinance 우선, AV 폴백) ──────────────────────────

    def _fetch_prices(self) -> Dict[str, List[float]]:
        global _price_cache, _price_cache_ts

        if _price_cache and (time.time() - _price_cache_ts) < PRICE_CACHE_TTL:
            log.info("LiveDataLoader: 가격 캐시 사용 (24h TTL)")
            return _price_cache

        prices = self._fetch_yfinance()

        if not prices and self._av_key:
            log.warning("yfinance 실패 — Alpha Vantage 폴백 시도")
            prices = self._fetch_av_prices()

        if prices:
            _price_cache    = prices
            _price_cache_ts = time.time()

        return prices

    def _fetch_yfinance(self) -> Dict[str, List[float]]:
        """yfinance로 ETF 가격 일괄 수집 (무료, 속도 제한 없음)."""
        try:
            import yfinance as yf
            all_tickers = SECTOR_TICKERS + BENCHMARK_TICKERS
            symbols = " ".join(all_tickers)
            data = yf.download(symbols, period="1y", auto_adjust=True,
                               progress=False, threads=True)

            if data.empty:
                return {}

            prices: Dict[str, List[float]] = {}
            close = data["Close"] if "Close" in data.columns else data

            for ticker in all_tickers:
                if ticker in close.columns:
                    series = close[ticker].dropna().tolist()
                    if series:
                        prices[ticker] = [round(p, 4) for p in series]

            log.info(f"yfinance: {len(prices)}개 티커 로드 완료")
            return prices

        except ImportError:
            log.warning("yfinance 미설치")
            return {}
        except Exception as e:
            log.warning(f"yfinance 오류: {e}")
            return {}

    def _fetch_av_prices(self) -> Dict[str, List[float]]:
        """Alpha Vantage 가격 수집 (분당 5회 한도 준수 — 13초 간격)."""
        prices: Dict[str, List[float]] = {}
        all_tickers = SECTOR_TICKERS + BENCHMARK_TICKERS

        for i, ticker in enumerate(all_tickers):
            closes = self._fetch_av_daily(ticker)
            if closes:
                prices[ticker] = closes
            if i < len(all_tickers) - 1:
                time.sleep(13)  # 분당 5회 한도 (60/5 = 12s + 여유 1s)

        log.info(f"Alpha Vantage: {len(prices)}개 티커 로드 완료")
        return prices

    def _fetch_av_daily(self, ticker: str) -> List[float]:
        """Alpha Vantage TIME_SERIES_DAILY → 종가 리스트 (오래된 순)."""
        try:
            resp = requests.get(
                "https://www.alphavantage.co/query",
                params={
                    "function":   "TIME_SERIES_DAILY",
                    "symbol":     ticker,
                    "outputsize": "compact",
                    "apikey":     self._av_key,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            ts = data.get("Time Series (Daily)", {})
            if not ts:
                log.warning(f"AV {ticker}: 데이터 없음 — {list(data.keys())}")
                return []
            return [float(v["4. close"]) for _, v in sorted(ts.items())]
        except Exception as e:
            log.warning(f"AV {ticker} 오류: {e}")
            return []

    # ── 정규화 (0~100) ────────────────────────────────────────────────

    def _normalize_macro(self, raw: Dict[str, float]) -> Dict[str, float]:
        def clamp(v: float) -> float:
            return max(0.0, min(100.0, v))

        return {
            "gdp_growth":   clamp(50 + raw["gdp_growth"]   * 12.5) if "gdp_growth"   in raw else 55.0,
            "unemployment": clamp(100 - (raw["unemployment"] - 2) * 14.3) if "unemployment" in raw else 60.0,
            "inflation":    clamp(80 - max(0, raw["inflation"] - 2) * 10)  if "inflation"    in raw else 50.0,
            "consumer_conf":clamp((raw["consumer_conf"] - 50) / 60 * 100)  if "consumer_conf" in raw else 60.0,
            "ism_mfg":      clamp((raw["ism_mfg"] - 10000) / 2000 * 10 + 55) if "ism_mfg"   in raw else 55.0,
            "yield_curve":  clamp(50 + raw["yield_curve"]  * 25)   if "yield_curve"  in raw else 55.0,
        }

    # ── 시장 폭 지표 ──────────────────────────────────────────────────

    def _calc_breadth(self, prices: Dict[str, List[float]]) -> Dict[str, float]:
        if not prices:
            return {"advance_decline": 55.0, "new_highs_lows": 50.0,
                    "above_ma200": 60.0, "mcclellan_osc": 50.0}

        vals = list(prices.values())
        n    = len(vals)

        up = sum(1 for p in vals if len(p) >= 2 and p[-1] > p[-2])
        advance_decline = round(up / n * 100, 1)

        highs = sum(1 for p in vals if p and p[-1] >= max(p[-252:] if len(p) >= 252 else p) * 0.98)
        new_highs_lows = round(highs / n * 100, 1)

        above = sum(1 for p in vals
                    if (len(p) >= 200 and p[-1] > sum(p[-200:]) / 200)
                    or (len(p) < 200 and p and p[-1] > sum(p) / len(p)))
        above_ma200 = round(above / n * 100, 1)

        n_days = min(20, min(len(p) for p in vals))
        daily_adv = [sum(1 for p in vals if len(p) >= abs(i)+1 and p[i] > p[i-1]) / n * 100
                     for i in range(-n_days, 0)]
        mcclellan = 50.0
        if len(daily_adv) >= 10:
            mcclellan = max(0.0, min(100.0, 50 + (sum(daily_adv[-5:])/5 - sum(daily_adv[-10:])/10) * 2))

        return {
            "advance_decline": advance_decline,
            "new_highs_lows":  new_highs_lows,
            "above_ma200":     above_ma200,
            "mcclellan_osc":   round(mcclellan, 1),
        }

    @staticmethod
    def _fallback_prices(n: int = 100) -> List[float]:
        import random
        p = [100.0]
        for _ in range(n):
            p.append(round(p[-1] * (1 + random.gauss(0.0003, 0.012)), 4))
        return p
