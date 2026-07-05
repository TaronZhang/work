"""Centralized logging with rotation and file storage."""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "log"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── Formatters ──────────────────────────────────────────

_detail_fmt = logging.Formatter(
    "[%(asctime)s] %(levelname)-7s %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_brief_fmt = logging.Formatter("%(levelname)-7s %(message)s")


def setup_logger(
    name: str,
    level: int = logging.INFO,
) -> logging.Logger:
    """Create a logger that writes to both file and console.

    - File: ``log/{name}.log`` with rotation (10 MB × 5 backups)
    - Console: brief format for readability
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # File handler with rotation
    log_file = LOG_DIR / f"{name}.log"
    fh = RotatingFileHandler(
        str(log_file), maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    fh.setLevel(level)
    fh.setFormatter(_detail_fmt)
    logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(_brief_fmt)
    logger.addHandler(ch)

    return logger


# ── Application-wide loggers ────────────────────────────

# Main app logger
app_log = setup_logger("app")

# API access log (separate file for request tracing)
access_log = setup_logger("access")

# Error log (all errors go here regardless of source)
error_log = setup_logger("error", logging.WARNING)


def log_request(method: str, path: str, status: int, detail: str = "") -> None:
    """Log an API request."""
    access_log.info(f"{method:6s} {status} {path}" + (f" | {detail}" if detail else ""))


def log_error(source: str, error: str, extra: dict | None = None) -> None:
    """Log an error with optional structured context."""
    ctx = ""
    if extra:
        ctx = " | " + " ".join(f"{k}={v}" for k, v in extra.items())
    error_log.error(f"[{source}] {error}{ctx}")
