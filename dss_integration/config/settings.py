"""
dss_integration/config/settings.py
전역 설정 — 엔진 순서, 경로, 타임아웃
"""
from __future__ import annotations
import os

# ── Project Paths ──────────────────────────────────────────────────────
PROJECT_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINES_ROOT   = os.path.join(os.path.dirname(PROJECT_ROOT), "engines")
OUTPUT_DIR     = PROJECT_ROOT
LOG_DIR        = os.path.join(PROJECT_ROOT, "logs")
RESULT_JSON    = os.path.join(PROJECT_ROOT, "dss_result.json")

# ── Engine Order ───────────────────────────────────────────────────────
# 이 순서를 변경하면 안 됨 (Engine 간 의존성)
ENGINE_ORDER = [
    "Macro Engine",
    "Breadth Engine",
    "Relative Strength Engine",
    "Rotation Engine",
    "Portfolio Decision Engine",
    "Portfolio Optimizer Engine",
    "Validation Engine",
    "Dashboard Engine",
]

# ── Engine Criticality (False = 실패해도 파이프라인 계속) ──────────────
ENGINE_CRITICAL = {
    "Macro Engine":               True,
    "Breadth Engine":             True,
    "Relative Strength Engine":   True,
    "Rotation Engine":            True,
    "Portfolio Decision Engine":  True,
    "Portfolio Optimizer Engine": True,
    "Validation Engine":          False,  # Validation은 실패해도 계속
    "Dashboard Engine":           False,
}

# ── Default Market Tickers ─────────────────────────────────────────────
SECTOR_TICKERS = [
    "XLK", "XLC", "XLY", "XLF", "XLI",
    "XLE", "XLB", "XLV", "XLP", "XLU", "XLRE",
]
BENCHMARK_TICKERS = ["SPY", "QQQ"]

# ── Synthetic Data Config ──────────────────────────────────────────────
SYNTHETIC_PRICE_BARS    = 400
SYNTHETIC_DECISION_BARS = 380
SYNTHETIC_RANDOM_SEED   = 42

# ── Risk ───────────────────────────────────────────────────────────────
RISK_FREE_RATE = 0.045
INITIAL_CAPITAL = 100_000.0

# ── Logging ────────────────────────────────────────────────────────────
LOG_LEVEL  = "INFO"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
LOG_FILE   = os.path.join(LOG_DIR, "dss.log")
