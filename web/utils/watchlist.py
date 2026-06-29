"""
web/utils/watchlist.py
Favorites & Watchlist 관리 — JSON 파일 기반 영속 저장소.
"""
from __future__ import annotations
import json
import os
from typing import List, Set


def _watchlist_path() -> str:
    _here = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(_here, "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "watchlist.json")


class WatchlistManager:
    """Favorites와 Watchlist를 JSON 파일로 관리."""

    DEFAULT_TICKERS = [
        "XLK", "XLC", "XLY", "XLF", "XLI",
        "XLE", "XLB", "XLV", "XLP", "XLU", "XLRE",
    ]

    def __init__(self, path: str | None = None) -> None:
        self._path = path or _watchlist_path()
        self._data = self._load_raw()

    # ── Favorites ─────────────────────────────────────────────────────────────

    @property
    def favorites(self) -> List[str]:
        return list(self._data.get("favorites", []))

    def add_favorite(self, ticker: str) -> None:
        favs: list = self._data.setdefault("favorites", [])
        ticker = ticker.upper()
        if ticker not in favs:
            favs.append(ticker)
            self._write()

    def remove_favorite(self, ticker: str) -> None:
        favs: list = self._data.get("favorites", [])
        ticker = ticker.upper()
        if ticker in favs:
            favs.remove(ticker)
            self._write()

    def is_favorite(self, ticker: str) -> bool:
        return ticker.upper() in self._data.get("favorites", [])

    # ── Watchlist ─────────────────────────────────────────────────────────────

    @property
    def watchlist(self) -> List[str]:
        return list(self._data.get("watchlist", []))

    def add_watchlist(self, ticker: str) -> None:
        wl: list = self._data.setdefault("watchlist", [])
        ticker = ticker.upper()
        if ticker not in wl:
            wl.append(ticker)
            self._write()

    def remove_watchlist(self, ticker: str) -> None:
        wl: list = self._data.get("watchlist", [])
        ticker = ticker.upper()
        if ticker in wl:
            wl.remove(ticker)
            self._write()

    def is_watchlist(self, ticker: str) -> bool:
        return ticker.upper() in self._data.get("watchlist", [])

    # ── Combined ──────────────────────────────────────────────────────────────

    def all_tracked(self) -> List[str]:
        """Favorites + Watchlist 합집합 (중복 제거)."""
        seen: Set[str] = set()
        result = []
        for t in self.favorites + self.watchlist:
            if t not in seen:
                seen.add(t)
                result.append(t)
        return result

    # ── Private ───────────────────────────────────────────────────────────────

    def _load_raw(self) -> dict:
        if not os.path.exists(self._path):
            return {"favorites": [], "watchlist": self.DEFAULT_TICKERS[:3]}
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {"favorites": [], "watchlist": self.DEFAULT_TICKERS[:3]}

    def _write(self) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
