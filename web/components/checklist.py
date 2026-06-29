"""
web/components/checklist.py
Morning Checklist + Decision Timeline
UI renders only — no calculations.
"""
from __future__ import annotations
import streamlit as st
from web.utils.data_bridge import ChecklistViewData, TimelineViewData
from web.styles.theme import (
    progress_bar, BUY_COLOR, SELL_COLOR, INFO_COLOR,
    HOLD_COLOR, MUTED_COLOR, BORDER_COLOR,
)


def render_checklist(data: ChecklistViewData) -> None:
    _checklist_header(data)
    _checklist_items(data)


def render_timeline(data: TimelineViewData) -> None:
    _timeline_header(data)
    _timeline_events(data)


# ── Checklist Header ──────────────────────────────────────────────────────────

def _checklist_header(d: ChecklistViewData) -> None:
    pct   = d.completion_pct
    color = BUY_COLOR if d.all_complete else (INFO_COLOR if pct >= 50 else HOLD_COLOR)
    bar   = progress_bar(pct, 100, color)
    status_text = "완료" if d.all_complete else f"{pct:.0f}% 완료"

    st.markdown(f"""
<div class="dss-card">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
    <div class="dss-card-title">Morning Checklist</div>
    <div style="font-size:13px;font-weight:700;color:{color};">{status_text}</div>
  </div>
  {bar}
  <div style="font-size:11px;color:{MUTED_COLOR};margin-top:6px;">
    마지막 업데이트: {d.last_update or 'N/A'}
  </div>
</div>
""", unsafe_allow_html=True)


def _checklist_items(d: ChecklistViewData) -> None:
    rows_html = ""
    for item in d.items:
        if item.status == "SUCCESS":
            icon  = "✅"
            color = BUY_COLOR
        elif item.status == "FAILED":
            icon  = "❌"
            color = SELL_COLOR
        elif item.status == "SKIPPED":
            icon  = "⏭️"
            color = MUTED_COLOR
        else:
            icon  = "⏳"
            color = MUTED_COLOR

        rows_html += f"""
<div style="display:flex;align-items:center;gap:10px;padding:9px 0;
            border-bottom:1px solid {BORDER_COLOR};">
  <div style="font-size:16px;flex-shrink:0;">{icon}</div>
  <div style="flex:1;">
    <div style="font-weight:600;font-size:13px;color:#1e293b;">{item.label}</div>
    <div style="font-size:11px;color:{MUTED_COLOR};">{item.engine}</div>
  </div>
  <div style="font-size:12px;color:{color};text-align:right;max-width:160px;">{item.note}</div>
</div>"""

    st.markdown(f'<div class="dss-card" style="padding:4px 14px;">{rows_html}</div>',
                unsafe_allow_html=True)


# ── Timeline Header ───────────────────────────────────────────────────────────

def _timeline_header(d: TimelineViewData) -> None:
    st.markdown(f"""
<div class="dss-card" style="display:flex;justify-content:space-between;align-items:center;">
  <div>
    <div class="dss-card-title">Decision Timeline</div>
    <div class="dss-card-sub">{d.run_date or 'N/A'}</div>
  </div>
  <div style="text-align:right;">
    <div class="dss-card-title">총 실행 시간</div>
    <div class="dss-card-value" style="font-size:20px;">{d.total_sec:.2f}s</div>
  </div>
</div>
""", unsafe_allow_html=True)


def _timeline_events(d: TimelineViewData) -> None:
    if not d.events:
        st.markdown("""
<div class="dss-card" style="text-align:center;padding:20px;">
  <div class="dss-card-sub">Timeline 데이터가 없습니다 (Engine Monitor 미실행)</div>
</div>
""", unsafe_allow_html=True)
        return

    events_html = ""
    for ev in d.events:
        if ev.status == "SUCCESS":
            dot_color = BUY_COLOR
            icon = "●"
        elif ev.status == "FAILED":
            dot_color = SELL_COLOR
            icon = "●"
        else:
            dot_color = MUTED_COLOR
            icon = "○"

        is_last = ev.seq == len(d.events)
        line_html = (
            "" if is_last
            else f'<div style="width:2px;height:100%;background:{BORDER_COLOR};'
                 f'margin:0 auto;min-height:24px;"></div>'
        )

        events_html += f"""
<div style="display:flex;gap:12px;align-items:flex-start;">
  <div style="display:flex;flex-direction:column;align-items:center;width:20px;flex-shrink:0;">
    <div style="color:{dot_color};font-size:16px;line-height:1;">{icon}</div>
    {line_html}
  </div>
  <div style="flex:1;padding-bottom:16px;">
    <div style="display:flex;justify-content:space-between;align-items:baseline;">
      <div style="font-weight:600;font-size:13px;color:#1e293b;">{ev.engine}</div>
      <div style="font-size:12px;color:{MUTED_COLOR};">{ev.elapsed_sec:.3f}s</div>
    </div>
    <div style="font-size:12px;color:{MUTED_COLOR};margin-top:2px;
                font-family:monospace;">{ev.output_summary}</div>
  </div>
</div>"""

    st.markdown(f'<div class="dss-card" style="padding:14px;">{events_html}</div>',
                unsafe_allow_html=True)
