"""
web/utils/data_bridge.py
DSSResult -> UI-friendly data conversion (read-only).
Web Step 3: Checklist, Timeline, ETFSearch, Watchlist, Comparison added.
Architecture 100: HistorySummaryViewData, DiagnosticsViewData, EngineRow.timing_pct added.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ===========================================================================
# View Data Models (Web Step 2)
# ===========================================================================

@dataclass
class HomeViewData:
    action: str
    confidence: float
    confidence_level: str
    top_etfs: List[str]
    allocation_changes: List[Dict]
    market_status: str
    macro_score: float
    risk_level: str
    brief_lines: List[str]
    why_decision: str
    why_now: str
    why_etf: str
    why_allocation: str
    run_date: str
    run_id: str


@dataclass
class MarketCardData:
    label: str
    score: float
    status: str
    trend: str
    detail: str


@dataclass
class MarketViewData:
    macro: MarketCardData
    breadth: MarketCardData
    rs_cards: List[Dict]
    top_rs_sectors: List[str]
    rotation_dominant: str
    rotation_forecast: float
    rotation_active: bool
    market_health_score: float
    market_health_label: str


@dataclass
class AllocRow:
    ticker: str
    target_pct: float
    current_pct: float
    delta_pct: float


@dataclass
class PortfolioViewData:
    rows: List[AllocRow]
    cash_pct: float
    regime: str
    regime_explanation: str
    diversification_score: float
    rebalance_urgency: str
    top_delta_up: List[AllocRow]
    top_delta_down: List[AllocRow]
    expected_return: float
    expected_vol: float


@dataclass
class BacktestViewData:
    grade: str
    cagr: float
    sharpe: float
    sortino: float
    max_drawdown: float
    win_rate: float
    alpha: float
    is_robust: bool
    mc_significant: bool
    warnings: List[str]
    reasons: List[str]
    available: bool


@dataclass
class EngineRow:
    name: str
    elapsed_sec: float
    status: str
    error_message: Optional[str]
    is_critical: bool
    timing_pct: float = 0.0     # (elapsed / max_elapsed) * 100 — DataBridge 계산


@dataclass
class SystemViewData:
    engines: List[EngineRow]
    total_sec: float
    all_success: bool
    failed_engines: List[str]
    success_count: int
    system_health: str
    run_id: str
    run_date: str
    available: bool


# ===========================================================================
# View Data Models (Web Step 3)
# ===========================================================================

@dataclass
class ChecklistItem:
    engine: str
    label: str
    completed: bool
    elapsed_sec: float
    status: str   # SUCCESS / FAILED / SKIPPED / PENDING
    note: str


@dataclass
class ChecklistViewData:
    items: List[ChecklistItem]
    all_complete: bool
    completion_pct: float
    last_update: str
    run_id: str


@dataclass
class TimelineEvent:
    seq: int
    engine: str
    elapsed_sec: float
    status: str
    output_summary: str


@dataclass
class TimelineViewData:
    events: List[TimelineEvent]
    total_sec: float
    run_date: str


@dataclass
class ComparisonData:
    action_changed: bool
    confidence_delta: float
    etf_changed: bool
    change_reason: str


@dataclass
class ETFSearchResult:
    ticker: str
    found: bool
    rs_score: float
    rotation_score: float
    macro_state: str
    is_top: bool
    is_favorite: bool
    is_watchlist: bool
    recommendation: str   # "추천" / "관찰" / "회피" / "정보 없음"
    reason: str


@dataclass
class WatchlistViewData:
    favorites: List[ETFSearchResult]
    watchlist: List[ETFSearchResult]
    all_tickers: List[str]


# ===========================================================================
# View Data Models (Architecture 100 — UI 계산 제거)
# ===========================================================================

@dataclass
class HistorySummaryViewData:
    """Journal 기록 집계 — DataBridge가 계산, UI는 렌더링만."""
    total_entries: int
    avg_confidence: float
    avg_conf_color: str    # score_color() 결과 — pre-computed
    buy_count: int
    sell_count: int
    hold_count: int
    label: str             # "최근 N일" 또는 "기록 없음"


@dataclass
class DiagnosticsViewData:
    """시스템 진단 정보 — Diagnostics 탭 전용."""
    python_version: str
    dss_version: str
    theme_config_loaded: bool
    app_config_loaded: bool
    cache_ttl_sec: int
    pipeline_success: bool
    engine_count: int
    success_count: int
    all_success: bool
    failed_engines: List[str]
    last_update: str
    run_id: str
    memory_mb: float
    cpu_pct: float


# ===========================================================================
# DataBridge
# ===========================================================================

class DataBridge:
    """
    DSSResult -> per-tab ViewData.
    Only this class reads DSSResult fields.
    UI components only render ViewData.
    """

    def __init__(self, result: Any) -> None:
        self._r = result

    # ------------------------------------------------------------------
    # Web Step 2 methods
    # ------------------------------------------------------------------

    def home_data(self) -> HomeViewData:
        r = self._r
        action      = getattr(r, "recommended_action", "WAIT") or "WAIT"
        confidence  = getattr(r, "overall_confidence", 0.0)
        top_etfs    = list(getattr(r, "top_opportunities", []))
        macro_state = getattr(r, "macro_state", "Unknown")
        run_date    = getattr(r, "run_date", "")
        run_id      = getattr(r, "run_id", "")

        macro   = getattr(r, "macro_result", None)
        breadth = getattr(r, "breadth_result", None)
        rot     = getattr(r, "rotation_result", None)
        port    = getattr(r, "portfolio_optimization_result", None)
        val     = getattr(r, "validation_result", None)
        pd_res  = getattr(r, "portfolio_decision_result", None)

        macro_score   = getattr(macro,   "macro_score",   50.0)
        breadth_trend = getattr(breadth, "breadth_trend", "NEUTRAL")
        rot_active    = getattr(rot,     "market_rotation_active", False)

        alloc_changes = self._alloc_changes(port, top_etfs)
        risk_level    = self._risk_level(val)

        return HomeViewData(
            action=action.upper(),
            confidence=round(confidence, 1),
            confidence_level=self._confidence_label(confidence),
            top_etfs=top_etfs,
            allocation_changes=alloc_changes,
            market_status=macro_state,
            macro_score=macro_score,
            risk_level=risk_level,
            brief_lines=self._brief(action, macro_state, breadth_trend, rot_active, risk_level),
            why_decision=self._why_decision(action, macro_state, macro_score),
            why_now=self._why_now(breadth, rot),
            why_etf=self._why_etf(top_etfs, rot),
            why_allocation=self._why_allocation(port, pd_res),
            run_date=run_date,
            run_id=run_id,
        )

    def market_data(self) -> MarketViewData:
        r = self._r
        macro   = getattr(r, "macro_result",   None)
        breadth = getattr(r, "breadth_result", None)
        rs      = getattr(r, "rs_result",      None)
        rot     = getattr(r, "rotation_result",None)

        m_score  = getattr(macro,   "macro_score",    0.0)
        m_state  = getattr(macro,   "macro_state",    "Unknown")
        m_dir    = getattr(macro,   "macro_direction","NEUTRAL")
        b_score  = getattr(breadth, "breadth_score",  0.0)
        b_health = getattr(breadth, "breadth_health", "Neutral")
        b_trend  = getattr(breadth, "breadth_trend",  "NEUTRAL")

        sector_results = getattr(rs, "sector_results", {}) or {}
        rs_cards = sorted(
            [{"ticker": t, "score": round(getattr(v, "rs_score", 0.0), 1)}
             for t, v in sector_results.items()],
            key=lambda x: -x["score"]
        )
        for i, c in enumerate(rs_cards):
            c["rank"] = i + 1
        top_rs = [c["ticker"] for c in rs_cards[:3]]

        rot_dominant = getattr(rot, "dominant_rotation",    "N/A")
        rot_forecast = getattr(rot, "rotation_forecast",    0.0)
        rot_active   = getattr(rot, "market_rotation_active", False)

        health       = (m_score + b_score) / 2
        health_label = "강세" if health >= 65 else ("중립" if health >= 45 else "약세")

        return MarketViewData(
            macro=MarketCardData(label="거시경제", score=round(m_score,1),
                                 status=m_state,  trend=m_dir,
                                 detail=f"방향: {m_dir}"),
            breadth=MarketCardData(label="시장 폭", score=round(b_score,1),
                                   status=b_health, trend=b_trend,
                                   detail=f"추세: {b_trend}"),
            rs_cards=rs_cards,
            top_rs_sectors=top_rs,
            rotation_dominant=rot_dominant,
            rotation_forecast=round(rot_forecast,1),
            rotation_active=rot_active,
            market_health_score=round(health,1),
            market_health_label=health_label,
        )

    def portfolio_data(self) -> PortfolioViewData:
        r    = self._r
        port = getattr(r, "portfolio_optimization_result", None)

        target  = getattr(port, "target_allocation",  {}) or {}
        current = getattr(port, "current_allocation", {}) or {}
        delta   = getattr(port, "delta_allocation",   {}) or {}
        cash    = getattr(port, "cash_recommendation", 0.0)

        regime_obj = getattr(port, "regime", None)
        regime     = getattr(regime_obj, "value", "Unknown")
        regime_exp = getattr(port, "regime_explanation", "")
        div_score  = getattr(port, "diversification_score", 0.0)

        reb_signal      = getattr(port, "rebalance_signal", None)
        reb_urgency_obj = getattr(reb_signal, "urgency", None)
        reb_urgency     = getattr(reb_urgency_obj, "value", "Unknown")

        mc      = getattr(port, "monte_carlo", None)
        exp_ret = getattr(mc, "expected_annual_return", 0.0)
        exp_vol = getattr(mc, "expected_annual_vol",    0.0)

        rows: List[AllocRow] = [
            AllocRow(
                ticker=ticker,
                target_pct=round(target.get(ticker, 0.0) * 100, 1),
                current_pct=round(current.get(ticker, 0.0) * 100, 1),
                delta_pct=round(delta.get(ticker, 0.0) * 100, 1),
            )
            for ticker in sorted(target.keys())
        ]
        rows_by_delta = sorted(rows, key=lambda x: -x.delta_pct)
        top_up   = [r2 for r2 in rows_by_delta if r2.delta_pct > 0][:3]
        top_down = [r2 for r2 in reversed(rows_by_delta) if r2.delta_pct < 0][:3]

        return PortfolioViewData(
            rows=rows,
            cash_pct=round(cash * 100, 1),
            regime=regime,
            regime_explanation=regime_exp,
            diversification_score=round(div_score, 1),
            rebalance_urgency=reb_urgency,
            top_delta_up=top_up,
            top_delta_down=top_down,
            expected_return=round(exp_ret * 100, 1),
            expected_vol=round(exp_vol * 100, 1),
        )

    def backtest_data(self) -> BacktestViewData:
        r   = self._r
        val = getattr(r, "validation_result", None)
        if val is None:
            return BacktestViewData(
                grade="N/A", cagr=0.0, sharpe=0.0, sortino=0.0,
                max_drawdown=0.0, win_rate=0.0, alpha=0.0,
                is_robust=False, mc_significant=False,
                warnings=[], reasons=[], available=False,
            )

        grade_obj = getattr(val, "overall_grade", None)
        grade     = getattr(grade_obj, "value", "N/A")
        rm        = getattr(val, "risk_metrics", None)
        bt        = getattr(val, "backtest",     None)
        attr      = getattr(val, "attribution",  None)

        return BacktestViewData(
            grade=grade,
            cagr=round(getattr(rm,   "cagr",        0.0) * 100, 2),
            sharpe=round(getattr(rm, "sharpe",       0.0),       2),
            sortino=round(getattr(rm,"sortino",      0.0),       2),
            max_drawdown=round(getattr(rm,"max_drawdown",0.0)*100, 2),
            win_rate=round(getattr(bt,   "win_rate", 0.0) * 100, 1),
            alpha=round(getattr(attr,"total_alpha",  0.0) * 100, 2),
            is_robust=bool(getattr(val, "is_robust",       False)),
            mc_significant=bool(getattr(val,"mc_significant",False)),
            warnings=list(getattr(val, "warnings", []) or []),
            reasons=list(getattr(val,  "reasons",  []) or []),
            available=True,
        )

    def system_data(self) -> SystemViewData:
        r       = self._r
        mon     = getattr(r, "monitor_result", None)
        health  = getattr(r, "system_health",  "UNKNOWN")
        run_id  = getattr(r, "run_id",   "")
        run_date= getattr(r, "run_date", "")

        if mon is None:
            return SystemViewData(
                engines=[], total_sec=0.0, all_success=False,
                failed_engines=[], success_count=0,
                system_health=health, run_id=run_id,
                run_date=run_date, available=False,
            )

        rows = [
            EngineRow(
                name=e.engine_name,
                elapsed_sec=e.elapsed_sec,
                status=e.status.value,
                error_message=e.error_message,
                is_critical=e.is_critical,
            )
            for e in (getattr(mon, "engines", []) or [])
        ]
        # timing_pct: (elapsed / max_elapsed) * 100 — DataBridge에서 계산, UI 계산 금지
        if rows:
            max_t = max(r.elapsed_sec for r in rows) or 1.0
            for row in rows:
                row.timing_pct = round((row.elapsed_sec / max_t) * 100, 1)

        return SystemViewData(
            engines=rows,
            total_sec=getattr(mon, "total_elapsed_sec", 0.0),
            all_success=getattr(mon, "all_success",    True),
            failed_engines=list(getattr(mon, "failed_engines", []) or []),
            success_count=getattr(mon, "success_count", 0),
            system_health=health,
            run_id=run_id,
            run_date=run_date,
            available=True,
        )

    # ------------------------------------------------------------------
    # Web Step 3 methods
    # ------------------------------------------------------------------

    def checklist_data(self) -> ChecklistViewData:
        r   = self._r
        mon = getattr(r, "monitor_result", None)

        ENGINE_LABELS = {
            "Macro Engine":               "거시경제 분석",
            "Breadth Engine":             "시장 폭 분석",
            "Relative Strength Engine":   "상대강도 분석",
            "Rotation Engine":            "섹터 순환 분석",
            "Portfolio Decision Engine":  "투자 결정",
            "Portfolio Optimizer Engine": "포트폴리오 최적화",
            "Validation Engine":          "성과 검증",
            "Dashboard Engine":           "대시보드 집계",
        }

        if mon is None:
            items = [
                ChecklistItem(engine=eng, label=label, completed=False,
                              elapsed_sec=0.0, status="PENDING", note="데이터 없음")
                for eng, label in ENGINE_LABELS.items()
            ]
            return ChecklistViewData(
                items=items, all_complete=False, completion_pct=0.0,
                last_update=getattr(r, "run_date", ""),
                run_id=getattr(r, "run_id", ""),
            )

        engines_map = {e.engine_name: e for e in (getattr(mon, "engines", []) or [])}
        items = []
        for eng, label in ENGINE_LABELS.items():
            e = engines_map.get(eng)
            if e is None:
                items.append(ChecklistItem(engine=eng, label=label, completed=False,
                                           elapsed_sec=0.0, status="PENDING", note="미실행"))
            else:
                ok   = e.status.value == "SUCCESS"
                note = (f"완료 ({e.elapsed_sec:.2f}s)" if ok
                        else f"오류: {(e.error_message or '')[:40]}")
                items.append(ChecklistItem(engine=eng, label=label, completed=ok,
                                           elapsed_sec=e.elapsed_sec,
                                           status=e.status.value, note=note))

        n   = len(items)
        cnt = sum(1 for it in items if it.completed)
        pct = round(cnt / n * 100, 0) if n else 0.0

        return ChecklistViewData(
            items=items,
            all_complete=getattr(mon, "all_success", False),
            completion_pct=pct,
            last_update=getattr(r, "run_date", ""),
            run_id=getattr(r, "run_id", ""),
        )

    def timeline_data(self) -> TimelineViewData:
        r   = self._r
        mon = getattr(r, "monitor_result", None)

        def _summary(eng_name: str) -> str:
            result_map = {
                "Macro Engine": (
                    getattr(r, "macro_result", None),
                    lambda x: f"score={getattr(x,'macro_score',0):.1f}, state={getattr(x,'macro_state','')}"),
                "Breadth Engine": (
                    getattr(r, "breadth_result", None),
                    lambda x: f"score={getattr(x,'breadth_score',0):.1f}, health={getattr(x,'breadth_health','')}"),
                "Relative Strength Engine": (
                    getattr(r, "rs_result", None),
                    lambda x: f"avg_rs={getattr(x,'avg_rs_score',0):.1f}"),
                "Rotation Engine": (
                    getattr(r, "rotation_result", None),
                    lambda x: f"dominant={getattr(x,'dominant_rotation','?')}, forecast={getattr(x,'rotation_forecast',0):.0f}"),
                "Portfolio Decision Engine": (
                    getattr(r, "portfolio_decision_result", None),
                    lambda x: f"action={getattr(x,'action','?')}, score={getattr(x,'decision_score',0):.1f}"),
                "Portfolio Optimizer Engine": (
                    getattr(r, "portfolio_optimization_result", None),
                    lambda x: f"regime={getattr(getattr(x,'regime',None),'value','?')}, div={getattr(x,'diversification_score',0):.0f}"),
                "Validation Engine": (
                    getattr(r, "validation_result", None),
                    lambda x: f"grade={getattr(getattr(x,'overall_grade',None),'value','?')}"),
                "Dashboard Engine": (
                    getattr(r, "dashboard_result", None),
                    lambda x: f"confidence={getattr(x,'confidence',0):.1f}"),
            }
            entry = result_map.get(eng_name)
            if not entry:
                return ""
            obj, fmt = entry
            if obj is None:
                return "결과 없음"
            try:
                return fmt(obj)
            except Exception:
                return "요약 불가"

        if mon is None:
            return TimelineViewData(events=[], total_sec=0.0,
                                    run_date=getattr(r, "run_date", ""))

        events = [
            TimelineEvent(
                seq=i + 1,
                engine=e.engine_name,
                elapsed_sec=e.elapsed_sec,
                status=e.status.value,
                output_summary=_summary(e.engine_name),
            )
            for i, e in enumerate(getattr(mon, "engines", []) or [])
        ]
        return TimelineViewData(
            events=events,
            total_sec=getattr(mon, "total_elapsed_sec", 0.0),
            run_date=getattr(r, "run_date", ""),
        )

    def search_etf(self, ticker: str, wl_mgr: Any = None) -> ETFSearchResult:
        r      = self._r
        ticker = ticker.upper().strip()

        rs  = getattr(r, "rs_result",      None)
        rot = getattr(r, "rotation_result", None)
        top = list(getattr(r, "top_opportunities", []))

        rs_entry  = getattr(rs,  "sector_results", {}).get(ticker) if rs  else None
        rot_entry = getattr(rot, "sector_results", {}).get(ticker) if rot else None

        found     = rs_entry is not None or rot_entry is not None
        rs_score  = round(getattr(rs_entry,  "rs_score",       0.0), 1) if rs_entry  else 0.0
        rot_score = round(getattr(rot_entry, "rotation_score", 0.0), 1) if rot_entry else 0.0
        macro_state = getattr(r, "macro_state", "Unknown")
        is_top    = ticker in top

        if not found:
            recommendation = "정보 없음"
            reason = "현재 분석 대상에 포함되지 않은 티커입니다."
        elif is_top or rs_score >= 65:
            recommendation = "추천"
            reason = f"RS {rs_score:.0f}점 — 상위 모멘텀, 포트폴리오 편입 권고"
        elif rs_score >= 45:
            recommendation = "관찰"
            reason = f"RS {rs_score:.0f}점 — 중립, 추가 모멘텀 확인 필요"
        else:
            recommendation = "회피"
            reason = f"RS {rs_score:.0f}점 — 하위 모멘텀, 현 시점 편입 비권고"

        is_fav = wl_mgr.is_favorite(ticker)  if wl_mgr else False
        is_wl  = wl_mgr.is_watchlist(ticker) if wl_mgr else False

        return ETFSearchResult(
            ticker=ticker, found=found,
            rs_score=rs_score, rotation_score=rot_score,
            macro_state=macro_state, is_top=is_top,
            is_favorite=is_fav, is_watchlist=is_wl,
            recommendation=recommendation, reason=reason,
        )

    def watchlist_data(self, wl_mgr: Any) -> WatchlistViewData:
        r   = self._r
        rs  = getattr(r, "rs_result", None)
        all_tickers = sorted(
            getattr(rs, "sector_results", {}).keys() if rs else []
        )
        return WatchlistViewData(
            favorites=[self.search_etf(t, wl_mgr) for t in wl_mgr.favorites],
            watchlist=[self.search_etf(t, wl_mgr) for t in wl_mgr.watchlist],
            all_tickers=all_tickers,
        )

    def comparison_data(self, today_entry: Any,
                        yesterday_entry: Any) -> ComparisonData:
        if yesterday_entry is None:
            return ComparisonData(
                action_changed=False, confidence_delta=0.0,
                etf_changed=False, change_reason="이전 기록이 없습니다.",
            )
        t_action = getattr(today_entry,     "action",     "")
        y_action = getattr(yesterday_entry, "action",     "")
        t_conf   = getattr(today_entry,     "confidence", 0.0)
        y_conf   = getattr(yesterday_entry, "confidence", 0.0)
        t_etfs   = set(getattr(today_entry,     "top_etfs", []))
        y_etfs   = set(getattr(yesterday_entry, "top_etfs", []))

        conf_delta    = round(t_conf - y_conf, 1)
        action_changed = t_action != y_action
        etf_changed    = t_etfs != y_etfs

        reasons = []
        if action_changed:
            reasons.append(f"액션 변경: {y_action} → {t_action}")
        if abs(conf_delta) >= 5:
            reasons.append(f"신뢰도 {'상승' if conf_delta > 0 else '하락'}: {conf_delta:+.1f}%")
        if etf_changed:
            added   = t_etfs - y_etfs
            removed = y_etfs - t_etfs
            if added:   reasons.append(f"신규 추천: {', '.join(sorted(added))}")
            if removed: reasons.append(f"제외: {', '.join(sorted(removed))}")
        if not reasons:
            reasons.append("전일 대비 변동 없음")

        return ComparisonData(
            action_changed=action_changed,
            confidence_delta=conf_delta,
            etf_changed=etf_changed,
            change_reason=" / ".join(reasons),
        )

    # ------------------------------------------------------------------
    # Architecture 100 methods (UI 계산 완전 제거)
    # ------------------------------------------------------------------

    def history_summary(self, entries: List[Any]) -> HistorySummaryViewData:
        """
        Journal entries → 집계 ViewData.
        avg_conf, action counts 등 모든 집계를 DataBridge에서 계산.
        UI(history.py)는 이 ViewData를 렌더링만 한다.
        """
        if not entries:
            return HistorySummaryViewData(
                total_entries=0,
                avg_confidence=0.0,
                avg_conf_color="#64748b",   # MUTED_COLOR
                buy_count=0,
                sell_count=0,
                hold_count=0,
                label="기록 없음",
            )
        total      = len(entries)
        avg_conf   = sum(getattr(e, "confidence", 0.0) for e in entries) / total
        buy_count  = sum(1 for e in entries if getattr(e, "action", "") == "BUY")
        sell_count = sum(1 for e in entries if getattr(e, "action", "") == "SELL")
        hold_count = sum(1 for e in entries if getattr(e, "action", "") in ("HOLD", "WAIT"))
        return HistorySummaryViewData(
            total_entries=total,
            avg_confidence=round(avg_conf, 1),
            avg_conf_color=self._score_color(avg_conf),
            buy_count=buy_count,
            sell_count=sell_count,
            hold_count=hold_count,
            label=f"최근 {total}일",
        )

    def diagnostics_data(self) -> DiagnosticsViewData:
        """
        시스템 진단 정보 → DiagnosticsViewData.
        Python 버전, config 파일 존재 여부, 메모리/CPU, Pipeline 상태.
        """
        import sys
        import os

        r   = self._r
        mon = getattr(r, "monitor_result", None)

        # Python version
        vi = sys.version_info
        py_ver = f"{vi.major}.{vi.minor}.{vi.micro}"

        # Config 파일 존재 여부 확인
        _this  = os.path.abspath(__file__)                  # .../web/utils/data_bridge.py
        _root  = os.path.dirname(os.path.dirname(os.path.dirname(_this)))  # project root
        theme_loaded = os.path.isfile(os.path.join(_root, "config", "theme.yaml"))
        app_loaded   = os.path.isfile(os.path.join(_root, "config", "app_config.yaml"))

        # Pipeline 상태
        all_success    = getattr(mon, "all_success",    False) if mon else False
        engine_count   = len(getattr(mon, "engines",    []) or []) if mon else 0
        success_count  = getattr(mon, "success_count",  0) if mon else 0
        failed_engines = list(getattr(mon, "failed_engines", []) or []) if mon else []

        # Memory / CPU (psutil 선택 사항)
        memory_mb = 0.0
        cpu_pct   = 0.0
        try:
            import psutil
            proc      = psutil.Process(os.getpid())
            memory_mb = proc.memory_info().rss / 1024 / 1024
            cpu_pct   = psutil.cpu_percent(interval=None)
        except Exception:
            pass

        return DiagnosticsViewData(
            python_version=py_ver,
            dss_version="1.0.0",
            theme_config_loaded=theme_loaded,
            app_config_loaded=app_loaded,
            cache_ttl_sec=300,
            pipeline_success=bool(getattr(r, "pipeline_success", False)),
            engine_count=engine_count,
            success_count=success_count,
            all_success=all_success,
            failed_engines=failed_engines,
            last_update=getattr(r, "run_date", ""),
            run_id=getattr(r, "run_id", ""),
            memory_mb=round(memory_mb, 1),
            cpu_pct=round(cpu_pct, 1),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _score_color(score: float) -> str:
        """0~100 점수 → 색상 (theme.py 미참조 — 순환 import 방지)."""
        if score >= 65: return "#22c55e"   # BUY_COLOR
        if score >= 45: return "#3b82f6"   # INFO_COLOR
        return "#ef4444"                   # SELL_COLOR

    def _alloc_changes(self, port: Any, top_etfs: List[str]) -> List[Dict]:
        delta = getattr(port, "delta_allocation", {}) or {}
        result = []
        for ticker, d in delta.items():
            pct = round(d * 100, 1)
            if abs(pct) < 0.1:
                continue
            result.append({
                "ticker": ticker,
                "delta_pct": pct,
                "direction": "+" if pct > 0 else "-",
                "is_top": ticker in top_etfs,
            })
        result.sort(key=lambda x: -abs(x["delta_pct"]))
        return result[:5]

    @staticmethod
    def _confidence_label(score: float) -> str:
        if score >= 80: return "매우 높음"
        if score >= 65: return "높음"
        if score >= 50: return "보통"
        if score >= 35: return "낮음"
        return "매우 낮음"

    @staticmethod
    def _risk_level(val: Any) -> str:
        rm = getattr(val, "risk_metrics", None)
        if rm is None:
            return "보통"
        max_dd = getattr(rm, "max_drawdown", 0.0)
        if max_dd < 0.10: return "낮음"
        if max_dd < 0.20: return "보통"
        return "높음"

    @staticmethod
    def _brief(action: str, macro_state: str, breadth_trend: str,
               rot_active: bool, risk: str) -> List[str]:
        line1 = (f"현재 시장은 {macro_state} 국면으로, "
                 f"시장 폭이 {'확대' if breadth_trend == 'UP' else '축소'}되고 있습니다.")
        if action == "BUY":
            line2 = "섹터 순환이 활발하여 적극적 매수 기회가 포착되었습니다."
        elif action == "SELL":
            line2 = "하락 압력이 강화되고 있어 포트폴리오 방어가 권고됩니다."
        else:
            line2 = "뚜렷한 방향성이 없어 현 포지션 유지를 권고합니다."
        line3 = f"리스크 수준: {risk} — 포지션 비중 조절 시 유의하세요."
        return [line1, line2, line3]

    @staticmethod
    def _why_decision(action: str, macro_state: str, macro_score: float) -> str:
        state_map = {
            "Expansion": "경제 확장기로 위험자산 선호도가 높습니다",
            "Slowdown":  "경기 둔화 국면으로 선별적 접근이 필요합니다",
            "Recession": "경기 침체 우려가 있어 방어적 포지션이 적합합니다",
        }
        state_desc = state_map.get(macro_state, f"{macro_state} 국면")
        signal = ("매수 신호" if action == "BUY"
                  else ("매도 신호" if action == "SELL" else "중립 신호"))
        return (f"{state_desc}. "
                f"거시경제 종합 점수는 {macro_score:.0f}/100점으로 {signal}를 나타냅니다.")

    @staticmethod
    def _why_now(breadth: Any, rot: Any) -> str:
        b_trend      = getattr(breadth, "breadth_trend",        "NEUTRAL")
        b_score      = getattr(breadth, "breadth_score",        50.0)
        rot_active   = getattr(rot,     "market_rotation_active", False)
        rot_forecast = getattr(rot,     "rotation_forecast",    50.0)
        direction    = "상승 추세" if b_trend == "UP" else "하락 추세"
        rotation_st  = "활발하게 진행 중" if rot_active else "정체 상태"
        return (f"시장 폭 지표({b_score:.0f}점)가 {direction}를 보이고 있으며, "
                f"섹터 순환이 {rotation_st}입니다 (순환 강도: {rot_forecast:.0f}점).")

    @staticmethod
    def _why_etf(top_etfs: List[str], rot: Any) -> str:
        dominant = getattr(rot, "dominant_rotation", None)
        if not top_etfs and not dominant:
            return "현재 상위 기회 ETF가 확인되지 않았습니다. 시장 안정화 후 재평가 권고합니다."
        etfs    = top_etfs if top_etfs else ([dominant] if dominant else [])
        etf_str = ", ".join(etfs)
        dom     = dominant or etfs[0]
        return (f"{etf_str}는 상대강도(RS) 및 섹터 순환 분석에서 최상위 모멘텀을 보이고 있습니다. "
                f"현재 주도 섹터는 {dom}로, 자금 유입이 지속되고 있습니다.")

    @staticmethod
    def _why_allocation(port: Any, pd_res: Any) -> str:
        regime_obj = getattr(port, "regime", None)
        regime     = getattr(regime_obj, "value", "Unknown")
        div_score  = getattr(port, "diversification_score", 0.0)
        reasons    = getattr(port, "reasons", []) or []
        reason_str = reasons[0] if reasons else "시장 상황에 따른 최적 배분"
        return (f"{regime} 국면에 맞춰 포트폴리오를 최적화했습니다. "
                f"분산화 점수: {div_score:.0f}/100. "
                f"핵심 근거: {reason_str}.")

    # STEP 7 — Operation Validation methods
    # ------------------------------------------------------------------

    def market_status(self) -> MarketStatusViewData:
        """
        현재 US 시장 상태 + 경제 이벤트 → MarketStatusViewData.
        외부 API 없음 — MarketCalendar(순수 datetime 기반) 호출.
        """
        from web.utils.market_calendar import MarketCalendar, MarketCalendarData
        cal: MarketCalendarData = MarketCalendar.get_status()
        return MarketStatusViewData(
            is_open=cal.is_open,
            is_weekend=cal.is_weekend,
            is_holiday=cal.is_holiday,
            is_early_close=cal.is_early_close,
            holiday_name=cal.holiday_name,
            market_phase=cal.market_phase,
            status_icon=cal.status_icon,
            status_text=cal.status_text,
            status_color=cal.status_color,
            et_time_str=cal.et_time_str,
            kst_time_str=cal.kst_time_str,
            today_events=list(cal.today_events),
            has_events=cal.has_events,
        )

    def daily_op_check(
        self,
        journal_today: bool = False,
        journal_count: int = 0,
    ) -> DailyOpCheckViewData:
        """
        운영 체크리스트 7개 항목 → DailyOpCheckViewData.
        DataBridge가 계산. UI는 렌더링만.
        """
        import datetime as _dt
        r   = self._r
        mon = getattr(r, "monitor_result", None)

        run_id   = getattr(r, "run_id",   "") or ""
        run_date = getattr(r, "run_date", "") or ""

        # ① 데이터 최신 여부
        data_fresh = bool(run_date) and run_id != "DEMO"
        data_detail = (f"실행: {run_date[:16]}" if data_fresh
                       else "Demo 데이터 사용 중 (Pipeline 실패 폴백)")

        # ② Engine 성공 여부
        engines_list = getattr(mon, "engines", []) or [] if mon else []
        suc_count    = sum(1 for e in engines_list if getattr(e, "succeeded", False))
        eng_count    = len(engines_list)
        all_eng_ok   = bool(getattr(mon, "all_success", False)) if mon else False
        eng_detail   = (f"{suc_count}/{eng_count} 성공" if mon
                        else "Monitor 없음 (Demo 모드)")

        # ③ Recommendation 생성 여부
        action = getattr(r, "recommended_action", "") or ""
        rec_ok = action in ("BUY", "SELL", "HOLD", "WAIT")
        rec_detail = f"오늘 결정: {action}" if rec_ok else "추천 생성 실패"

        # ④ Journal 저장 여부
        journal_ok     = journal_today and journal_count > 0
        journal_detail = (f"{journal_count}일 기록 / 오늘 저장됨" if journal_ok
                          else "오늘 기록 없음 (접속 후 자동 저장됨)")

        # ⑤ Cache 상태
        cache_ok     = True       # _run_pipeline() 성공 = cache 정상
        cache_detail = "TTL 300초 (5분 자동 갱신)"

        # ⑥ Engine Monitor 상태
        monitor_ok     = mon is not None
        monitor_detail = ("Monitor 연결됨" if monitor_ok
                          else "Monitor 없음 (Demo 모드)")

        # ⑦ Dashboard 상태
        dash        = getattr(r, "dashboard_result", None)
        dash_ok     = dash is not None or rec_ok
        dash_detail = "Dashboard 생성됨" if dash_ok else "Dashboard 없음"

        def _item(label: str, ok: bool, detail: str) -> DailyOpCheckItem:
            icon = "✅" if ok else "⚠️"
            return DailyOpCheckItem(label=label, ok=ok, detail=detail, icon=icon)

        items = [
            _item("데이터 최신",        data_fresh,   data_detail),
            _item("모든 Engine 성공",   all_eng_ok,   eng_detail),
            _item("Recommendation 생성", rec_ok,      rec_detail),
            _item("Journal 저장",       journal_ok,   journal_detail),
            _item("Cache 정상",         cache_ok,     cache_detail),
            _item("Engine Monitor 정상", monitor_ok,  monitor_detail),
            _item("Dashboard 정상",     dash_ok,      dash_detail),
        ]

        ok_count = sum(1 for it in items if it.ok)
        return DailyOpCheckViewData(
            items=items,
            all_ok=(ok_count == len(items)),
            ok_count=ok_count,
            total=len(items),
            last_check=run_date[:16] if run_date else "N/A",
        )


# ===========================================================================
# View Data Models (STEP 7 — Operation Validation)
# ===========================================================================


@dataclass
class MarketStatusViewData:
    """US 시장 상태 + 경제 이벤트. MarketCalendar → DataBridge → UI."""
    is_open: bool
    is_weekend: bool
    is_holiday: bool
    is_early_close: bool
    holiday_name: str
    market_phase: str      # "Open" / "Pre-Market" / "After-Hours" / "Closed"
    status_icon: str       # 🟢 / 🟡 / 🔴
    status_text: str       # "US Market Open" etc.
    status_color: str      # hex color
    et_time_str: str       # "Mon Jun 29, 10:30 EDT"
    kst_time_str: str      # "Tue Jun 30, 23:30 KST"
    today_events: List[str] = field(default_factory=list)
    has_events: bool = False


@dataclass
class DailyOpCheckItem:
    """운영 체크리스트 단일 항목."""
    label: str    # "데이터 최신"
    ok: bool
    detail: str   # "실행: 2026-06-29 09:00"
    icon: str     # "✅" / "⚠️" / "❌"


@dataclass
class DailyOpCheckViewData:
    """Daily Operation Checklist — Diagnostics 탭에 렌더링."""
    items: List[DailyOpCheckItem]
    all_ok: bool
    ok_count: int
    total: int
    last_check: str   # run_date 앞 16자 or "N/A"


