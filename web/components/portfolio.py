"""
web/components/portfolio.py
💼 Portfolio 탭 — 배분 현황 및 목표 배분
UI는 렌더링만 한다. 계산 없음.
"""
from __future__ import annotations
import streamlit as st
from web.utils.data_bridge import PortfolioViewData, AllocRow, RotationRow
from web.styles.theme import (
    progress_bar, score_color,
    BUY_COLOR, SELL_COLOR, INFO_COLOR, HOLD_COLOR, MUTED_COLOR,
)

# Plotly optional
try:
    import plotly.graph_objects as go
    _HAS_PLOTLY = True
except ImportError:
    _HAS_PLOTLY = False


def render(data: PortfolioViewData) -> None:
    """Portfolio 탭 전체 렌더링."""
    _summary_cards(data)
    _rotation_section(data)      # ★ 순환매 추천 배분 (최상단 강조)
    _allocation_wheel(data)
    _allocation_table(data)
    _delta_summary(data)
    _monte_carlo_card(data)


# ── 순환매 추천 배분 ──────────────────────────────────────────────────────────

def _rotation_section(d: PortfolioViewData) -> None:
    """RS 점수 기반 순환매 추천 배분 섹션."""
    rows = d.rotation_rows
    if not rows:
        return

    included = [r for r in rows if r.included]
    excluded = [r for r in rows if not r.included]

    # 헤더
    st.markdown("""
<div class="section-hdr" style="margin-top:4px;">
  🔄 순환매 추천 배분
  <span style="font-size:11px;font-weight:400;color:#64748b;margin-left:8px;">
    RS ≥ 80 섹터만 선택 · RS 비례 배분 · 단일 최대 35%
  </span>
</div>
""", unsafe_allow_html=True)

    if not included:
        st.info("현재 RS 80 이상 섹터 없음 — 전체 현금 보유 권장")
        return

    # 포함 섹터 카드
    rows_html = ""
    for r in included:
        bar_w  = int(r.weight_pct / 35 * 100)   # 35%=100% 기준 바
        medal  = "🥇" if r.weight_pct == max(x.weight_pct for x in included) else ""
        rows_html += f"""
<div style="display:flex;align-items:center;padding:7px 0;border-bottom:1px solid #f1f5f9;">
  <div style="width:52px;font-weight:700;font-size:14px;color:#1e293b;">{r.ticker}</div>
  <div style="flex:1;margin:0 10px;">
    <div style="background:#e2e8f0;border-radius:4px;height:10px;overflow:hidden;">
      <div style="width:{bar_w}%;background:#3b82f6;height:100%;border-radius:4px;transition:width 0.4s;"></div>
    </div>
  </div>
  <div style="width:46px;text-align:right;font-weight:700;font-size:14px;color:#3b82f6;">{r.weight_pct:.1f}%</div>
  <div style="width:28px;text-align:center;font-size:14px;">{medal}</div>
  <div style="width:44px;text-align:right;font-size:11px;color:#64748b;">RS {r.rs_score:.0f}</div>
</div>"""

    # 제외 섹터 요약
    excl_text = " · ".join(f"{r.ticker}({r.rs_score:.0f})" for r in excluded) if excluded else ""

    st.markdown(f"""
<div class="dss-card" style="padding:12px 16px;">
  {rows_html}
  {"<div style='margin-top:10px;font-size:11px;color:#94a3b8;'>제외 (RS<80): " + excl_text + "</div>" if excl_text else ""}
</div>
""", unsafe_allow_html=True)

    # 추천 요약 문장
    top3_names = ", ".join(r.ticker for r in included[:3])
    st.markdown(f"""
<div style="background:#eff6ff;border-left:3px solid #3b82f6;padding:10px 14px;
            border-radius:0 6px 6px 0;margin:8px 0;font-size:13px;color:#1e40af;">
  💡 현재 시장: <strong>{top3_names}</strong> 집중 — 실시간 RS 점수 반영 (FRED + yfinance)
</div>
""", unsafe_allow_html=True)


# ── Summary Cards ─────────────────────────────────────────────────────────────

