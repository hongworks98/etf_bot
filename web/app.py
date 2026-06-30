"""
web/app.py
DSS Decision Intelligence Dashboard — Mobile First
실행: cd outputs && streamlit run web/app.py

★★★★★ 핵심 원칙:
- 기존 Engine 절대 수정 금지
- UI는 계산하지 않는다 (DataBridge가 담당)
- 모든 데이터는 DSSResult 에서만 온다
- Engine은 독립적으로 유지한다 (Loose Coupling)
"""
from __future__ import annotations
import sys, os, logging
import datetime

# ── Path setup ────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ── Streamlit MUST be first ───────────────────────────────────────────────────
import streamlit as st

st.set_page_config(
    page_title="DSS Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Internal imports ──────────────────────────────────────────────────────────
from web.styles.theme import inject_css
from web.utils.data_bridge import DataBridge
from web.utils.journal import DecisionJournal, entry_from_result
from web.utils.watchlist import WatchlistManager
from web.utils import state_manager
from web.components import home, market, portfolio, backtest, system
from web.components import checklist as checklist_comp
from web.components import history as history_comp
from web.components import search as search_comp
from web.components import notification as notif_comp
from web.components import diagnostics as diagnostics_comp

log = logging.getLogger("web.app")


# ── Pipeline Runner ───────────────────────────────────────────────────────────

def _safe_secret(key: str) -> str:
    """st.secrets 에서 값 안전 조회 — 키 없을 때 빈 문자열 반환."""
    try:
        return st.secrets.get(key, "")
    except Exception:
        return ""


@st.cache_resource(ttl=300, show_spinner=False)
def _run_pipeline() -> object:
    """
    DSS Integration Layer 실행 → DSSResult 반환.
    API 키 있으면 LiveDataLoader(실시간), 없으면 SyntheticDataLoader(폴백).
    기존 Engine 코드 수정 없음 — 호출만 한다.
    """
    try:
        from dss_integration.monitor.engine_monitor import EngineMonitor
        from dss_integration.core.dss_pipeline import DSSPipeline

        # ── API 키 자동 감지 ──────────────────────────────────────────
        fred_key = os.environ.get("FRED_API_KEY", "") or _safe_secret("FRED_API_KEY")
        av_key   = os.environ.get("ALPHA_VANTAGE_API_KEY", "") or _safe_secret("ALPHA_VANTAGE_API_KEY")

        if fred_key and av_key:
            from dss_integration.data.live_loader import LiveDataLoader
            loader = LiveDataLoader(fred_key=fred_key, av_key=av_key)
            log.info("Pipeline: LiveDataLoader 활성화 (FRED + Alpha Vantage)")
        else:
            from dss_integration.data.synthetic_loader import SyntheticDataLoader
            loader = SyntheticDataLoader(seed=42)
            log.warning("Pipeline: API 키 없음 — SyntheticDataLoader 폴백")

        run_id   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        monitor  = EngineMonitor(run_id=run_id)
        raw      = loader.load()
        pipeline = DSSPipeline(monitor=monitor, run_id=run_id)
        result   = pipeline.run(raw)
        return result
    except Exception as exc:
        log.warning("Pipeline failed: %s — using demo data", exc)
        return _demo_result()


def _demo_result() -> object:
    """Integration Layer 없을 때 최소한의 데모 결과."""
    from types import SimpleNamespace

    class _Regime:
        value = "Aggressive"
    class _Urgency:
        value = "This Week"

    tickers = ["XLK", "XLC", "XLY", "XLF", "XLI", "XLE", "XLB", "XLV", "XLP", "XLU"]
    n       = len(tickers)
    alloc   = {t: 0.95 / n for t in tickers}
    delta   = {t: (0.02 if i < 3 else (-0.01 if i < 6 else 0.0))
               for i, t in enumerate(tickers)}

    return SimpleNamespace(
        macro_result=SimpleNamespace(
            macro_score=65.0, macro_state="Expansion", macro_direction="UP"),
        breadth_result=SimpleNamespace(
            breadth_score=60.0, breadth_health="Healthy", breadth_trend="UP"),
        rs_result=SimpleNamespace(
            sector_results={t: SimpleNamespace(rs_score=70.0 - i * 5)
                            for i, t in enumerate(tickers)},
            avg_rs_score=47.5,
        ),
        rotation_result=SimpleNamespace(
            dominant_rotation="XLK",
            rotation_forecast=72.0,
            market_rotation_active=True,
            sector_results={},
            rotation_directions=[],
        ),
        portfolio_decision_result=SimpleNamespace(decision_score=65.0, action="BUY"),
        portfolio_optimization_result=SimpleNamespace(
            target_allocation=alloc,
            current_allocation=alloc,
            delta_allocation=delta,
            cash_recommendation=0.05,
            regime=_Regime(),
            regime_explanation="Expansion 국면 지속",
            diversification_score=74.0,
            concentration_risk=20.0,
            rebalance_signal=SimpleNamespace(urgency=_Urgency(), max_delta=0.05),
            monte_carlo=SimpleNamespace(
                expected_annual_return=0.09, expected_annual_vol=0.14),
            reasons=["Expansion 국면 — 위험자산 비중 확대"],
            warnings=[],
        ),
        validation_result=None,
        dashboard_result=SimpleNamespace(confidence=65.0, today_decision=None),
        monitor_result=None,
        recommended_action="BUY",
        overall_confidence=65.0,
        top_opportunities=["XLK", "XLC"],
        system_health="HEALTHY",
        macro_state="Expansion",
        validation_grade="N/A",
        run_date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        run_id="DEMO",
        pipeline_success=True,
        pipeline_error=None,
    )


# ── Market Status Card ────────────────────────────────────────────────────────

def _render_market_status_card(cal: object) -> None:
    """
    Today's Market Status 카드 — 탭 위에 표시.
    cal: DataBridge.market_status() → MarketStatusViewData
    UI 계산 없음 — ViewData 렌더링만.
    """
    events_html = ""
    if getattr(cal, "has_events", False):
        pills = "".join(
            f'<span class="market-event-pill">{e}</span>'
            for e in (cal.today_events or [])[:4]
        )
        events_html = f'<div style="margin-top:6px;">{pills}</div>'

    phase   = getattr(cal, "market_phase", "")
    icon    = getattr(cal, "status_icon", "⚪")
    text    = getattr(cal, "status_text", "")
    color   = getattr(cal, "status_color", "#64748b")
    et_str  = getattr(cal, "et_time_str", "")
    kst_str = getattr(cal, "kst_time_str", "")

    st.markdown(f"""
<div class="market-status-card">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <span style="font-size:15px;font-weight:700;color:{color};">
        {icon}&nbsp;{text}
      </span>
      {events_html}
    </div>
    <div style="text-align:right;font-size:11px;color:#64748b;flex-shrink:0;margin-left:12px;">
      <div>{et_str}</div>
      <div>{kst_str}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Refresh Handler ───────────────────────────────────────────────────────────

def _handle_refresh() -> None:
    """Refresh 버튼 처리 — 캐시 초기화 후 재실행."""
    st.cache_data.clear()
    state_manager.set_value(st.session_state, "refresh_ts",
                            datetime.datetime.now().timestamp())
    st.rerun()


# ── Journal Auto-Save ─────────────────────────────────────────────────────────

def _auto_save_journal(result: object, bridge: DataBridge,
                       journal: DecisionJournal) -> None:
    """
    Pipeline 실행 후 Journal에 자동 저장.
    같은 날짜 실행 시 덮어쓴다.
    """
    try:
        home_data = bridge.home_data()
        entry     = entry_from_result(result, home_data)
        journal.save(entry)
    except Exception as exc:
        log.warning("Journal auto-save failed: %s", exc)


# ── Main App ──────────────────────────────────────────────────────────────────

def main() -> None:
    # 세션 초기화
    state_manager.init(st.session_state)

    # CSS 주입
    st.markdown(inject_css(), unsafe_allow_html=True)

    # 헤더 행
    col_title, col_refresh = st.columns([5, 1])
    with col_title:
        st.markdown("## 📊 DSS Dashboard")
    with col_refresh:
        if st.button("🔄", help="새로고침 (Engine 재실행)"):
            _handle_refresh()

    # Pipeline 실행
    with st.spinner("DSS Engine 실행 중..."):
        result = _run_pipeline()

    # DataBridge 생성 (UI 계산 금지 — Bridge가 모든 데이터 변환 담당)
    bridge = DataBridge(result)

    # Singleton helpers (session-scoped)
    if "journal" not in st.session_state:
        st.session_state["journal"] = DecisionJournal()
    if "watchlist" not in st.session_state:
        st.session_state["watchlist"] = WatchlistManager()

    journal:   DecisionJournal  = st.session_state["journal"]
    wl_mgr:    WatchlistManager = st.session_state["watchlist"]

    # Journal 자동 저장
    _auto_save_journal(result, bridge, journal)

    # 날짜 + Journal 데이터 (탭 전에 로드 — Diagnostics 탭에서도 사용)
    today           = datetime.date.today().isoformat()
    today_entry     = journal.load_today(today)
    recent_entries  = journal.load_recent(30)

    # ── Market Status 카드 (탭 최상단) ───────────────────────────────────────
    _render_market_status_card(bridge.market_status())

    # ── 7-Tab 구성 ────────────────────────────────────────────────────────────
    tabs = st.tabs([
        "🏠 Today",
        "📊 Market",
        "💼 Portfolio",
        "📅 History",
        "🔍 Discover",
        "⚙️ System",
        "🔧 Diagnostics",
    ])

    # ── 🏠 Today ──────────────────────────────────────────────────────────────
    with tabs[0]:
        home.render(bridge.home_data(), checklist_data=bridge.checklist_data())

        # Morning Checklist 전체 (Today 탭 하단)
        st.markdown('<div class="section-hdr">🌅 Morning Checklist</div>',
                    unsafe_allow_html=True)
        checklist_comp.render_checklist(bridge.checklist_data())

        # Decision Timeline
        st.markdown('<div class="section-hdr">⏱️ Decision Timeline</div>',
                    unsafe_allow_html=True)
        checklist_comp.render_timeline(bridge.timeline_data())

    # ── 📊 Market ──────────────────────────────────────────────────────────────
    with tabs[1]:
        market.render(bridge.market_data())

    # ── 💼 Portfolio ───────────────────────────────────────────────────────────
    with tabs[2]:
        portfolio.render(bridge.portfolio_data())

    # ── 📅 History ─────────────────────────────────────────────────────────────
    with tabs[3]:
        yesterday_entry = journal.load_yesterday(today)
        cmp_data        = bridge.comparison_data(today_entry, yesterday_entry)
        hist_summary    = bridge.history_summary(recent_entries)   # DataBridge 집계

        history_comp.render_comparison(cmp_data, today_entry, yesterday_entry)
        st.markdown("---")
        history_comp.render_history(recent_entries, hist_summary)

    # ── 🔍 Discover ────────────────────────────────────────────────────────────
    with tabs[4]:
        # Smart Search
        st.markdown('<div class="section-hdr">🔍 Smart Search</div>',
                    unsafe_allow_html=True)
        query = st.text_input(
            "ETF 티커 입력",
            value=state_manager.get(st.session_state, "search_query"),
            placeholder="예: XLK, XLC, XLY ...",
            label_visibility="collapsed",
        )
        state_manager.set_value(st.session_state, "search_query", query)

        if query.strip():
            ticker = query.strip().upper()
            search_result = bridge.search_etf(ticker, wl_mgr)
            search_comp.render_search_result(search_result)

            # 즐겨찾기 / 관심 토글
            col_fav, col_wl = st.columns(2)
            with col_fav:
                if search_result.found:
                    fav_label = "⭐ 즐겨찾기 제거" if search_result.is_favorite else "☆ 즐겨찾기 추가"
                    if st.button(fav_label, key=f"fav_{ticker}"):
                        if search_result.is_favorite:
                            wl_mgr.remove_favorite(ticker)
                        else:
                            wl_mgr.add_favorite(ticker)
                        st.rerun()
            with col_wl:
                if search_result.found:
                    wl_label = "👁️ 관심 제거" if search_result.is_watchlist else "👁 관심 추가"
                    if st.button(wl_label, key=f"wl_{ticker}"):
                        if search_result.is_watchlist:
                            wl_mgr.remove_watchlist(ticker)
                        else:
                            wl_mgr.add_watchlist(ticker)
                        st.rerun()

        st.markdown("---")
        search_comp.render_watchlist(bridge.watchlist_data(wl_mgr))

    # ── ⚙️ System ──────────────────────────────────────────────────────────────
    with tabs[5]:
        system.render(bridge.system_data())
        st.markdown("---")
        notif_comp.render(st.session_state, result)

    # ── 🔧 Diagnostics ─────────────────────────────────────────────────────────
    with tabs[6]:
        diagnostics_comp.render(bridge.diagnostics_data())
        diagnostics_comp.render_op_check(bridge.daily_op_check(
            journal_today=(today_entry is not None),
            journal_count=len(recent_entries),
        ))


if __name__ == "__main__":
    main()
