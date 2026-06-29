"""
web/components/market.py
📊 Market 탭 — Macro · Breadth · RS · Rotation
각 Engine 결과를 카드 형태로 표시.
UI는 렌더링만 한다. 계산 없음.
"""
from __future__ import annotations
import streamlit as st
from web.utils.data_bridge import MarketViewData, MarketCardData
from web.styles.theme import (
    progress_bar, score_color,
    BUY_COLOR, SELL_COLOR, INFO_COLOR, HOLD_COLOR, MUTED_COLOR, BORDER_COLOR,
)


def render(data: MarketViewData) -> None:
    """Market 탭 전체 렌더링."""
    _market_health_banner(data)
    _engine_cards(data)
    _rs_sector_table(data)
    _rotation_card(data)


# ── Market Health Banner ──────────────────────────────────────────────────────

def _market_health_banner(d: MarketViewData) -> None:
    health_color = score_color(d.market_health_score)
    bar = progress_bar(d.market_health_score, 100, health_color)
    st.markdown(f"""
<div class="dss-card">
  <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;">
    <div class="dss-card-title">📊 Market Health</div>
    <div style="font-size:13px;font-weight:700;color:{health_color};">{d.market_health_label}</div>
  </div>
  <div style="display:flex;align-items:baseline;gap:6px;margin-bottom:6px;">
    <div class="dss-card-value" style="color:{health_color};">{d.market_health_score:.1f}</div>
    <div class="dss-card-sub">/100</div>
  </div>
  {bar}
</div>
""", unsafe_allow_html=True)


# ── Engine Cards (Macro + Breadth) ────────────────────────────────────────────

def _engine_cards(d: MarketViewData) -> None:
    st.markdown('<div class="section-hdr">Engine 지표</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        _score_card(d.macro)
    with col2:
        _score_card(d.breadth)


def _score_card(card: MarketCardData) -> None:
    color = score_color(card.score)
    bar = progress_bar(card.score, 100, color)
    trend_icon = "↑" if "UP" in card.trend else ("↓" if "DOWN" in card.trend else "→")
    st.markdown(f"""
<div class="dss-card">
  <div class="dss-card-title">{card.label}</div>
  <div class="dss-card-value" style="color:{color};">{card.score:.0f}</div>
  <div class="dss-card-sub">{card.status} &nbsp; {trend_icon}</div>
  {bar}
</div>
""", unsafe_allow_html=True)


# ── RS Sector Table ───────────────────────────────────────────────────────────

def _rs_sector_table(d: MarketViewData) -> None:
    if not d.rs_cards:
        return
    st.markdown('<div class="section-hdr">📈 Relative Strength (섹터별)</div>', unsafe_allow_html=True)

    # Top 3 highlighted
    if d.top_rs_sectors:
        top_str = " &nbsp;·&nbsp; ".join(
            f'<span style="font-weight:700;color:{BUY_COLOR};">{t}</span>'
            for t in d.top_rs_sectors
        )
        st.markdown(f"""
<div class="dss-card" style="padding:10px 14px;margin-bottom:8px;">
  <div class="dss-card-title">상위 RS 섹터</div>
  <div style="font-size:15px;margin-top:4px;">{top_str}</div>
</div>
""", unsafe_allow_html=True)

    # Full table
    rows_html = ""
    for item in d.rs_cards:
        score = item["score"]
        color = score_color(score)
        bar   = progress_bar(score, 100, color)
        medal = "🥇" if item["rank"] == 1 else ("🥈" if item["rank"] == 2 else ("🥉" if item["rank"] == 3 else f'{item["rank"]}위'))
        rows_html += f"""
<div class="alloc-row">
  <div style="width:28px;font-size:13px;">{medal}</div>
  <div class="alloc-ticker">{item["ticker"]}</div>
  <div class="alloc-bar-wrap">{bar}</div>
  <div class="alloc-pct" style="color:{color};font-weight:700;">{score:.0f}</div>
</div>"""

    st.markdown(f'<div class="dss-card" style="padding:10px 14px;">{rows_html}</div>',
                unsafe_allow_html=True)


# ── Rotation Card ─────────────────────────────────────────────────────────────

def _rotation_card(d: MarketViewData) -> None:
    st.markdown('<div class="section-hdr">🔄 Sector Rotation</div>', unsafe_allow_html=True)

    active_badge = (
        f'<span class="badge badge-buy">활성</span>'
        if d.rotation_active
        else f'<span class="badge badge-muted">정체</span>'
    )
    forecast_color = score_color(d.rotation_forecast)
    forecast_bar = progress_bar(d.rotation_forecast, 100, forecast_color)

    st.markdown(f"""
<div class="dss-card">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
    <div>
      <div class="dss-card-title">주도 섹터</div>
      <div class="dss-card-value" style="font-size:22px;color:{INFO_COLOR};">{d.rotation_dominant}</div>
    </div>
    <div style="text-align:right;">
      <div class="dss-card-title">순환 상태</div>
      <div style="margin-top:4px;">{active_badge}</div>
    </div>
  </div>
  <div class="dss-card-title" style="margin-bottom:4px;">
    순환 강도 &nbsp; <span style="color:{forecast_color};font-weight:700;">{d.rotation_forecast:.0f}/100</span>
  </div>
  {forecast_bar}
</div>
""", unsafe_allow_html=True)
