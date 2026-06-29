"""
web/styles/theme.py
Mobile-first CSS 테마 — 색상 상수 + CSS 주입
UI는 이 파일의 상수와 inject_css() 만 사용한다.

config/theme.yaml 이 존재하면 로드하고, 없으면 하드코딩 기본값을 사용한다.
기존 코드와 100% 호환 — 모든 상수는 그대로 유지된다.
"""
from __future__ import annotations
import os as _os


# ── YAML 설정 로더 ────────────────────────────────────────────────────────────

def _load_theme_yaml() -> dict:
    """config/theme.yaml 로드. 없거나 실패하면 빈 dict 반환."""
    try:
        import yaml
        _here  = _os.path.abspath(__file__)                        # web/styles/theme.py
        _root  = _os.path.dirname(_os.path.dirname(_os.path.dirname(_here)))  # project root
        _path  = _os.path.join(_root, "config", "theme.yaml")
        if _os.path.isfile(_path):
            with open(_path, "r", encoding="utf-8") as _f:
                return yaml.safe_load(_f) or {}
    except Exception:
        pass
    return {}


_THEME_YAML: dict = _load_theme_yaml()


def _color(key: str, default: str) -> str:
    """theme.yaml colors 섹션에서 색상 조회. 없으면 default 반환."""
    return _THEME_YAML.get("colors", {}).get(key, default)


def theme_yaml_loaded() -> bool:
    """config/theme.yaml 이 성공적으로 로드되었는지 반환."""
    return bool(_THEME_YAML)


# ── Color Constants ───────────────────────────────────────────────────────────

BUY_COLOR    = _color("buy",        "#22c55e")   # green-500
SELL_COLOR   = _color("sell",       "#ef4444")   # red-500
HOLD_COLOR   = _color("hold",       "#f97316")   # orange-500
INFO_COLOR   = _color("info",       "#3b82f6")   # blue-500
WARN_COLOR   = _color("warn",       "#eab308")   # yellow-500

BG_COLOR     = _color("bg",         "#ffffff")
CARD_COLOR   = _color("card",       "#f8fafc")
BORDER_COLOR = _color("border",     "#e2e8f0")
TEXT_COLOR   = _color("text",       "#1e293b")
MUTED_COLOR  = _color("muted",      "#64748b")
SUCCESS_BG   = _color("success_bg", "#f0fdf4")
DANGER_BG    = _color("danger_bg",  "#fef2f2")

_ac = _THEME_YAML.get("action_colors", {})
ACTION_COLORS = {
    "BUY":  _ac.get("BUY",  BUY_COLOR),
    "SELL": _ac.get("SELL", SELL_COLOR),
    "HOLD": _ac.get("HOLD", HOLD_COLOR),
    "WAIT": _ac.get("WAIT", HOLD_COLOR),
}

_hc = _THEME_YAML.get("health_colors", {})
HEALTH_COLORS = {
    "HEALTHY":  _hc.get("HEALTHY",  BUY_COLOR),
    "DEGRADED": _hc.get("DEGRADED", HOLD_COLOR),
    "CRITICAL": _hc.get("CRITICAL", SELL_COLOR),
    "UNKNOWN":  _hc.get("UNKNOWN",  MUTED_COLOR),
}

_gc = _THEME_YAML.get("grade_colors", {})
GRADE_COLORS = {
    "A+":  _gc.get("A+",  BUY_COLOR),
    "A":   _gc.get("A",   BUY_COLOR),
    "B":   _gc.get("B",   INFO_COLOR),
    "C":   _gc.get("C",   HOLD_COLOR),
    "D":   _gc.get("D",   SELL_COLOR),
    "F":   _gc.get("F",   SELL_COLOR),
    "N/A": _gc.get("N/A", MUTED_COLOR),
}


# ── CSS ───────────────────────────────────────────────────────────────────────

