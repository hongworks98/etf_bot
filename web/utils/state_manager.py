"""
web/utils/state_manager.py
Streamlit Session State 헬퍼 — 세션 상태 초기화 및 접근 통일화.
"""
from __future__ import annotations
from typing import Any


# ── 기본값 ────────────────────────────────────────────────────────────────────

_DEFAULTS: dict[str, Any] = {
    "refresh_ts":          0.0,       # 마지막 새로고침 타임스탬프
    "search_query":        "",        # Smart Search 입력
    "selected_tab":        0,         # 현재 선택 탭
    "explain_expanded":    False,     # AI Explain More 펼침 여부
    "notification_config": {          # Notification 설정
        "telegram_enabled":          False,
        "discord_enabled":           False,
        "email_enabled":             False,
        "notify_on_buy":             True,
        "notify_on_sell":            True,
        "notify_on_high_confidence": True,
        "confidence_threshold":      70.0,
    },
    "pipeline_running":    False,     # 파이프라인 실행 중 여부
    "last_action":         None,      # 마지막 BUY/SELL/HOLD
}


def init(state: Any) -> None:
    """
    Streamlit session_state에 기본값을 초기화한다.
    이미 설정된 키는 건드리지 않는다.
    """
    for key, val in _DEFAULTS.items():
        if key not in state:
            state[key] = val


def get(state: Any, key: str) -> Any:
    """session_state 에서 값을 가져온다. 없으면 기본값."""
    return state.get(key, _DEFAULTS.get(key))


def set_value(state: Any, key: str, value: Any) -> None:
    """session_state 에 값을 설정."""
    state[key] = value


def get_notification_config(state: Any) -> dict:
    return state.get("notification_config", _DEFAULTS["notification_config"])


def update_notification_config(state: Any, **kwargs: Any) -> None:
    cfg = state.setdefault("notification_config",
                           dict(_DEFAULTS["notification_config"]))
    cfg.update(kwargs)


def should_notify(state: Any, action: str, confidence: float) -> bool:
    """현재 알림 설정에 따라 알림을 보내야 하는지 판단 (UI용, 실제 전송 없음)."""
    cfg = get_notification_config(state)
    if action == "BUY"  and cfg.get("notify_on_buy"):  return True
    if action == "SELL" and cfg.get("notify_on_sell"): return True
    threshold = cfg.get("confidence_threshold", 70.0)
    if cfg.get("notify_on_high_confidence") and confidence >= threshold:
        return True
    return False
