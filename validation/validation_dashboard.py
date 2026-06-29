"""
validation/validation_dashboard.py
Streamlit Validation Center — 7 Tabs
Run: streamlit run validation/validation_dashboard.py
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

st.set_page_config(
    page_title="DSS Validation Center",
    page_icon="🔬",
    layout="wide",
)

from validation.data_models import (
    ValidationResult, ValidationGrade, HealthGrade
)


# ═══════════════════════════════════════════════════════════════════════════
# Color helpers (no external deps)
# ═══════════════════════════════════════════════════════════════════════════
def _grade_color(g: ValidationGrade) -> str:
    return {"A+":"#00c851","A":"#33b679","B":"#f9a825",
            "C":"#ff8800","D":"#ff4444","F":"#cc0000"}.get(g.value,"#888")

def _health_color(h: HealthGrade) -> str:
    return {"Excellent":"#00c851","Good":"#33b679","Fair":"#f9a825",
            "Poor":"#ff8800","Critical":"#cc0000"}.get(h.value,"#888")


# ═══════════════════════════════════════════════════════════════════════════
# Demo data factory
# ═══════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def _load_demo_result():
    import math, random
    from validation.data_models import DecisionRecord, PriceHistory, ValidationInput
    from validation.validation_engine import ValidationEngine

    rng = random.Random(99)
    n   = 400

    # Synthetic price history (11 ETFs)
    tickers = ["XLK","XLC","XLY","XLF","XLI","XLE","XLB","XLV","XLP","XLU","XLRE"]
    prices  = {}
    for t in tickers:
        p = [100.0]
        for _ in range(n):
            p.append(p[-1] * (1 + rng.gauss(0.0004, 0.012)))
        prices[t] = p

    dates = [f"2023-{(i//21+1):02d}-{(i%21+1):02d}" for i in range(n+1)]

    ph = PriceHistory(dates=dates, prices=prices)

    # Synthetic benchmark
    bench_spy = [100.0]
    bench_qqq = [100.0]
    for _ in range(n):
        bench_spy.append(bench_spy[-1] * (1 + rng.gauss(0.0003, 0.011)))
        bench_qqq.append(bench_qqq[-1] * (1 + rng.gauss(0.0005, 0.014)))

    # Decision records (one per date after first)
    records = []
    wts_eq = {t: 0.95/len(tickers) for t in tickers}
    for i in range(1, n+1):
        macro = min(100, max(0, rng.gauss(65, 12)))
        act_ret = rng.gauss(0.0004, 0.009)
        conf = min(95, max(20, rng.gauss(62, 12)))
        action = "BUY" if macro > 55 else ("SELL" if macro < 40 else "HOLD")
        records.append(DecisionRecord(
            date=dates[i],
            macro_score   = round(macro, 1),
            breadth_score = round(min(100,max(0,rng.gauss(60,10))), 1),
            rs_score      = round(min(100,max(0,rng.gauss(63,11))), 1),
            rotation_score= round(min(100,max(0,rng.gauss(58,12))), 1),
            portfolio_score=round(min(100,max(0,rng.gauss(65,10))), 1),
            risk_score    = round(min(100,max(0,rng.gauss(35,12))), 1),
            confidence    = round(conf, 1),
            action        = action,
            weights       = wts_eq,
            actual_return = round(act_ret, 6),
            correct       = (act_ret > 0) == (action == "BUY"),
        ))

    inp = ValidationInput(
        decision_records  = records,
        price_history     = ph,
        benchmark_prices  = {"SPY": bench_spy, "QQQ": bench_qqq},
        initial_capital   = 100_000.0,
        risk_free_rate    = 0.045,
        replay_date       = dates[50],
    )

    engine = ValidationEngine()
    return engine.validate(inp)


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════
def main():
    result: ValidationResult = _load_demo_result()
    rm  = result.risk_metrics
    bts = result.benchmarks

    # ── Header ─────────────────────────────────────────────────────────
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown("# 🔬 DSS Validation Center")
    with col2:
        gc = _grade_color(result.overall_grade)
        st.markdown(
            f"<h2 style='color:{gc};text-align:right'>"
            f"Grade: {result.overall_grade.value}</h2>",
            unsafe_allow_html=True,
        )
    st.markdown("---")

    tabs = st.tabs([
        "📊 Validation Center",
        "📈 Strategy Performance",
        "⚙️ Engine Health",
        "🎬 Decision Replay",
        "🔍 Sensitivity",
        "📅 Backtest Timeline",
        "★ Weight Recommendation",
    ])

    # ── Tab 1: Validation Center ──────────────────────────────────────
    with tabs[0]:
        st.subheader("핵심 리스크 지표")
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("CAGR",         f"{rm.cagr*100:.2f}%")
        c2.metric("Sharpe",       f"{rm.sharpe:.3f}")
        c3.metric("Max Drawdown", f"{rm.max_drawdown*100:.2f}%",
                  delta=f"{-rm.max_drawdown*100:.1f}%", delta_color="inverse")
        c4.metric("Sortino",      f"{rm.sortino:.3f}")
        c1b,c2b,c3b,c4b = st.columns(4)
        c1b.metric("Calmar",   f"{rm.calmar:.3f}")
        c2b.metric("Volatility",f"{rm.volatility*100:.2f}%")
        c3b.metric("Ulcer Index",f"{rm.ulcer_index*100:.2f}%")
        c4b.metric("VaR 95%",  f"{rm.var_95*100:.2f}%")

        if bts:
            st.subheader("벤치마크 비교")
            for b in bts:
                ex = "✅" if b.alpha > 0 else "❌"
                st.markdown(
                    f"**{b.benchmark_id}** — Alpha {b.alpha*100:+.2f}% {ex} | "
                    f"Beta {b.beta:.2f} | IR {b.information_ratio:.3f} | "
                    f"상관 {b.correlation:.3f}"
                )

        st.subheader("XAI 요약")
        x = result.xai_summary
        st.info(x.overall_narrative)
        st.markdown(f"- **SPY 대비**: {x.why_outperformed_spy}")
        st.markdown(f"- **Alpha 최대 Engine**: {x.best_alpha_engine}")
        st.markdown(f"- **불리한 환경**: {x.worst_market_env}")
        st.markdown(f"- **Weight 인사이트**: {x.best_weight_insight}")

        if result.reasons:
            st.success("  \n".join(result.reasons))
        if result.warnings:
            st.warning("  \n".join(result.warnings))

    # ── Tab 2: Strategy Performance ───────────────────────────────────
    with tabs[1]:
        st.subheader("포트폴리오 성과")
        bt = result.backtest
        if bt.portfolio_values:
            try:
                import plotly.graph_objects as go
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=list(range(len(bt.portfolio_values))),
                    y=bt.portfolio_values, name="Strategy", line_color="#00c851"))
                fig.update_layout(title="누적 포트폴리오 가치",
                                  xaxis_title="거래일", yaxis_title="포트폴리오 가치")
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                st.line_chart(bt.portfolio_values)

        wf = result.walk_forward
        st.subheader("Walk-Forward 검증")
        c1, c2, c3 = st.columns(3)
        c1.metric("평균 OOS Sharpe", f"{wf.avg_oos_sharpe:.3f}")
        c2.metric("안정성 점수",    f"{wf.stability_score:.1f}%")
        c3.metric("OOS 일관성",     "✅ 통과" if wf.oos_consistent else "❌ 불통과")
        if wf.windows:
            oos_sharpes = [w.oos_sharpe for w in wf.windows]
            st.line_chart(oos_sharpes)
            st.caption("WF Window별 OOS Sharpe")

        st.subheader("MC Validation")
        mc = result.monte_carlo
        st.markdown(
            f"p-value: **{mc.p_value:.3f}** — "
            f"{'★ 통계적 유의 (p < 0.05)' if mc.significant else '비유의 (p ≥ 0.05)'}"
        )
        st.markdown(
            f"시뮬 Sharpe P5/P50/P95: "
            f"{mc.sim_sharpe_p5:.3f} / {mc.sim_sharpe_p50:.3f} / {mc.sim_sharpe_p95:.3f} | "
            f"실제: **{mc.strategy_sharpe:.3f}**"
        )

    # ── Tab 3: Engine Health ──────────────────────────────────────────
    with tabs[2]:
        st.subheader("Engine 건강도")
        for eng, h in result.engine_health.items():
            col_e, col_b, col_g = st.columns([2, 4, 1])
            with col_e:
                hc = _health_color(h.grade)
                st.markdown(f"**{eng}** <span style='color:{hc}'>{h.grade.value}</span>",
                            unsafe_allow_html=True)
            with col_b:
                st.progress(int(h.overall))
            with col_g:
                st.markdown(f"{h.overall:.0f}/100 {h.trend}")

        st.subheader("자동 진단 결과")
        diag = result.diagnostic
        st.metric("전체 건강도", f"{diag.overall_health:.1f}/100")
        if diag.degraded_engines:
            st.error(f"성능 저하 Engine: {', '.join(diag.degraded_engines)}")
        for f in diag.findings[:5]:
            icon = "🔴" if f.severity.value == "Critical" else "🟡"
            with st.expander(f"{icon} {f.engine} — {f.issue}"):
                st.markdown(f"**근본 원인:** {f.root_cause}")
                st.markdown(f"**권고 사항:** {f.recommendation}")

        st.subheader("Confidence Calibration")
        cal = result.calibration
        st.markdown(
            f"ECE: **{cal.ece:.2f}%** | Brier: **{cal.brier_score:.4f}** | "
            f"과신 구간: {cal.overconfident_pct:.0f}%"
        )
        st.caption(cal.xai_summary)

    # ── Tab 4: Decision Replay ────────────────────────────────────────
    with tabs[3]:
        st.subheader("의사결정 재현")
        replay = result.replay
        if replay:
            st.info(replay.explanation)
            cols = st.columns(3)
            cols[0].metric("결정",   replay.decision)
            cols[1].metric("신뢰도", f"{replay.confidence:.1f}")
            cols[2].metric("실제 수익", f"{replay.actual_return*100:.2f}%",
                           delta="정확" if replay.was_correct else "오류")
            st.markdown("**당시 Engine 점수:**")
            sc = st.columns(len(replay.engine_scores))
            for i, (eng, score) in enumerate(replay.engine_scores.items()):
                sc[i].metric(eng, f"{score:.0f}")
            if replay.weights:
                st.markdown("**당시 배분:**")
                items = sorted(replay.weights.items(), key=lambda x:-x[1])[:6]
                st.markdown(" | ".join(f"**{t}** {w:.1%}" for t,w in items))
        else:
            st.info("replay_date를 ValidationInput에 지정하면 재현 결과가 표시됩니다.")

    # ── Tab 5: Sensitivity Analysis ───────────────────────────────────
    with tabs[4]:
        st.subheader("Weight 민감도 분석")
        sens = result.sensitivity
        st.markdown(
            f"가장 민감: **{sens.most_sensitive_engine}** | "
            f"가장 안정: **{sens.least_sensitive_engine}** | "
            f"Sharpe 최대 개선: **{sens.max_sharpe_engine}**"
        )
        # Pivot table
        engines = list({c.engine for c in sens.grid})
        deltas  = sorted({c.delta_pct for c in sens.grid})
        if engines and deltas:
            import io
            rows = []
            for eng in engines:
                row = {"Engine": eng}
                for d in deltas:
                    cell = next((c for c in sens.grid
                                 if c.engine == eng and c.delta_pct == d), None)
                    row[f"Δ{d:+.0f}%"] = f"{cell.sharpe_change:+.4f}" if cell else "-"
                rows.append(row)
            st.table(rows)

        st.subheader("Robustness Test")
        rob = result.robustness
        st.metric("안정성 점수", f"{rob.robustness_score:.1f}%")
        if rob.fragile_params:
            st.warning(f"취약 파라미터: {', '.join(rob.fragile_params)}")
        if rob.stable_params:
            st.success(f"안정 파라미터: {', '.join(rob.stable_params)}")

    # ── Tab 6: Backtest Timeline ──────────────────────────────────────
    with tabs[5]:
        st.subheader("거래 내역")
        bt = result.backtest
        st.metric("총 거래 수",  bt.n_trades)
        st.metric("승률",        f"{bt.win_rate*100:.1f}%")
        st.metric("총 수익률",   f"{bt.total_return*100:.2f}%")
        if bt.trades[:20]:
            data = [{"날짜": t.date, "티커": t.ticker,
                     "액션": t.action,
                     "이전 비중": f"{t.weight_before:.1%}",
                     "이후 비중": f"{t.weight_after:.1%}"}
                    for t in bt.trades[:20]]
            st.table(data)

        st.subheader("실패 분석")
        fa = result.failure_analysis
        c1,c2,c3 = st.columns(3)
        c1.metric("총 실패", fa.total_failures)
        c2.metric("실패율",  f"{fa.failure_rate*100:.1f}%")
        c3.metric("평균 회복",f"{fa.recovery_avg_days:.0f}일")
        st.caption(f"가장 흔한 실패 환경: {fa.common_context}")
        if fa.by_type:
            st.bar_chart(fa.by_type)

        st.subheader("XAI 일관성 감사")
        audit = result.xai_audit
        st.metric("평균 일관성",     f"{audit.avg_consistency:.1f}%")
        st.metric("저일관성 결정",   audit.low_consistency_cnt)
        st.metric("과신 오류",       audit.high_confidence_wrong)

    # ── Tab 7: ★ Weight Recommendation ───────────────────────────────
    with tabs[6]:
        st.subheader("★ Adaptive Weight Recommendation Engine")
        st.error(
            "⚠️ 아래 추천은 참고용입니다. **절대 자동 적용되지 않습니다.** "
            "검토 후 직접 config 파일을 수정하십시오."
        )
        recs = result.weight_recommendations
        if not recs:
            st.success("현재 Weight 설정이 적절합니다. 변경 추천 없음.")
        else:
            for rec in recs:
                conf_icon = {"High":"🟢","Medium":"🟡","Low":"🔴"}.get(rec.confidence_level,"⚪")
                with st.expander(
                    f"{conf_icon} {rec.engine}: {rec.current_weight:.1f} → "
                    f"{rec.recommended_weight:.1f} (Δ{rec.delta:+.1f})"
                ):
                    st.markdown(f"**추천 이유:** {rec.reason}")
                    st.markdown(f"**예상 Sharpe 변화:** {rec.expected_sharpe_delta:+.4f}")
                    st.markdown(f"**예상 수익률 변화:** {rec.expected_return_delta*100:+.3f}bps")
                    st.markdown(f"**신뢰 수준:** {rec.confidence_level}")
                    st.warning(f"⚠️ 주의: {rec.caveat}")


if __name__ == "__main__":
    main()
