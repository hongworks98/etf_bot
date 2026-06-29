"""
web/components/system.py
⚙️ System 탭 — Engine Monitor
각 Engine 실행 상태, 소요 시간, 오류 여부를 표시.
UI는 렌더링만 한다. 계산 없음.
"""
from __future__ import annotations
import streamlit as st
from web.utils.data_bridge import SystemViewData, EngineRow
from web.styles.theme import (
    BUY_COLOR, SELL_COLOR, HOLD_COLOR, INFO_COLOR, MUTED_COLOR,
    HEALTH_COLORS,
)


def render(data: SystemViewData) -> None:
    """System 탭 전체 렌더링."""
    _health_banner(data)
    _engine_monitor_table(data)
    _summary_footer(data)


# ── Health Banner ─────────────────────────────────────────────────────────────

def _health_banner(d: SystemViewData) -> None:
    health_color = HEALTH_COLORS.get(d.system_health, MUTED_COLOR)
    status_cls   = {
        "HEALTHY":  "status-healthy",
        "DEGRADED": "status-degraded",
        "CRITICAL": "status-critical",
    }.get(d.system_health, "status-unknown")

    ok_cnt  = d.success_count
    all_cnt = len(d.engines) if d.engines else 0

    st.markdown(f"""
<div class="dss-card" style="display:flex;justify-content:space-between;align-items:center;">
  <div>
    <div class="dss-card-title">System Health</div>
    <div style="margin-top:4px;"><span class="{status_cls}">{d.system_health}</span></div>
  </div>
  <div style="text-align:center;">
    <div class="dss-card-title">Engine</div>
    <div class="dss-card-value" style="font-size:22px;color:{health_color};">{ok_cnt}/{all_cnt}</div>
  </div>
  <div style="text-align:right;">
    <div class="dss-card-title">Total Time</div>
    <div class="dss-card-value" style="font-size:22px;">{d.total_sec:.2f}s</div>
  </div>
</div>
""", unsafe_allow_html=True)

    if d.failed_engines:
        failed_str = ", ".join(d.failed_engines)
        st.markdown(f"""
<div style="background:#fee2e2;border-radius:8px;padding:10px 14px;margin-bottom:10px;
            font-size:13px;color:#b91c1c;">
  ❌ 실패 Engine: {failed_str}
</div>
""", unsafe_allow_html=True)


# ── Engine Monitor Table ──────────────────────────────────────────────────────

def _engine_monitor_table(d: SystemViewData) -> None:
    st.markdown('<div class="section-hdr">🔍 Engine 실행 현황</div>', unsafe_allow_html=True)

    if not d.available or not d.engines:
        st.markdown("""
<div class="dss-card" style="text-align:center;padding:24px;">
  <div class="dss-card-sub">Engine Monitor 데이터가 없습니다.</div>
</div>
""", unsafe_allow_html=True)
        return

    rows_html = ""
    for eng in d.engines:
        rows_html += _engine_row_html(eng)

    st.markdown(f'<div class="dss-card" style="padding:4px 0;">{rows_html}</div>',
                unsafe_allow_html=True)


def _engine_row_html(eng: EngineRow) -> str:
    status = eng.status
    if status == "SUCCESS":
        icon     = "🟢"
        stat_cls = "engine-status-ok"
        stat_txt = "OK"
    elif status == "FAILED":
        icon     = "🔴"
        stat_cls = "engine-status-fail"
        stat_txt = "FAIL"
    else:  # SKIPPED
        icon     = "⚪"
        stat_cls = "engine-status-fail"
        stat_txt = "SKIP"

    crit_badge = ""
    if not eng.is_critical:
        crit_badge = f'<span style="font-size:10px;color:{MUTED_COLOR};margin-left:4px;">[선택]</span>'

    error_html = ""
    if eng.error_message:
        err_short = eng.error_message[:60] + ("..." if len(eng.error_message) > 60 else "")
        error_html = f'<div class="engine-error">└ {err_short}</div>'

    return f"""
<div class="engine-row">
  <div class="engine-icon">{icon}</div>
  <div class="engine-name">{eng.name}{crit_badge}</div>
  <div class="engine-time">{eng.elapsed_sec:.2f}s</div>
  <div class="{stat_cls}">{stat_txt}</div>
</div>{error_html}"""


# ── Summary Footer ────────────────────────────────────────────────────────────

def _summary_footer(d: SystemViewData) -> None:
    if not d.run_id and not d.run_date:
        return
    st.markdown(f"""
<div class="dss-card" style="margin-top:10px;">
  <div class="dss-card-title">실행 정보</div>
  <div style="display:flex;justify-content:space-between;margin-top:6px;font-size:13px;">
    <span style="color:{MUTED_COLOR};">Run ID</span>
    <span style="font-family:monospace;font-size:12px;">{d.run_id or "N/A"}</span>
  </div>
  <div style="display:flex;justify-content:space-between;margin-top:4px;font-size:13px;">
    <span style="color:{MUTED_COLOR};">실행 시각</span>
    <span>{d.run_date or "N/A"}</span>
  </div>
  <div style="display:flex;justify-content:space-between;margin-top:4px;font-size:13px;">
    <span style="color:{MUTED_COLOR};">총 실행 시간</span>
    <span style="font-weight:700;">{d.total_sec:.3f}초</span>
  </div>
</div>
""", unsafe_allow_html=True)

    # Timing breakdown bar chart (optional)
    if d.engines and any(e.elapsed_sec > 0 for e in d.engines):
        _timing_bars(d)


def _timing_bars(d: SystemViewData) -> None:
    # timing_pct는 DataBridge.system_data()에서 계산 완료.
    # UI는 eng.timing_pct를 렌더링만 한다. 계산 없음.
    st.markdown('<div class="section-hdr">⏱️ Engine별 소요 시간</div>', unsafe_allow_html=True)

    rows_html = ""
    for eng in d.engines:
        color      = SELL_COLOR if eng.status == "FAILED" else (BUY_COLOR if eng.elapsed_sec < 0.5 else HOLD_COLOR)
        name_short = eng.name.replace(" Engine", "").replace("Portfolio ", "Port.")
        rows_html += f"""
<div style="display:flex;align-items:center;gap:8px;padding:5px 0;font-size:12px;">
  <div style="width:80px;flex-shrink:0;color:{MUTED_COLOR};">{name_short}</div>
  <div style="flex:1;background:#e2e8f0;border-radius:99px;height:7px;overflow:hidden;">
    <div style="width:{eng.timing_pct:.1f}%;background:{color};height:100%;border-radius:99px;"></div>
  </div>
  <div style="width:42px;text-align:right;font-weight:600;color:{color};">{eng.elapsed_sec:.3f}s</div>
</div>"""

    st.markdown(f'<div class="dss-card" style="padding:10px 14px;">{rows_html}</div>',
                unsafe_allow_html=True)
