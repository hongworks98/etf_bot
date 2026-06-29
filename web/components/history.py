"""
web/components/history.py
Decision History + Recommendation Comparison + Journal Viewer
UI renders only — no calculations.
"""
from __future__ import annotations
import streamlit as st
from typing import List, Optional
from web.utils.data_bridge import ComparisonData, HistorySummaryViewData
from web.utils.journal import JournalEntry
from web.styles.theme import (
    ACTION_COLORS, GRADE_COLORS,
    BUY_COLOR, SELL_COLOR, HOLD_COLOR, INFO_COLOR, MUTED_COLOR,
    BORDER_COLOR, badge_class, progress_bar,
)


def render_comparison(data: ComparisonData,
                      today: Optional[JournalEntry],
                      yesterday: Optional[JournalEntry]) -> None:
    _comparison_card(data, today, yesterday)


def render_history(entries: List[JournalEntry],
                   summary: Optional[HistorySummaryViewData] = None) -> None:
    if summary is not None and entries:
        _history_header(summary)
    _history_timeline(entries)


# ── Comparison Card ───────────────────────────────────────────────────────────

def _comparison_card(cmp: ComparisonData,
                     today: Optional[JournalEntry],
                     yesterday: Optional[JournalEntry]) -> None:
    st.markdown('<div class="section-hdr">📊 어제 vs 오늘</div>', unsafe_allow_html=True)

    if today is None:
        st.markdown("""
<div class="dss-card" style="text-align:center;padding:20px;">
  <div class="dss-card-sub">오늘 데이터가 없습니다.</div>
</div>
""", unsafe_allow_html=True)
        return

    y_action = (yesterday.action if yesterday else "—")
    t_action = today.action
    y_conf   = f"{yesterday.confidence:.0f}%" if yesterday else "—"
    t_conf   = f"{today.confidence:.0f}%"
    y_etfs   = ", ".join(yesterday.top_etfs) if yesterday and yesterday.top_etfs else "—"
    t_etfs   = ", ".join(today.top_etfs)     if today.top_etfs else "—"

    y_color = ACTION_COLORS.get(y_action, MUTED_COLOR)
    t_color = ACTION_COLORS.get(t_action, MUTED_COLOR)
    delta_color = (BUY_COLOR if cmp.confidence_delta > 0
                   else (SELL_COLOR if cmp.confidence_delta < 0 else MUTED_COLOR))
    delta_str = (f"+{cmp.confidence_delta:.1f}%" if cmp.confidence_delta > 0
                 else f"{cmp.confidence_delta:.1f}%") if yesterday else "—"

    change_icon = "🔄" if cmp.action_changed else "📌"

    st.markdown(f"""
<div class="dss-card">
  <div style="display:grid;grid-template-columns:1fr 40px 1fr;gap:8px;
              align-items:center;text-align:center;margin-bottom:12px;">
    <div>
      <div class="dss-card-title">어제</div>
      <div style="font-size:22px;font-weight:800;color:{y_color};">{y_action}</div>
      <div class="dss-card-sub">{y_conf} | {y_etfs}</div>
    </div>
    <div style="font-size:20px;">{change_icon}</div>
    <div>
      <div class="dss-card-title">오늘</div>
      <div style="font-size:22px;font-weight:800;color:{t_color};">{t_action}</div>
      <div class="dss-card-sub">{t_conf} | {t_etfs}</div>
    </div>
  </div>
  <div style="background:#f0f9ff;border-left:3px solid {INFO_COLOR};
              border-radius:0 8px 8px 0;padding:8px 12px;font-size:13px;">
    <span style="color:{INFO_COLOR};font-weight:700;">변경 이유</span>&nbsp;
    {cmp.change_reason}
  </div>
  {"" if not cmp.confidence_delta or not yesterday else f'''
  <div style="display:flex;justify-content:space-between;
              margin-top:10px;font-size:13px;">
    <span style="color:{MUTED_COLOR};">신뢰도 변화</span>
    <span style="font-weight:700;color:{delta_color};">{delta_str}</span>
  </div>'''}
</div>
""", unsafe_allow_html=True)


# ── History Header ────────────────────────────────────────────────────────────
# 모든 집계(avg_conf, counts)는 DataBridge.history_summary()에서 계산.
# UI는 HistorySummaryViewData를 렌더링만 한다.

def _history_header(summary: HistorySummaryViewData) -> None:
    st.markdown(f"""
<div class="metric-grid" style="margin-bottom:10px;">
  <div class="metric-cell">
    <div class="metric-label">{summary.label} 평균 신뢰도</div>
    <div class="metric-value" style="color:{summary.avg_conf_color};">{summary.avg_confidence:.0f}%</div>
  </div>
  <div class="metric-cell">
    <div class="metric-label">액션 분포</div>
    <div style="font-size:13px;margin-top:4px;">
      <span style="color:{BUY_COLOR};font-weight:700;">BUY {summary.buy_count}</span>
      &nbsp;
      <span style="color:{SELL_COLOR};font-weight:700;">SELL {summary.sell_count}</span>
      &nbsp;
      <span style="color:{HOLD_COLOR};font-weight:700;">HOLD {summary.hold_count}</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


def _history_timeline(entries: List[JournalEntry]) -> None:
    st.markdown('<div class="section-hdr">📅 추천 기록</div>', unsafe_allow_html=True)

    if not entries:
        st.markdown("""
<div class="dss-card" style="text-align:center;padding:20px;">
  <div class="dss-card-sub">기록이 없습니다. 내일 다시 확인해 주세요.</div>
</div>
""", unsafe_allow_html=True)
        return

    rows_html = ""
    for entry in entries:
        color   = ACTION_COLORS.get(entry.action, MUTED_COLOR)
        etf_str = ", ".join(entry.top_etfs) if entry.top_etfs else "—"
        conf_bar = progress_bar(entry.confidence, 100, color)

        # hit 여부 표시 (향후 Validation 연결)
        if entry.hit is True:
            hit_icon = '<span style="color:#22c55e;font-size:11px;">✅ 적중</span>'
        elif entry.hit is False:
            hit_icon = '<span style="color:#ef4444;font-size:11px;">❌ 미적중</span>'
        else:
            hit_icon = '<span style="color:#64748b;font-size:11px;">⏳ 미확인</span>'

        rows_html += f"""
<div style="border:1px solid {BORDER_COLOR};border-radius:10px;
            padding:12px 14px;margin-bottom:8px;">
  <div style="display:flex;justify-content:space-between;align-items:center;
              margin-bottom:6px;">
    <div style="font-size:12px;color:{MUTED_COLOR};">{entry.date}</div>
    {hit_icon}
  </div>
  <div style="display:flex;align-items:baseline;gap:10px;margin-bottom:4px;">
    <div style="font-size:20px;font-weight:800;color:{color};">{entry.action}</div>
    <div style="font-size:13px;color:{MUTED_COLOR};">{entry.market_status}</div>
    <div style="font-size:13px;color:{MUTED_COLOR};margin-left:auto;">{entry.confidence:.0f}%</div>
  </div>
  {conf_bar}
  <div style="font-size:12px;color:{MUTED_COLOR};margin-top:4px;">ETF: {etf_str}</div>
</div>"""

    st.markdown(f'<div>{rows_html}</div>', unsafe_allow_html=True)
