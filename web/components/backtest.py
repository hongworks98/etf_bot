"""
web/components/backtest.py
📈 Backtest 탭 — Validation Engine 결과
UI는 렌더링만 한다. 계산 없음.
"""
from __future__ import annotations
import streamlit as st
from web.utils.data_bridge import BacktestViewData
from web.styles.theme import (
    progress_bar, score_color,
    BUY_COLOR, SELL_COLOR, INFO_COLOR, HOLD_COLOR, MUTED_COLOR,
    GRADE_COLORS,
)


def render(data: BacktestViewData) -> None:
    """Backtest 탭 전체 렌더링."""
    if not data.available:
        _not_available()
        return

    _grade_banner(data)
    _core_metrics(data)
    _quality_flags(data)
    _warnings_section(data)
    _reasons_section(data)


# ── Not Available ─────────────────────────────────────────────────────────────

def _not_available() -> None:
    st.markdown(f"""
<div class="dss-card" style="text-align:center;padding:32px;">
  <div style="font-size:36px;">📊</div>
  <div class="dss-card-value" style="font-size:18px;margin-top:8px;">Validation 데이터 없음</div>
  <div class="dss-card-sub">Validation Engine이 실행되지 않았습니다.</div>
</div>
""", unsafe_allow_html=True)


# ── Grade Banner ──────────────────────────────────────────────────────────────

def _grade_banner(d: BacktestViewData) -> None:
    color = GRADE_COLORS.get(d.grade, MUTED_COLOR)
    st.markdown(f"""
<div class="dss-card" style="text-align:center;padding:18px;">
  <div class="dss-card-title">전략 등급</div>
  <div style="font-size:52px;font-weight:900;color:{color};line-height:1.1;">{d.grade}</div>
  <div class="dss-card-sub" style="margin-top:4px;">
    {'검증 완료 ✅' if d.is_robust else '추가 검증 필요 ⚠️'}
    &nbsp;&nbsp;
    {'Monte Carlo 유의 ✅' if d.mc_significant else 'Monte Carlo 비유의'}
  </div>
</div>
""", unsafe_allow_html=True)


# ── Core Metrics ──────────────────────────────────────────────────────────────

def _core_metrics(d: BacktestViewData) -> None:
    st.markdown('<div class="section-hdr">📊 핵심 성과 지표</div>', unsafe_allow_html=True)

    cagr_color   = BUY_COLOR  if d.cagr    > 0  else SELL_COLOR
    sharpe_color = BUY_COLOR  if d.sharpe  > 1.0 else (HOLD_COLOR if d.sharpe > 0.5 else SELL_COLOR)
    sort_color   = BUY_COLOR  if d.sortino > 1.0 else (HOLD_COLOR if d.sortino > 0.5 else SELL_COLOR)
    dd_color     = BUY_COLOR  if d.max_drawdown < 10 else (HOLD_COLOR if d.max_drawdown < 20 else SELL_COLOR)
    wr_color     = BUY_COLOR  if d.win_rate > 55 else (HOLD_COLOR if d.win_rate >= 45 else SELL_COLOR)
    alpha_color  = BUY_COLOR  if d.alpha   > 0  else SELL_COLOR

    st.markdown(f"""
<div class="metric-grid">
  <div class="metric-cell">
    <div class="metric-label">CAGR</div>
    <div class="metric-value" style="color:{cagr_color};">{"+" if d.cagr > 0 else ""}{d.cagr:.2f}%</div>
    <div class="metric-sub">연환산 수익률</div>
  </div>
  <div class="metric-cell">
    <div class="metric-label">Sharpe Ratio</div>
    <div class="metric-value" style="color:{sharpe_color};">{d.sharpe:.2f}</div>
    <div class="metric-sub">위험조정 수익률</div>
  </div>
  <div class="metric-cell">
    <div class="metric-label">Sortino Ratio</div>
    <div class="metric-value" style="color:{sort_color};">{d.sortino:.2f}</div>
    <div class="metric-sub">하방 위험 조정</div>
  </div>
  <div class="metric-cell">
    <div class="metric-label">Max Drawdown</div>
    <div class="metric-value" style="color:{dd_color};">-{d.max_drawdown:.2f}%</div>
    <div class="metric-sub">최대 낙폭</div>
  </div>
  <div class="metric-cell">
    <div class="metric-label">Win Rate</div>
    <div class="metric-value" style="color:{wr_color};">{d.win_rate:.1f}%</div>
    <div class="metric-sub">승률</div>
  </div>
  <div class="metric-cell">
    <div class="metric-label">Alpha</div>
    <div class="metric-value" style="color:{alpha_color};">{"+" if d.alpha > 0 else ""}{d.alpha:.2f}%</div>
    <div class="metric-sub">초과 수익률</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Quality Flags ─────────────────────────────────────────────────────────────

def _quality_flags(d: BacktestViewData) -> None:
    st.markdown('<div class="section-hdr">🔍 검증 결과</div>', unsafe_allow_html=True)

    flags = [
        ("Walk-Forward 검증", d.is_robust, "통과 — 미래 데이터 유출 없음", "미통과 — 과적합 위험"),
        ("Monte Carlo 유의성", d.mc_significant, "통계적으로 유의함 (p < 0.05)", "통계적 유의성 불충분"),
    ]
    items = ""
    for label, passed, ok_text, fail_text in flags:
        icon  = "✅" if passed else "⚠️"
        color = BUY_COLOR if passed else HOLD_COLOR
        desc  = ok_text if passed else fail_text
        items += f"""
<div style="display:flex;align-items:flex-start;gap:10px;padding:8px 0;border-bottom:1px solid #e2e8f0;">
  <div style="font-size:18px;flex-shrink:0;">{icon}</div>
  <div>
    <div style="font-weight:600;font-size:13px;color:#1e293b;">{label}</div>
    <div style="font-size:12px;color:{color};margin-top:2px;">{desc}</div>
  </div>
</div>"""

    st.markdown(f'<div class="dss-card" style="padding:10px 14px;">{items}</div>',
                unsafe_allow_html=True)


# ── Warnings ─────────────────────────────────────────────────────────────────

def _warnings_section(d: BacktestViewData) -> None:
    if not d.warnings:
        return
    st.markdown('<div class="section-hdr">⚠️ 주의사항</div>', unsafe_allow_html=True)
    items = "".join(
        f'<div style="padding:6px 0;border-bottom:1px solid #e2e8f0;font-size:13px;color:#92400e;">⚠️ {w}</div>'
        for w in d.warnings
    )
    st.markdown(f'<div class="dss-card" style="background:#fffbeb;padding:10px 14px;">{items}</div>',
                unsafe_allow_html=True)


# ── Reasons ───────────────────────────────────────────────────────────────────

def _reasons_section(d: BacktestViewData) -> None:
    if not d.reasons:
        return
    st.markdown('<div class="section-hdr">📝 평가 근거</div>', unsafe_allow_html=True)
    items = "".join(
        f'<div class="brief-line">{r}</div>'
        for r in d.reasons
    )
    st.markdown(f'<div class="brief-box">{items}</div>', unsafe_allow_html=True)
