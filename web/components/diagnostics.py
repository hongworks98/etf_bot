"""
web/components/diagnostics.py
🔧 Diagnostics 탭 — 시스템 진단 정보
UI renders only — no calculations.
모든 데이터는 DataBridge.diagnostics_data()에서 온다.
"""
from __future__ import annotations
import streamlit as st
from web.utils.data_bridge import DiagnosticsViewData, DailyOpCheckViewData
from web.styles.theme import (
    BUY_COLOR, SELL_COLOR, HOLD_COLOR, INFO_COLOR, MUTED_COLOR, BORDER_COLOR,
)


def render(data: DiagnosticsViewData) -> None:
    """Diagnostics 탭 전체 렌더링."""
    _system_info(data)
    _config_status(data)
    _pipeline_status(data)


# ── System Info ───────────────────────────────────────────────────────────────

def _system_info(d: DiagnosticsViewData) -> None:
    st.markdown('<div class="section-hdr">🖥️ 시스템 정보</div>', unsafe_allow_html=True)
    st.markdown(f"""
<div class="metric-grid">
  <div class="metric-cell">
    <div class="metric-label">Python 버전</div>
    <div style="font-size:14px;font-weight:700;font-family:monospace;">{d.python_version}</div>
  </div>
  <div class="metric-cell">
    <div class="metric-label">DSS 버전</div>
    <div style="font-size:14px;font-weight:700;">{d.dss_version}</div>
  </div>
  <div class="metric-cell">
    <div class="metric-label">메모리 사용</div>
    <div style="font-size:18px;font-weight:700;">{d.memory_mb:.1f} <span style="font-size:12px;color:{MUTED_COLOR};">MB</span></div>
  </div>
  <div class="metric-cell">
    <div class="metric-label">CPU 사용률</div>
    <div style="font-size:18px;font-weight:700;">{d.cpu_pct:.1f}<span style="font-size:12px;color:{MUTED_COLOR};">%</span></div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Config Status ─────────────────────────────────────────────────────────────

def _config_status(d: DiagnosticsViewData) -> None:
    st.markdown('<div class="section-hdr">⚙️ 설정 파일 상태</div>', unsafe_allow_html=True)

    def _row(label: str, loaded: bool) -> str:
        icon  = "✅" if loaded else "⚠️"
        state = "로드됨" if loaded else "기본값 사용"
        color = BUY_COLOR if loaded else HOLD_COLOR
        return (f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:8px 0;font-size:13px;border-bottom:1px solid {BORDER_COLOR};">'
                f'<span style="color:{MUTED_COLOR};font-family:monospace;">{label}</span>'
                f'<span style="font-weight:600;color:{color};">{icon} {state}</span></div>')

    theme_row = _row("config/theme.yaml",      d.theme_config_loaded)
    app_row   = _row("config/app_config.yaml", d.app_config_loaded)

    st.markdown(f"""
<div class="dss-card" style="padding:4px 16px;">
  {theme_row}
  <div style="display:flex;justify-content:space-between;align-items:center;
              padding:8px 0;font-size:13px;">
    <span style="color:{MUTED_COLOR};font-family:monospace;">config/app_config.yaml</span>
    <span style="font-weight:600;color:{"#22c55e" if d.app_config_loaded else "#f97316"};">
      {"✅ 로드됨" if d.app_config_loaded else "⚠️ 기본값 사용"}
    </span>
  </div>
  <div style="display:flex;justify-content:space-between;align-items:center;
              padding:8px 0;font-size:13px;">
    <span style="color:{MUTED_COLOR};">Cache TTL</span>
    <span style="font-weight:600;">{d.cache_ttl_sec}초</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Pipeline Status ───────────────────────────────────────────────────────────

def _pipeline_status(d: DiagnosticsViewData) -> None:
    st.markdown('<div class="section-hdr">🔗 Pipeline 상태</div>', unsafe_allow_html=True)

    if d.all_success:
        status_color = BUY_COLOR
        status_text  = "✅ 정상"
    elif d.failed_engines:
        status_color = SELL_COLOR
        status_text  = "❌ 오류"
    else:
        status_color = INFO_COLOR
        status_text  = "ℹ️ 데모 모드"

    failed_html = ""
    if d.failed_engines:
        failed_list = ", ".join(d.failed_engines)
        failed_html = (f'<div style="font-size:12px;color:{SELL_COLOR};'
                       f'margin-top:6px;padding-top:6px;border-top:1px solid {BORDER_COLOR};">'
                       f'실패 Engine: {failed_list}</div>')

    st.markdown(f"""
<div class="dss-card">
  <div style="display:flex;justify-content:space-between;padding:5px 0;font-size:13px;">
    <span style="color:{MUTED_COLOR};">Pipeline</span>
    <span style="font-weight:700;color:{status_color};">{status_text}</span>
  </div>
  <div style="display:flex;justify-content:space-between;padding:5px 0;font-size:13px;
              border-top:1px solid {BORDER_COLOR};">
    <span style="color:{MUTED_COLOR};">Engine 성공률</span>
    <span style="font-weight:600;">{d.success_count}/{d.engine_count}</span>
  </div>
  <div style="display:flex;justify-content:space-between;padding:5px 0;font-size:13px;
              border-top:1px solid {BORDER_COLOR};">
    <span style="color:{MUTED_COLOR};">마지막 실행</span>
    <span>{d.last_update or "N/A"}</span>
  </div>
  <div style="display:flex;justify-content:space-between;padding:5px 0;font-size:13px;
              border-top:1px solid {BORDER_COLOR};">
    <span style="color:{MUTED_COLOR};">Run ID</span>
    <span style="font-family:monospace;font-size:12px;">{d.run_id or "N/A"}</span>
  </div>
  {failed_html}
</div>
""", unsafe_allow_html=True)


# ── Daily Operation Checklist ─────────────────────────────────────────────────

def render_op_check(data: DailyOpCheckViewData) -> None:
    """운영 체크리스트 — Diagnostics 탭 하단에 렌더링."""
    st.markdown('<div class="section-hdr">☑️ Daily Operation Checklist</div>',
                unsafe_allow_html=True)

    # 요약 헤더
    if data.all_ok:
        summary_color = BUY_COLOR
        summary_text  = f"✅ 모든 항목 정상 ({data.ok_count}/{data.total})"
    else:
        summary_color = HOLD_COLOR
        summary_text  = f"⚠️ {data.ok_count}/{data.total}개 정상 — {data.total - data.ok_count}개 확인 필요"

    # 체크리스트 행 HTML 생성
    rows_html = ""
    for item in data.items:
        ok_color = BUY_COLOR if item.ok else HOLD_COLOR
        rows_html += f"""
<div class="op-check-row">
  <div>
    <div class="op-check-label">{item.icon}&nbsp;{item.label}</div>
    <div class="op-check-detail">{item.detail}</div>
  </div>
  <div style="font-size:18px;">{item.icon}</div>
</div>"""

    st.markdown(f"""
<div style="margin-bottom:8px;padding:8px 14px;border-radius:8px;
            background:{"#f0fdf4" if data.all_ok else "#fffbeb"};
            font-size:13px;font-weight:700;color:{summary_color};">
  {summary_text}
</div>
<div class="dss-card" style="padding:4px 16px;">
  {rows_html}
</div>
<div style="font-size:11px;color:{MUTED_COLOR};margin-top:4px;text-align:right;">
  마지막 확인: {data.last_check}
</div>
""", un