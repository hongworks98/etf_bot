"""
web/components/home.py
Today 탭 — Today's Decision + Morning Checklist + AI Explain More
UI renders only — no calculations.
"""
from __future__ import annotations
from typing import Optional
import streamlit as st
from web.utils.data_bridge import HomeViewData, ChecklistViewData
from web.styles.theme import (
    action_class, badge_class, hero_class,
    progress_bar, score_color,
    BUY_COLOR, SELL_COLOR, HOLD_COLOR, INFO_COLOR, MUTED_COLOR,
    ACTION_COLORS,
)


def render(data: HomeViewData,
           checklist_data: Optional[ChecklistViewData] = None) -> None:
    """Home 탭 전체 렌더링."""
    _hero_card(data)
    if checklist_data is not None:
        _checklist_mini(checklist_data)
    _market_status_row(data)
    _today_brief(data)
    _action_items(data)
    _xai_section(data)
    _explain_more(data)
    _footer(data)


# ── Hero Card ─────────────────────────────────────────────────────────────────

def _hero_card(d: HomeViewData) -> None:
    color = ACTION_COLORS.get(d.action, HOLD_COLOR)
    conf_bar = progress_bar(d.confidence, 100, color)
    risk_badge_cls = (
        "badge-sell" if d.risk_level == "높음"
        else ("badge-hold" if d.risk_level == "보통" else "badge-buy")
    )
    st.markdown(f"""
<div class="{hero_class(d.action)}">
  <div class="hero-confidence">신뢰도 {d.confidence:.1f}% — {d.confidence_level}</div>
  {conf_bar}
  <div style="margin:12px 0 4px">
    <div class="hero-action" style="color:{color}">{d.action}</div>
  </div>
  <div>
    <span class="badge {risk_badge_cls}">리스크 {d.risk_level}</span>
    &nbsp;
    <span class="badge badge-muted">{d.market_status}</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Market Status Row ─────────────────────────────────────────────────────────

def _market_status_row(d: HomeViewData) -> None:
    macro_color = score_color(d.macro_score)
    st.markdown(f"""
<div class="dss-card" style="display:flex;justify-content:space-between;align-items:center;">
  <div>
    <div class="dss-card-title">거시경제 점수</div>
    <div class="dss-card-value" style="color:{macro_color};font-size:22px;">{d.macro_score:.0f}<span style="font-size:14px;color:{MUTED_COLOR}">/100</span></div>
  </div>
  <div style="text-align:center;">
    <div class="dss-card-title">시장 국면</div>
    <div class="dss-card-value" style="font-size:18px;">{d.market_status}</div>
  </div>
  <div style="text-align:right;">
    <div class="dss-card-title">기회 ETF</div>
    <div class="dss-card-value" style="font-size:18px;color:{INFO_COLOR};">
      {", ".join(d.top_etfs) if d.top_etfs else "—"}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Today's Brief ─────────────────────────────────────────────────────────────

def _today_brief(d: HomeViewData) -> None:
    st.markdown('<div class="section-hdr">📋 Today\'s Brief</div>', unsafe_allow_html=True)
    lines_html = "".join(
        f'<div class="brief-line">{line}</div>'
        for line in d.brief_lines
    )
    st.markdown(f'<div class="brief-box">{lines_html}</div>', unsafe_allow_html=True)


# ── Action Items ──────────────────────────────────────────────────────────────

def _action_items(d: HomeViewData) -> None:
    st.markdown('<div class="section-hdr">⚡ Today\'s Action</div>', unsafe_allow_html=True)

    if not d.allocation_changes:
        st.markdown("""
<div class="dss-card">
  <div class="dss-card-sub" style="text-align:center;padding:8px 0;">
    배분 변경 없음 — 현 포지션 유지
  </div>
</div>
""", unsafe_allow_html=True)
        return

    for i, item in enumerate(d.allocation_changes, 1):
        delta   = item["delta_pct"]
        ticker  = item["ticker"]
        sign    = "+" if delta > 0 else ""
        color   = BUY_COLOR if delta > 0 else SELL_COLOR
        top_mark = " ⭐" if item.get("is_top") else ""
        st.markdown(f"""
<div class="dss-card" style="display:flex;align-items:center;gap:12px;padding:12px 14px;">
  <div style="width:24px;height:24px;border-radius:50%;background:{color};
              color:white;display:flex;align-items:center;justify-content:center;
              font-size:12px;font-weight:700;flex-shrink:0;">{i}</div>
  <div style="flex:1;">
    <div style="font-weight:700;font-size:15px;color:#1e293b;">{ticker}{top_mark}</div>
  </div>
  <div style="font-size:18px;font-weight:800;color:{color};">{sign}{delta:.1f}%</div>
</div>
""", unsafe_allow_html=True)


# ── Checklist Mini Banner ─────────────────────────────────────────────────────

def _checklist_mini(d: ChecklistViewData) -> None:
    """Morning Checklist 간략 상태 배너."""
    pct   = d.completion_pct
    color = BUY_COLOR if d.all_complete else (INFO_COLOR if pct >= 50 else MUTED_COLOR)
    bar   = progress_bar(pct, 100, color)
    label = "✅ 모든 엔진 완료" if d.all_complete else f"⏳ {pct:.0f}% 완료 ({d.last_update or 'N/A'})"

    st.markdown(f"""
<div class="dss-card" style="padding:10px 14px;margin-bottom:4px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
    <div style="font-size:12px;font-weight:600;color:#1e293b;">🌅 Morning Checklist</div>
    <div style="font-size:12px;color:{color};font-weight:700;">{label}</div>
  </div>
  {bar}
</div>
""", unsafe_allow_html=True)


# ── XAI Section ───────────────────────────────────────────────────────────────

def _xai_section(d: HomeViewData) -> None:
    st.markdown('<div class="section-hdr">🧠 Why (AI 설명)</div>', unsafe_allow_html=True)

    xai_items = [
        ("Why", d.why_decision),
        ("Why Now", d.why_now),
        ("Why This ETF", d.why_etf),
        ("Why This Allocation", d.why_allocation),
    ]
    for label, text in xai_items:
        st.markdown(f"""
<div class="why-box">
  <div class="why-label">{label}</div>
  {text}
</div>
""", unsafe_allow_html=True)


# ── AI Explain More ───────────────────────────────────────────────────────────

def _explain_more(d: HomeViewData) -> None:
    """AI 상세 분석 — 확장 가능한 섹션."""
    with st.expander("🔍 AI 상세 분석 보기"):
        macro_color = score_color(d.macro_score)

        st.markdown(f"""
<div class="dss-card" style="margin-bottom:8px;">
  <div class="dss-card-title">📈 거시경제 분석</div>
  <div style="display:flex;align-items:baseline;gap:8px;margin:6px 0;">
    <div style="font-size:28px;font-weight:800;color:{macro_color};">{d.macro_score:.0f}</div>
    <div class="dss-card-sub">/100 — {d.market_status}</div>
  </div>
  <div style="font-size:13px;color:#374151;line-height:1.6;">
    거시경제 점수는 GDP 성장률, 금리 환경, 물가 지수, 고용 지표를 종합하여 산출합니다.
    현재 <strong>{d.market_status}</strong> 국면은 위험자산 선호도에 직접적인 영향을 미칩니다.
  </div>
</div>

<div class="dss-card" style="margin-bottom:8px;">
  <div class="dss-card-title">🎯 추천 근거 요약</div>
  <div style="font-size:13px;color:#374151;line-height:1.7;margin-top:6px;">
    {d.why_decision}
  </div>
</div>

<div class="dss-card" style="margin-bottom:8px;">
  <div class="dss-card-title">⏰ 타이밍 근거</div>
  <div style="font-size:13px;color:#374151;line-height:1.7;margin-top:6px;">
    {d.why_now}
  </div>
</div>

<div class="dss-card" style="margin-bottom:8px;">
  <div class="dss-card-title">🏆 ETF 선택 이유</div>
  <div style="margin-top:6px;">
    {"".join(f'<span style="display:inline-block;background:#eff6ff;color:#1d4ed8;font-weight:700;padding:2px 10px;border-radius:20px;font-size:12px;margin:2px;">{etf}</span>' for etf in d.top_etfs) if d.top_etfs else '<span style="color:#64748b;font-size:13px;">—</span>'}
  </div>
  <div style="font-size:13px;color:#374151;line-height:1.7;margin-top:6px;">
    {d.why_etf}
  </div>
</div>

<div class="dss-card">
  <div class="dss-card-title">⚖️ 배분 전략 이유</div>
  <div style="font-size:13px;color:#374151;line-height:1.7;margin-top:6px;">
    {d.why_allocation}
  </div>
</div>
""", unsafe_allow_html=True)


# ── Footer ────────────────────────────────────────────────────────────────────

def _footer(d: HomeViewData) -> None:
    st.markdown(f"""
<div style="text-align:center;padding:12px 0 4px;font-size:11px;color:{MUTED_COLOR};">
  Last Update: {d.run_date or "N/A"} &nbsp;|&nbsp; Run ID: {d.run_id or "N/A"}
</div>
""", unsafe_allow_html=True)
