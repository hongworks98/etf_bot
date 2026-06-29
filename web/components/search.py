"""
web/components/search.py
Smart Search + Favorites + Watchlist
UI renders only — no calculations.
"""
from __future__ import annotations
import streamlit as st
from web.utils.data_bridge import ETFSearchResult, WatchlistViewData
from web.styles.theme import (
    BUY_COLOR, SELL_COLOR, HOLD_COLOR, INFO_COLOR, MUTED_COLOR,
    BORDER_COLOR, score_color, progress_bar,
)


def render_search_result(result: ETFSearchResult) -> None:
    _search_result_card(result)


def render_watchlist(data: WatchlistViewData) -> None:
    _favorites_section(data)
    _watchlist_section(data)


# ── Search Result Card ────────────────────────────────────────────────────────

def _search_result_card(r: ETFSearchResult) -> None:
    if not r.ticker:
        return

    if not r.found:
        st.markdown(f"""
<div class="dss-card" style="text-align:center;padding:20px;">
  <div style="font-size:24px;font-weight:800;color:{MUTED_COLOR};">{r.ticker}</div>
  <div class="dss-card-sub" style="margin-top:6px;">분석 대상에 없는 티커입니다.</div>
  <div style="font-size:12px;color:{MUTED_COLOR};margin-top:4px;">{r.reason}</div>
</div>
""", unsafe_allow_html=True)
        return

    rec_color = (BUY_COLOR  if r.recommendation == "추천"
                 else (SELL_COLOR if r.recommendation == "회피" else HOLD_COLOR))
    rec_bg    = ("#f0fdf4" if r.recommendation == "추천"
                 else ("#fef2f2" if r.recommendation == "회피" else "#fffbeb"))

    top_badge = ('&nbsp;<span class="badge badge-buy">Top ETF</span>'
                 if r.is_top else "")
    fav_badge = ('&nbsp;<span class="badge badge-info">즐겨찾기</span>'
                 if r.is_favorite else "")
    wl_badge  = ('&nbsp;<span class="badge badge-muted">관심</span>'
                 if r.is_watchlist else "")

    rs_color  = score_color(r.rs_score)
    rs_bar    = progress_bar(r.rs_score, 100, rs_color)

    rot_color = score_color(r.rotation_score) if r.rotation_score > 0 else MUTED_COLOR
    rot_bar   = progress_bar(r.rotation_score, 100, rot_color) if r.rotation_score > 0 else ""

    st.markdown(f"""
<div class="dss-card" style="border:2px solid {rec_color};background:{rec_bg};">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <div style="font-size:28px;font-weight:900;color:#1e293b;">{r.ticker}</div>
      <div style="margin-top:4px;">{top_badge}{fav_badge}{wl_badge}</div>
    </div>
    <div style="text-align:right;">
      <div style="font-size:18px;font-weight:800;color:{rec_color};">{r.recommendation}</div>
      <div style="font-size:11px;color:{MUTED_COLOR};">{r.macro_state}</div>
    </div>
  </div>
  <div class="dss-divider"></div>
  <div class="dss-card-title" style="margin-bottom:4px;">Relative Strength</div>
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
    <div style="flex:1;">{rs_bar}</div>
    <div style="font-weight:700;color:{rs_color};width:38px;text-align:right;">{r.rs_score:.0f}</div>
  </div>
  {"" if not r.rotation_score else f'''
  <div class="dss-card-title" style="margin-bottom:4px;">Rotation Score</div>
  <div style="display:flex;align-items:center;gap:8px;">
    <div style="flex:1;">{rot_bar}</div>
    <div style="font-weight:700;color:{rot_color};width:38px;text-align:right;">{r.rotation_score:.0f}</div>
  </div>'''}
  <div class="why-box" style="margin-top:10px;">
    <div class="why-label">분석 근거</div>
    {r.reason}
  </div>
</div>
""", unsafe_allow_html=True)


# ── Favorites Section ─────────────────────────────────────────────────────────

def _favorites_section(data: WatchlistViewData) -> None:
    st.markdown('<div class="section-hdr">⭐ 즐겨찾기</div>', unsafe_allow_html=True)

    if not data.favorites:
        st.markdown(f"""
<div class="dss-card" style="text-align:center;padding:16px;">
  <div class="dss-card-sub">즐겨찾기가 없습니다.</div>
  <div style="font-size:12px;color:{MUTED_COLOR};margin-top:4px;">
    아래 검색에서 ETF를 찾아 즐겨찾기에 추가하세요.
  </div>
</div>
""", unsafe_allow_html=True)
        return

    for r in data.favorites:
        _compact_etf_row(r, star=True)


def _watchlist_section(data: WatchlistViewData) -> None:
    st.markdown('<div class="section-hdr">👁️ 관심 ETF</div>', unsafe_allow_html=True)

    if not data.watchlist:
        st.markdown(f"""
<div class="dss-card" style="text-align:center;padding:16px;">
  <div class="dss-card-sub">관심 ETF가 없습니다.</div>
</div>
""", unsafe_allow_html=True)
        return

    for r in data.watchlist:
        _compact_etf_row(r, star=False)


def _compact_etf_row(r: ETFSearchResult, star: bool) -> None:
    rec_color = (BUY_COLOR  if r.recommendation == "추천"
                 else (SELL_COLOR if r.recommendation == "회피" else HOLD_COLOR))
    rs_bar = progress_bar(r.rs_score, 100, rec_color)
    icon   = "⭐" if star else "👁️"
    top_mark = " 🏆" if r.is_top else ""

    st.markdown(f"""
<div class="dss-card" style="padding:10px 14px;margin-bottom:6px;">
  <div style="display:flex;align-items:center;gap:10px;">
    <div style="font-size:14px;">{icon}</div>
    <div style="font-weight:700;font-size:15px;width:52px;">{r.ticker}{top_mark}</div>
    <div style="flex:1;">{rs_bar}</div>
    <div style="width:42px;text-align:right;font-weight:700;
                font-size:14px;color:{rec_color};">{r.rs_score:.0f}</div>
    <div style="width:60px;text-align:right;font-size:12px;
                color:{rec_color};font-weight:600;">{r.recommendation}</div>
  </div>
</div>
""", unsafe_allow_html=True)
