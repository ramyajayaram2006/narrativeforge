"""
logger.py — NarrativeForge application logging
Import and call setup_logging() once at app startup (in app.py).

Usage:
    from logger import setup_logging, get_logger

    setup_logging()                        # call once at startup
    log = get_logger("narrativeforge.auth")
    log.info("User logged in", extra={"user": "alice"})
"""
import logging
import logging.handlers
import os
import sys


_CONFIGURED = False
_LOG_FILE   = os.environ.get("NARRATIVEFORGE_LOG_FILE", "narrativeforge.log")
_LOG_LEVEL  = os.environ.get("NARRATIVEFORGE_LOG_LEVEL", "INFO").upper()


def setup_logging() -> None:
    """Configure root logger. Safe to call multiple times (idempotent)."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = getattr(logging, _LOG_LEVEL, logging.INFO)

    fmt = logging.Formatter(
        fmt="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── Console handler (Streamlit shows stderr in terminal) ──────────────────
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(fmt)

    # ── Rotating file handler (max 5 MB × 3 backups) ─────────────────────────
    try:
        file_h = logging.handlers.RotatingFileHandler(
            _LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3,
            encoding="utf-8",
        )
        file_h.setLevel(level)
        file_h.setFormatter(fmt)
        handlers: list = [console, file_h]
    except OSError:
        # If we can't write to the log file (e.g., read-only filesystem), use console only
        handlers = [console]

    root = logging.getLogger()
    root.setLevel(level)
    for h in handlers:
        root.addHandler(h)

    # Silence chatty third-party loggers
    for noisy in ("urllib3", "httpx", "streamlit", "watchdog"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Call setup_logging() first."""
    return logging.getLogger(name)


# ── Module-level loggers used across the app ─────────────────────────────────
def auth_logger()  -> logging.Logger: return get_logger("narrativeforge.auth")
def db_logger()    -> logging.Logger: return get_logger("narrativeforge.db")
def ai_logger()    -> logging.Logger: return get_logger("narrativeforge.ai")
def app_logger()   -> logging.Logger: return get_logger("narrativeforge.app")
