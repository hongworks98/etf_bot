"""
web/utils/market_calendar.py
US 시장 개장 상태 및 경제 이벤트 조회.

★ 외부 API 없음 — 순수 Python datetime 기반 ★
2026년 NYSE 휴장일, 조기 폐장일, 주요 경제 이벤트 하드코딩.
DataBridge.market_status()가 이 모듈을 호출하여 MarketStatusViewData로 변환한다.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import List, Optional


# ── US Market Hours (ET) ──────────────────────────────────────────────────────
_MARKET_OPEN  = datetime.time(9, 30)   # 09:30 ET
_MARKET_CLOSE = datetime.time(16, 0)   # 16:00 ET (regular)
_EARLY_CLOSE  = datetime.time(13, 0)   # 13:00 ET (early close)
_PREMARKET_START = datetime.time(4, 0) # 04:00 ET
_AFTERHOURS_END  = datetime.time(20, 0)# 20:00 ET


# ── 2026 NYSE Full Holiday List ───────────────────────────────────────────────
_HOLIDAYS_2026: dict = {
    "2026-01-01": "New Year's Day",
    "2026-01-19": "Martin Luther King Jr. Day",
    "2026-02-16": "Presidents' Day",
    "2026-04-03": "Good Friday",
    "2026-05-25": "Memorial Day",
    "2026-06-19": "Juneteenth National Independence Day",
    "2026-07-03": "Independence Day (observed)",
    "2026-09-07": "Labor Day",
    "2026-11-26": "Thanksgiving Day",
    "2026-12-25": "Christmas Day",
}

# ── 2026 Early Close Days (13:00 ET) ─────────────────────────────────────────
_EARLY_CLOSE_2026: dict = {
    "2026-11-27": "Black Friday",
    "2026-12-24": "Christmas Eve",
}

# ── 2026 Economic Events ──────────────────────────────────────────────────────
# 출처: Fed/BLS 일반적인 발표 패턴 기반 근사 날짜
_EVENTS_2026: dict = {
    # January
    "2026-01-07":  ["📋 Non-Farm Payroll (Dec 2025)"],
    "2026-01-14":  ["📊 CPI (Dec 2025)"],
    "2026-01-15":  ["📊 PPI (Dec 2025)"],
    "2026-01-28":  ["🏦 FOMC Meeting (Day 1)"],
    "2026-01-29":  ["🏦 FOMC Rate Decision"],
    # February
    "2026-02-04":  ["📋 Non-Farm Payroll (Jan)"],
    "2026-02-11":  ["📊 CPI (Jan)"],
    "2026-02-12":  ["📊 PPI (Jan)"],
    # March
    "2026-03-04":  ["📋 Non-Farm Payroll (Feb)"],
    "2026-03-11":  ["📊 CPI (Feb)"],
    "2026-03-12":  ["📊 PPI (Feb)"],
    "2026-03-18":  ["🏦 FOMC Meeting (Day 1)", "⚡ Quad Witching Week"],
    "2026-03-19":  ["🏦 FOMC Rate Decision"],
    "2026-03-20":  ["⚡ Quad Witching (Options Expiry)"],
    # April
    "2026-04-01":  ["📋 Non-Farm Payroll (Mar)"],
    "2026-04-09":  ["📊 CPI (Mar)"],
    "2026-04-10":  ["📊 PPI (Mar)"],
    # May
    "2026-05-06":  ["📋 Non-Farm Payroll (Apr)", "🏦 FOMC Meeting (Day 1)"],
    "2026-05-07":  ["🏦 FOMC Rate Decision"],
    "2026-05-13":  ["📊 CPI (Apr)"],
    "2026-05-14":  ["📊 PPI (Apr)"],
    # June
    "2026-06-03":  ["📋 Non-Farm Payroll (May)"],
    "2026-06-10":  ["📊 CPI (May)"],
    "2026-06-11":  ["📊 PPI (May)"],
    "2026-06-17":  ["🏦 FOMC Meeting (Day 1)", "⚡ Quad Witching Week"],
    "2026-06-18":  ["🏦 FOMC Rate Decision"],
    "2026-06-19":  ["⚡ Quad Witching (Options Expiry)"],
    # July
    "2026-07-08":  ["📋 Non-Farm Payroll (Jun)"],
    "2026-07-14":  ["📊 CPI (Jun)"],
    "2026-07-15":  ["📊 PPI (Jun)"],
    # August
    "2026-08-05":  ["📋 Non-Farm Payroll (Jul)"],
    "2026-08-12":  ["📊 CPI (Jul)"],
    "2026-08-13":  ["📊 PPI (Jul)"],
    # September
    "2026-09-02":  ["📋 Non-Farm Payroll (Aug)"],
    "2026-09-09":  ["📊 CPI (Aug)"],
    "2026-09-10":  ["📊 PPI (Aug)"],
    "2026-09-15":  ["🏦 FOMC Meeting (Day 1)", "⚡ Quad Witching Week"],
    "2026-09-17":  ["🏦 FOMC Rate Decision"],
    "2026-09-18":  ["⚡ Quad Witching (Options Expiry)"],
    # October
    "2026-10-07":  ["📋 Non-Farm Payroll (Sep)"],
    "2026-10-14":  ["📊 CPI (Sep)"],
    "2026-10-15":  ["📊 PPI (Sep)"],
    # November
    "2026-11-04":  ["📋 Non-Farm Payroll (Oct)", "🏦 FOMC Meeting (Day 1)"],
    "2026-11-05":  ["🏦 FOMC Rate Decision"],
    "2026-11-11":  ["📊 CPI (Oct)"],
    "2026-11-12":  ["📊 PPI (Oct)"],
    # December
    "2026-12-02":  ["📋 Non-Farm Payroll (Nov)"],
    "2026-12-09":  ["📊 CPI (Nov)"],
    "2026-12-10":  ["📊 PPI (Nov)"],
    "2026-12-15":  ["🏦 FOMC Meeting (Day 1)", "⚡ Quad Witching Week"],
    "2026-12-16":  ["🏦 FOMC Rate Decision"],
    "2026-12-18":  ["⚡ Quad Witching (Options Expiry)"],
}


# ── Result Dataclass ──────────────────────────────────────────────────────────

@dataclass
class MarketCalendarData:
    """
    MarketCalendar.get_status() 반환 타입.
    DataBridge.market_status()가 이를 MarketStatusViewData로 매핑한다.
    """
    is_open: bool
    is_weekend: bool
    is_holiday: bool
    is_early_close: bool
    holiday_name: str           # "" if not holiday/early-close
    market_phase: str           # "Open" / "Pre-Market" / "After-Hours" / "Closed"
    status_icon: str            # 🟢 / 🟡 / 🔴
    status_text: str            # "US Market Open" / "US Market Closed" etc.
    status_color: str           # hex color string
    et_time_str: str            # "Mon Jun 29, 10:30 EDT"
    kst_time_str: str           # "Tue Jun 30, 23:30 KST"
    today_events: List[str] = field(default_factory=list)
    has_events: bool = False


# ── MarketCalendar ────────────────────────────────────────────────────────────

class MarketCalendar:
    """
    US NYSE 시장 상태 조회.
    외부 API 없음 — 순수 Python datetime.
    now_utc 파라미터를 통해 테스트 가능.
    """

    @classmethod
    def get_status(
        cls,
        now_utc: Optional[datetime.datetime] = None,
    ) -> MarketCalendarData:
        """현재 시각 기준 US 시장 상태를 반환한다."""
        if now_utc is None:
            now_utc = datetime.datetime.now(datetime.timezone.utc)

        # ET 오프셋 계산 (EDT -4 / EST -5)
        et_offset = cls._et_offset_hours(now_utc)
        et_label  = "EDT" if et_offset == -4 else "EST"
        now_et    = now_utc + datetime.timedelta(hours=et_offset)

        # KST = UTC + 9
        now_kst = now_utc + datetime.timedelta(hours=9)

        date_str = now_et.strftime("%Y-%m-%d")
        time_et  = now_et.time()
        weekday  = now_et.weekday()   # 0=Mon … 6=Sun

        # ── 휴장 여부 ──────────────────────────────────────────────
        is_weekend     = weekday >= 5
        holiday_name   = _HOLIDAYS_2026.get(date_str, "")
        is_holiday     = bool(holiday_name)
        early_cl_name  = _EARLY_CLOSE_2026.get(date_str, "")
        is_early_close = bool(early_cl_name)

        # 실효 폐장 시간
        close_time = _EARLY_CLOSE if is_early_close else _MARKET_CLOSE

        # ── 개장 여부 ──────────────────────────────────────────────
        is_open = (
            not is_weekend
            and not is_holiday
            and _MARKET_OPEN <= time_et < close_time
        )

        # ── 시장 단계 ──────────────────────────────────────────────
        if is_weekend or is_holiday:
            phase = "Closed"
        elif time_et < _PREMARKET_START:
            phase = "Closed"
        elif time_et < _MARKET_OPEN:
            phase = "Pre-Market"
        elif time_et < close_time:
            phase = "Open"
        elif time_et < _AFTERHOURS_END:
            phase = "After-Hours"
        else:
            phase = "Closed"

        # ── 오늘의 이벤트 ──────────────────────────────────────────
        events: List[str] = list(_EVENTS_2026.get(date_str, []))
        if is_early_close and early_cl_name:
            events.insert(0, f"⏰ Early Close — {early_cl_name} (13:00 ET)")
        if is_holiday and holiday_name:
            events.insert(0, f"🏖️ Holiday — {holiday_name}")

        # ── 상태 아이콘 / 색상 / 텍스트 ──────────────────────────
        icon, color, text = cls._status_display(phase, events, is_holiday, holiday_name)

        # ── 시간 문자열 ───────────────────────────────────────────
        et_str  = now_et.strftime(f"%a %b %d, %H:%M {et_label}")
        kst_str = now_kst.strftime("%a %b %d, %H:%M KST")

        return MarketCalendarData(
            is_open=is_open,
            is_weekend=is_weekend,
            is_holiday=is_holiday,
            is_early_close=is_early_close,
            holiday_name=holiday_name or early_cl_name,
            market_phase=phase,
            status_icon=icon,
            status_text=text,
            status_color=color,
            et_time_str=et_str,
            kst_time_str=kst_str,
            today_events=events,
            has_events=bool(events),
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _status_display(
        phase: str,
        events: List[str],
        is_holiday: bool,
        holiday_name: str,
    ) -> tuple:
        """(icon, color, text) 결정."""
        has_fomc = any("FOMC" in e for e in events)
        has_data_release = any(
            any(k in e for k in ("CPI", "PPI", "Non-Farm", "Payroll"))
            for e in events
        )
        has_quad = any("Quad Witching" in e for e in events)

        if phase == "Open":
            if has_fomc:
                return "🟡", "#f97316", "US Market Open — FOMC Day"
            if has_data_release:
                return "🟡", "#f97316", "US Market Open — Economic Data Day"
            if has_quad:
                return "🟡", "#f97316", "US Market Open — Quad Witching"
            return "🟢", "#22c55e", "US Market Open"

        if phase == "Pre-Market":
            return "🟡", "#f97316", "US Pre-Market"

        if phase == "After-Hours":
            return "🟡", "#f97316", "US After-Hours"

        # Closed
        if is_holiday:
            short = holiday_name[:30] if holiday_name else "Holiday"
            return "🔴", "#ef4444", f"US Market Closed — {short}"

        return "🔴", "#ef4444", "US Market Closed"

    @staticmethod
    def _et_offset_hours(now_utc: datetime.datetime) -> int:
        """
        EDT = -4 (Daylight Saving: 3월 둘째 일요일 ~ 11월 첫째 일요일)
        EST = -5 (그 외)
        """
        year = now_utc.year

        # DST 시작: 3월 둘째 일요일 2:00 AM EST = 7:00 UTC
        dst_start = datetime.datetime(year, 3, 8, 7, 0, 0,
                                      tzinfo=datetime.timezone.utc)
        while dst_start.weekday() != 6:   # Sunday
            dst_start += datetime.timedelta(days=1)

        # DST 종료: 11월 첫째 일요일 2:00 AM EDT = 6:00 UTC
        dst_end = datetime.datetime(year, 11, 1, 6, 0, 0,
                                    tzinfo=datetime.timezone.utc)
        while dst_end.weekday() != 6:   # Sunday
            dst_end += datetime.timedelta(days=1)

        if dst_start <= now_utc < dst_end:
            return -4   # EDT
        return -5        # EST