_CSS = f"""
<style>
/* ─── Reset & Base ──────────────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; }}

.block-container {{
    padding: 0.75rem 0.75rem 2rem !important;
    max-width: 100% !important;
}}

/* ─── Card ──────────────────────────────────────────────────── */
.dss-card {{
    background: {CARD_COLOR};
    border: 1px solid {BORDER_COLOR};
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 10px;
    width: 100%;
}}

.dss-card-title {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: {MUTED_COLOR};
    margin-bottom: 6px;
}}

.dss-card-value {{
    font-size: 28px;
    font-weight: 700;
    color: {TEXT_COLOR};
    line-height: 1.15;
    margin-bottom: 2px;
}}

.dss-card-sub {{
    font-size: 13px;
    color: {MUTED_COLOR};
    margin-top: 2px;
}}

/* ─── Action Badge ───────────────────────────────────────────── */
.action-buy  {{ color: {BUY_COLOR};  font-weight: 800; }}
.action-sell {{ color: {SELL_COLOR}; font-weight: 800; }}
.action-hold {{ color: {HOLD_COLOR}; font-weight: 800; }}
.action-wait {{ color: {HOLD_COLOR}; font-weight: 800; }}
.action-info {{ color: {INFO_COLOR}; font-weight: 800; }}

/* ─── Decision Hero Card ─────────────────────────────────────── */
.hero-card {{
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 12px;
    text-align: center;
}}
.hero-card-buy  {{ background: {SUCCESS_BG}; border: 2px solid {BUY_COLOR}; }}
.hero-card-sell {{ background: {DANGER_BG};  border: 2px solid {SELL_COLOR}; }}
.hero-card-hold {{ background: #fffbeb;       border: 2px solid {HOLD_COLOR}; }}

.hero-action {{
    font-size: 36px;
    font-weight: 900;
    margin-bottom: 4px;
}}
.hero-confidence {{
    font-size: 15px;
    color: {MUTED_COLOR};
}}

/* ─── Progress Bar ───────────────────────────────────────────── */
.progress-wrap {{
    background: {BORDER_COLOR};
    border-radius: 99px;
    height: 8px;
    overflow: hidden;
    margin-top: 6px;
}}
.progress-fill {{
    height: 100%;
    border-radius: 99px;
    transition: width 0.4s ease;
}}

/* ─── Badge ──────────────────────────────────────────────────── */
.badge {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 99px;
    font-size: 12px;
    font-weight: 600;
    line-height: 1.6;
}}
.badge-buy  {{ background: #dcfce7; color: #15803d; }}
.badge-sell {{ background: #fee2e2; color: #b91c1c; }}
.badge-hold {{ background: #ffedd5; color: #c2410c; }}
.badge-info {{ background: #dbeafe; color: #1d4ed8; }}
.badge-muted{{ background: #f1f5f9; color: {MUTED_COLOR}; }}

/* ─── XAI Why Box ────────────────────────────────────────────── */
.why-box {{
    background: #f0f9ff;
    border-left: 3px solid {INFO_COLOR};
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    margin-bottom: 8px;
    font-size: 13px;
    color: {TEXT_COLOR};
    line-height: 1.6;
}}
.why-label {{
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: {INFO_COLOR};
    margin-bottom: 3px;
}}

/* ─── Brief Lines ────────────────────────────────────────────── */
.brief-box {{
    background: {CARD_COLOR};
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 10px;
}}
.brief-line {{
    font-size: 14px;
    color: {TEXT_COLOR};
    line-height: 1.7;
    padding: 2px 0;
}}
.brief-line::before {{
    content: "• ";
    color: {INFO_COLOR};
    font-weight: 700;
}}

/* ─── Engine Monitor Row ─────────────────────────────────────── */
.engine-row {{
    display: flex;
    align-items: center;
    padding: 10px 14px;
    border-bottom: 1px solid {BORDER_COLOR};
    font-size: 14px;
}}
.engine-row:last-child {{ border-bottom: none; }}
.engine-icon {{ font-size: 16px; margin-right: 10px; flex-shrink: 0; }}
.engine-name {{ flex: 1; font-weight: 500; color: {TEXT_COLOR}; }}
.engine-time {{ color: {MUTED_COLOR}; font-size: 13px; margin-right: 12px; }}
.engine-status-ok   {{ color: {BUY_COLOR};  font-weight: 700; font-size: 12px; }}
.engine-status-fail {{ color: {SELL_COLOR}; font-weight: 700; font-size: 12px; }}
.engine-error {{
    font-size: 11px;
    color: {SELL_COLOR};
    padding: 3px 14px 8px 40px;
}}

/* ─── Allocation Table ───────────────────────────────────────── */
.alloc-row {{
    display: flex;
    align-items: center;
    padding: 7px 0;
    border-bottom: 1px solid {BORDER_COLOR};
    gap: 8px;
}}
.alloc-row:last-child {{ border-bottom: none; }}
.alloc-ticker {{ width: 52px; font-weight: 700; font-size: 13px; color: {TEXT_COLOR}; }}
.alloc-bar-wrap {{ flex: 1; }}
.alloc-pct {{ width: 46px; text-align: right; font-size: 13px; color: {MUTED_COLOR}; }}
.alloc-delta-pos {{ width: 52px; text-align: right; font-size: 12px; color: {BUY_COLOR}; font-weight: 600; }}
.alloc-delta-neg {{ width: 52px; text-align: right; font-size: 12px; color: {SELL_COLOR}; font-weight: 600; }}
.alloc-delta-zero{{ width: 52px; text-align: right; font-size: 12px; color: {MUTED_COLOR}; }}

/* ─── Metric Grid ────────────────────────────────────────────── */
.metric-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 10px;
}}
.metric-cell {{
    background: {CARD_COLOR};
    border: 1px solid {BORDER_COLOR};
    border-radius: 10px;
    padding: 12px 14px;
}}
.metric-label {{
    font-size: 11px;
    color: {MUTED_COLOR};
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 4px;
}}
.metric-value {{
    font-size: 22px;
    font-weight: 700;
    color: {TEXT_COLOR};
}}
.metric-sub {{
    font-size: 11px;
    color: {MUTED_COLOR};
    margin-top: 2px;
}}

/* ─── Section Header ─────────────────────────────────────────── */
.section-hdr {{
    font-size: 13px;
    font-weight: 700;
    color: {MUTED_COLOR};
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin: 16px 0 8px;
    padding-bottom: 4px;
    border-bottom: 1px solid {BORDER_COLOR};
}}

/* ─── Divider ────────────────────────────────────────────────── */
.dss-divider {{
    height: 1px;
    background: {BORDER_COLOR};
    margin: 12px 0;
}}

/* ─── Status Pill ────────────────────────────────────────────── */
.status-healthy  {{ background: #dcfce7; color: #15803d; padding: 4px 12px; border-radius: 99px; font-size: 13px; font-weight: 700; display:inline-block; }}
.status-degraded {{ background: #ffedd5; color: #c2410c; padding: 4px 12px; border-radius: 99px; font-size: 13px; font-weight: 700; display:inline-block; }}
.status-critical {{ background: #fee2e2; color: #b91c1c; padding: 4px 12px; border-radius: 99px; font-size: 13px; font-weight: 700; display:inline-block; }}
.status-unknown  {{ background: #f1f5f9; color: {MUTED_COLOR}; padding: 4px 12px; border-radius: 99px; font-size: 13px; font-weight: 700; display:inline-block; }}

/* ─── Tab styling ─────────────────────────────────────────────── */
div[data-testid="stTabs"] button {{
    font-size: 13px !important;
    padding: 8px 6px !important;
}}

/* ─── Market Status Card ───────────────── */
.market-status-card {{
    background: {CARD_COLOR};
    border: 1px solid {BORDER_COLOR};
    border-radius: 10px;
    padding: 10px 16px;
    margin-bottom: 10px;
}}
.market-event-pill {{
    display: inline-block;
    font-size: 11px;
    background: #f0f9ff;
    color: #1d4ed8;
    padding: 2px 8px;
    border-radius: 99px;
    margin-right: 4px;
    margin-top: 4px;
}}

/* ─── Op Check List ─────────────────────── */
.op-check-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    font-size: 13px;
    border-bottom: 1px solid {BORDER_COLOR};
}}
.op-check-row:last-child {{ border-bottom: none; }}
.op-check-label {{ color: {TEXT_COLOR}; }}
.op-check-detail {{ font-size: 11px; color: {MUTED_COLOR}; margin-top: 1px; }}

/* ─── Mobile: Tab overflow scroll ────────────────── */
@media (max-width: 480px) {{
    div[data-testid="stTabs"] > div:first-child {{
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
    }}
    div[data-testid="stTabs"] > div:first-child::-webkit-scrollbar {{
        display: none;
    }}
    div[data-testid="stTabs"] button {{
        font-size: 11px !important;
        padding: 6px 4px !important;
        white-space: nowrap;
    }}
}}
</style>
"""


def inject_css() -> str:
    return _CSS


def action_class(action: str) -> str:
    return f"action-{action.lower()}"


def badge_class(action: str) -> str:
    a = action.upper()
    if a == "BUY":   return "badge-buy"
    if a == "SELL":  return "badge-sell"
    if a in ("HOLD", "WAIT"): return "badge-hold"
    return "badge-info"


def hero_class(action: str) -> str:
    a = action.upper()
    if a == "BUY":  return "hero-card hero-card-buy"
    if a == "SELL": return "hero-card hero-card-sell"
    return "hero-card hero-card-hold"


def progress_bar(value: float, max_val: float = 100.0, color: str = INFO_COLOR) -> str:
    pct = max(0.0, min(100.0, (value / max_val) * 100)) if max_val else 0.0
    return (
        f'<div class="progress-wrap">'
        f'<div class="progress-fill" style="width:{pct:.1f}%;background:{color};"></div>'
        f'</div>'
    )


def score_color(score: float) -> str:
    if score >= 65: return BUY_COLOR
    if score >= 45: return INFO_COLOR
    return SELL_COLOR
