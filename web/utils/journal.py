"""
web/utils/journal.py
Decision Journal — 매일 자동 저장되는 투자 의사결정 기록.
JSON 파일로 영속 저장 (web/data/journal.json).

설계 원칙:
- DSSResult 에서 데이터를 읽어 저장
- 하루 1회 (같은 date → 덮어쓰기)
- 최대 30개 항목 유지 (rolling window)
- 향후 Validation Engine과 연결하여 실제 성과 기록 가능
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional


# ── 저장 경로 ─────────────────────────────────────────────────────────────────

def _journal_path() -> str:
    _here = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(_here, "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "journal.json")


# ── Data Model ────────────────────────────────────────────────────────────────

@dataclass
class JournalEntry:
    date: str                    # "2026-06-27"
    run_id: str
    action: str                  # "BUY" / "SELL" / "HOLD"
    confidence: float
    top_etfs: List[str] = field(default_factory=list)
    market_status: str = ""
    macro_score: float = 0.0
    risk_level: str = "보통"
    why_decision: str = ""
    # 향후 Validation Engine 연결 시 사용
    actual_return: Optional[float] = None   # 실제 수익률 (사후 기록)
    hit: Optional[bool] = None              # 추천 성공 여부


# ── Journal ───────────────────────────────────────────────────────────────────

class DecisionJournal:
    """
    Decision Journal — JSON 파일 기반 영속 저장소.
    """
    MAX_ENTRIES = 30

    def __init__(self, path: Optional[str] = None) -> None:
        self._path = path or _journal_path()
        self._data = self._load_raw()

    # ── Public ───────────────────────────────────────────────────────────────

    def save(self, entry: JournalEntry) -> None:
        """오늘 기록을 저장한다. 같은 date이면 덮어쓴다."""
        entries = self._data.get("entries", [])
        # 같은 날짜 제거
        entries = [e for e in entries if e.get("date") != entry.date]
        entries.append(asdict(entry))
        # 최신순 정렬 후 최대 개수 유지
        entries.sort(key=lambda e: e.get("date", ""), reverse=True)
        entries = entries[: self.MAX_ENTRIES]
        self._data["entries"] = entries
        self._write()

    def load_all(self) -> List[JournalEntry]:
        """전체 기록을 최신순으로 반환."""
        raw = self._data.get("entries", [])
        return [self._from_dict(e) for e in raw]

    def load_today(self, date: str) -> Optional[JournalEntry]:
        """오늘 기록 반환."""
        for e in self._data.get("entries", []):
            if e.get("date") == date:
                return self._from_dict(e)
        return None

    def load_yesterday(self, today: str) -> Optional[JournalEntry]:
        """오늘 바로 이전 기록 반환."""
        entries = self._data.get("entries", [])
        for e in sorted(entries, key=lambda x: x.get("date", ""), reverse=True):
            if e.get("date", "") < today:
                return self._from_dict(e)
        return None

    def load_recent(self, n: int = 7) -> List[JournalEntry]:
        """최근 n개 기록 반환 (최신순)."""
        return self.load_all()[:n]

    def count(self) -> int:
        return len(self._data.get("entries", []))

    # ── Private ───────────────────────────────────────────────────────────────

    def _load_raw(self) -> dict:
        if not os.path.exists(self._path):
            return {"version": "1.0", "entries": [], "max_entries": self.MAX_ENTRIES}
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {"version": "1.0", "entries": [], "max_entries": self.MAX_ENTRIES}

    def _write(self) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass  # 파일 저장 실패는 무시 (read-only 환경 등)

    @staticmethod
    def _from_dict(d: dict) -> JournalEntry:
        return JournalEntry(
            date=d.get("date", ""),
            run_id=d.get("run_id", ""),
            action=d.get("action", "WAIT"),
            confidence=d.get("confidence", 0.0),
            top_etfs=d.get("top_etfs", []),
            market_status=d.get("market_status", ""),
            macro_score=d.get("macro_score", 0.0),
            risk_level=d.get("risk_level", "보통"),
            why_decision=d.get("why_decision", ""),
            actual_return=d.get("actual_return"),
            hit=d.get("hit"),
        )


# ── Factory: DSSResult → JournalEntry ────────────────────────────────────────

def entry_from_result(result: object, home_data: object) -> JournalEntry:
    """
    DSSResult + HomeViewData → JournalEntry 변환.
    DataBridge가 이미 home_data를 만들었으므로 여기서는 필드 매핑만.
    """
    import datetime
    date = getattr(result, "run_date", "")
    if date:
        # run_date 형식: "2026-06-27 12:00:00" → "2026-06-27"
        date = date.split(" ")[0] if " " in date else date[:10]
    else:
        date = datetime.date.today().isoformat()

    return JournalEntry(
        date=date,
        run_id=getattr(result, "run_id", ""),
        action=getattr(home_data, "action", "WAIT"),
        confidence=getattr(home_data, "confidence", 0.0),
        top_etfs=list(getattr(home_data, "top_etfs", [])),
        market_status=getattr(home_data, "market_status", ""),
        macro_score=getattr(home_data, "macro_score", 0.0),
        risk_level=getattr(home_data, "risk_level", "보통"),
        why_decision=getattr(home_data, "why_decision", ""),
    )
