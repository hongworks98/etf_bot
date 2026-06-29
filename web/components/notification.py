"""
web/components/notification.py
Notification Center config UI.
실제 알림 전송 없음 — 구조 설계만 (향후 Web Step 4에서 실제 연동).
UI renders only — no calculations.
"""
from __future__ import annotations
import streamlit as st
from web.styles.theme import (
    BUY_COLOR, SELL_COLOR, INFO_COLOR, MUTED_COLOR, BORDER_COLOR,
)


def render(state: object, result: object) -> None:
    """
    Notification Center 렌더링.
    state: Streamlit session_state
    result: DSSResult (알림 조건 판단용)
    """
    _channel_config(state)
    _trigger_config(state)
    _preview_section(state, result)
    _future_notice()


# ── Channel Config ────────────────────────────────────────────────────────────

def _channel_config(state: object) -> None:
    st.markdown('<div class="section-hdr">📡 알림 채널</div>', unsafe_allow_html=True)

    cfg = state.get("notification_config", {}) if hasattr(state, "get") else {}

    channels = [
        ("telegram_enabled", "Telegram", "🤖", "Bot Token 필요"),
        ("discord_enabled",  "Discord",  "💬", "Webhook URL 필요"),
        ("email_enabled",    "Email",    "📧", "SMTP 설정 필요"),
    ]

    rows_html = ""
    for key, name, icon, note in channels:
        enabled = cfg.get(key, False)
        status_color = BUY_COLOR if enabled else MUTED_COLOR
        status_text  = "활성" if enabled else "미설정"
        badge_cls    = "badge-buy" if enabled else "badge-muted"

        rows_html += f"""
<div style="display:flex;align-items:center;gap:12px;padding:10px 0;
            border-bottom:1px solid {BORDER_COLOR};">
  <div style="font-size:20px;">{icon}</div>
  <div style="flex:1;">
    <div style="font-weight:600;font-size:14px;color:#1e293b;">{name}</div>
    <div style="font-size:12px;color:{MUTED_COLOR};">{note}</div>
  </div>
  <span class="badge {badge_cls}">{status_text}</span>
</div>"""

    st.markdown(f'<div class="dss-card" style="padding:4px 14px;">{rows_html}</div>',
                unsafe_allow_html=True)

    st.markdown(f"""
<div style="font-size:12px;color:{MUTED_COLOR};margin-top:4px;padding:0 4px;">
  📌 실제 채널 연동은 Web Step 4에서 구현 예정입니다.
</div>
""", unsafe_allow_html=True)


# ── Trigger Config ────────────────────────────────────────────────────────────

def _trigger_config(state: object) -> None:
    st.markdown('<div class="section-hdr">🔔 알림 조건</div>', unsafe_allow_html=True)

    cfg = state.get("notification_config", {}) if hasattr(state, "get") else {}
    threshold = cfg.get("confidence_threshold", 70.0)

    triggers = [
        ("notify_on_buy",             "BUY 신호 발생 시",       BUY_COLOR),
        ("notify_on_sell",            "SELL 신호 발생 시",      SELL_COLOR),
        ("notify_on_high_confidence", f"신뢰도 {threshold:.0f}% 이상 시", INFO_COLOR),
    ]

    rows_html = ""
    for key, label, color in triggers:
        enabled = cfg.get(key, True)
        icon    = "✅" if enabled else "⬜"
        rows_html += f"""
<div style="display:flex;align-items:center;gap:10px;padding:9px 0;
            border-bottom:1px solid {BORDER_COLOR};">
  <div style="font-size:16px;">{icon}</div>
  <div style="font-size:13px;color:#1e293b;font-weight:500;">{label}</div>
</div>"""

    st.markdown(f'<div class="dss-card" style="padding:4px 14px;">{rows_html}</div>',
                unsafe_allow_html=True)

    st.markdown(f"""
<div class="dss-card" style="margin-top:8px;">
  <div class="dss-card-title">신뢰도 임계값</div>
  <div style="display:flex;align-items:center;gap:8px;margin-top:6px;">
    <div class="dss-card-value" style="font-size:24px;">{threshold:.0f}%</div>
    <div class="dss-card-sub">이상 시 알림 발송</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Preview Section ───────────────────────────────────────────────────────────

def _preview_section(state: object, result: object) -> None:
    st.markdown('<div class="section-hdr">👁️ 알림 미리보기</div>', unsafe_allow_html=True)

    cfg        = state.get("notification_config", {}) if hasattr(state, "get") else {}
    action     = getattr(result, "recommended_action", "WAIT") or "WAIT"
    confidence = getattr(result, "overall_confidence", 0.0)
    top_etfs   = list(getattr(result, "top_opportunities", []))
    run_date   = getattr(result, "run_date", "")
    macro_state= getattr(result, "macro_state", "Unknown")

    threshold  = cfg.get("confidence_threshold", 70.0)
    would_send = (
        (action == "BUY"  and cfg.get("notify_on_buy",  True)) or
        (action == "SELL" and cfg.get("notify_on_sell", True)) or
        (cfg.get("notify_on_high_confidence", True) and confidence >= threshold)
    )

    if would_send:
        etf_str = ", ".join(top_etfs) if top_etfs else "없음"
        msg = (f"[DSS] {run_date}\n"
               f"액션: {action} | 신뢰도: {confidence:.0f}%\n"
               f"시장: {macro_state} | ETF: {etf_str}")
        st.markdown(f"""
<div style="background:#f0fdf4;border:1px solid #22c55e;border-radius:10px;padding:12px 14px;">
  <div style="font-size:12px;color:#15803d;font-weight:700;margin-bottom:6px;">
    ✅ 현재 설정으로 알림이 발송될 예정입니다.
  </div>
  <div style="font-family:monospace;font-size:12px;color:#1e293b;
              white-space:pre-line;">{msg}</div>
</div>
""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
<div style="background:#f8fafc;border:1px solid {BORDER_COLOR};border-radius:10px;
            padding:12px 14px;text-align:center;">
  <div style="font-size:13px;color:{MUTED_COLOR};">
    현재 조건에 해당하지 않아 알림이 발송되지 않습니다.
  </div>
</div>
""", unsafe_allow_html=True)


# ── Future Notice ─────────────────────────────────────────────────────────────

def _future_notice() -> None:
    st.markdown(f"""
<div style="margin-top:12px;padding:10px 14px;background:#eff6ff;
            border-radius:10px;font-size:12px;color:#1d4ed8;">
  <strong>Web Step 4 예정:</strong> Telegram Bot API, Discord Webhook,
  SMTP 이메일 실제 연동 구현. 현재는 설정 UI만 제공합니다.
</div>
""", unsafe_allow_html=True)