def _summary_cards(d: PortfolioViewData) -> None:
    div_color = score_color(d.diversification_score)
    reb_color = INFO_COLOR if "Week" in d.rebalance_urgency else MUTED_COLOR

    st.markdown(f"""
<div class="metric-grid">
  <div class="metric-cell">
    <div class="metric-label">운용 국면</div>
    <div class="metric-value" style="font-size:18px;color:{INFO_COLOR};">{d.regime}</div>
    <div class="metric-sub">{d.regime_explanation[:30] if d.regime_explanation else ""}</div>
  </div>
  <div class="metric-cell">
    <div class="metric-label">분산화 점수</div>
    <div class="metric-value" style="color:{div_color};">{d.diversification_score:.0f}</div>
    <div class="metric-sub">/100</div>
  </div>
  <div class="metric-cell">
    <div class="metric-label">현금 권장 비중</div>
    <div class="metric-value" style="color:{MUTED_COLOR};">{d.cash_pct:.1f}%</div>
  </div>
  <div class="metric-cell">
    <div class="metric-label">리밸런싱 시기</div>
    <div class="metric-value" style="font-size:16px;color:{reb_color};">{d.rebalance_urgency}</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Allocation Wheel (Pie Chart) ──────────────────────────────────────────────

def _allocation_wheel(d: PortfolioViewData) -> None:
    st.markdown('<div class="section-hdr">🍩 Target Allocation</div>', unsafe_allow_html=True)

    if not d.rows:
        st.info("배분 데이터 없음")
        return

    if _HAS_PLOTLY:
        labels = [r.ticker for r in d.rows if r.target_pct > 0]
        values = [r.target_pct for r in d.rows if r.target_pct > 0]
        if d.cash_pct > 0:
            labels.append("Cash")
            values.append(d.cash_pct)

        fig = go.Figure(go.Pie(
            labels=labels,
            values=values,
            hole=0.45,
            textinfo="label+percent",
            textfont_size=11,
            marker=dict(
                colors=[
                    "#3b82f6", "#22c55e", "#f97316", "#ef4444",
                    "#8b5cf6", "#06b6d4", "#eab308", "#ec4899",
                    "#10b981", "#f59e0b", "#6366f1", "#64748b",
                ],
                line=dict(color="#ffffff", width=2),
            ),
        ))
        fig.update_layout(
            margin=dict(t=10, b=10, l=10, r=10),
            height=280,
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        fig.add_annotation(
            text=f"{d.regime}<br><span style='font-size:10px'>국면</span>",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=13, color="#1e293b"),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        # Fallback: text list
        for r in d.rows:
            bar = progress_bar(r.target_pct, 100, INFO_COLOR)
            st.markdown(f"""
<div class="alloc-row">
  <div class="alloc-ticker">{r.ticker}</div>
  <div class="alloc-bar-wrap">{bar}</div>
  <div class="alloc-pct">{r.target_pct:.1f}%</div>
</div>""", unsafe_allow_html=True)


# ── Allocation Table ──────────────────────────────────────────────────────────

def _allocation_table(d: PortfolioViewData) -> None:
    st.markdown('<div class="section-hdr">📋 배분 상세 (목표 vs 현재)</div>', unsafe_allow_html=True)

    if not d.rows:
        return

    header = """
<div class="alloc-row" style="border-bottom:2px solid #e2e8f0;">
  <div class="alloc-ticker" style="font-size:11px;color:#64748b;">티커</div>
  <div class="alloc-bar-wrap" style="font-size:11px;color:#64748b;">목표</div>
  <div class="alloc-pct" style="font-size:11px;color:#64748b;">목표%</div>
  <div class="alloc-delta-pos" style="font-size:11px;color:#64748b;">변화</div>
</div>"""

    rows_html = header
    for r in d.rows:
        bar   = progress_bar(r.target_pct, 100, INFO_COLOR)
        delta = r.delta_pct
        if delta > 0.05:
            delta_cls = "alloc-delta-pos"
            delta_str = f"+{delta:.1f}%"
        elif delta < -0.05:
            delta_cls = "alloc-delta-neg"
            delta_str = f"{delta:.1f}%"
        else:
            delta_cls = "alloc-delta-zero"
            delta_str = "—"

        rows_html += f"""
<div class="alloc-row">
  <div class="alloc-ticker">{r.ticker}</div>
  <div class="alloc-bar-wrap">{bar}</div>
  <div class="alloc-pct">{r.target_pct:.1f}%</div>
  <div class="{delta_cls}">{delta_str}</div>
</div>"""

    st.markdown(f'<div class="dss-card" style="padding:10px 14px;">{rows_html}</div>',
                unsafe_allow_html=True)


# ── Delta Summary ─────────────────────────────────────────────────────────────

def _delta_summary(d: PortfolioViewData) -> None:
    if not d.top_delta_up and not d.top_delta_down:
        return
    st.markdown('<div class="section-hdr">⚡ 주요 변경 사항</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        _delta_list(d.top_delta_up, "▲ 증가", BUY_COLOR)
    with col2:
        _delta_list(d.top_delta_down, "▼ 감소", SELL_COLOR)


def _delta_list(rows: list[AllocRow], label: str, color: str) -> None:
    if not rows:
        return
    items = "".join(
        f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #e2e8f0;">'
        f'<span style="font-weight:600;font-size:13px;">{r.ticker}</span>'
        f'<span style="font-weight:700;font-size:13px;color:{color};">{"+" if r.delta_pct > 0 else ""}{r.delta_pct:.1f}%</span>'
        f'</div>'
        for r in rows
    )
    st.markdown(f"""
<div class="dss-card" style="padding:10px 14px;">
  <div class="dss-card-title" style="color:{color};">{label}</div>
  {items}
</div>
""", unsafe_allow_html=True)


# ── Monte Carlo Card ──────────────────────────────────────────────────────────

def _monte_carlo_card(d: PortfolioViewData) -> None:
    if d.expected_return == 0.0 and d.expected_vol == 0.0:
        return
    st.markdown('<div class="section-hdr">🎲 예상 성과 (Monte Carlo)</div>', unsafe_allow_html=True)

    ret_color = BUY_COLOR if d.expected_return > 0 else SELL_COLOR
    st.markdown(f"""
<div class="metric-grid">
  <div class="metric-cell">
    <div class="metric-label">예상 연간 수익률</div>
    <div class="metric-value" style="color:{ret_color};">{"+" if d.expected_return > 0 else ""}{d.expected_return:.1f}%</div>
    <div class="metric-sub">기대값 (Monte Carlo)</div>
  </div>
  <div class="metric-cell">
    <div class="metric-label">예상 연간 변동성</div>
    <div class="metric-value" style="color:{HOLD_COLOR};">{d.expected_vol:.1f}%</div>
    <div class="metric-sub">1σ 범위</div>
  </div>
</div>
""", unsafe_allow_html=True)
