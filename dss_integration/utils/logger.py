"""
dss_integration/utils/logger.py
구조화 로깅 — 콘솔 + 파일 동시 출력
"""
from __future__ import annotations
import logging
import os
import sys
from typing import Optional


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """Logger 반환. 최초 호출 시 콘솔 + 파일 핸들러 설정."""
    from dss_integration.config.settings import LOG_DIR, LOG_FILE, LOG_FORMAT, LOG_LEVEL

    log_level = getattr(logging, (level or LOG_LEVEL).upper(), logging.INFO)
    logger    = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(log_level)
    fmt = logging.Formatter(LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(log_level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        from logging.handlers import RotatingFileHandler
        fh = RotatingFileHandler(
            LOG_FILE,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        fh.setLevel(log_level)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError:
        pass

    logger.propagate = False
    return logger
