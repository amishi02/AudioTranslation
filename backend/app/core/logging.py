"""Structured logging for the backend.

Provides ``configure_logging(level)`` with a formatter that includes
``asctime``, ``levelname``, ``name`` and ``message`` and leaves room for
``session_id`` via ``extra`` / ``LoggerAdapter``.

Policy: raw audio bytes must NEVER be logged (see ``docs/trd.md`` and
``AGENTS.md``). Callers should log only byte lengths / counts.
"""

from __future__ import annotations

import logging
import sys
from typing import Final

DEFAULT_FORMAT: Final[str] = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging with structured formatter.

    Safe to call multiple times — re-applies handler only if not present
    or level changed.
    """
    numeric = getattr(logging, level.upper(), logging.INFO)
    # Ensure we use a single StreamHandler to avoid duplicate lines on reload.
    root = logging.getLogger()
    # Clear existing StreamHandlers added by prior configure_logging calls
    # (keep other handlers such as pytest's).
    for handler in list(root.handlers):
        if isinstance(handler, logging.StreamHandler) and getattr(
            handler, "_is_app_logging", False
        ):
            root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler._is_app_logging = True  # type: ignore[attr-defined]
    handler.setLevel(numeric)
    formatter = logging.Formatter(fmt=DEFAULT_FORMAT, datefmt=DATE_FORMAT)
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(numeric)

    # Quiet noisy third-party loggers slightly in development unless DEBUG.
    if numeric > logging.DEBUG:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Convenience wrapper — returns ``logging.getLogger(name)``."""
    return logging.getLogger(name)
