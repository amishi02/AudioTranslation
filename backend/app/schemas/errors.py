"""Central error taxonomy — P10-ERR-001.

Enumerates all WS/HTTP error codes with retryable flag and safe user messages.
No stack traces or internal model names are exposed via these messages.
"""

from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    INVALID_MESSAGE = "INVALID_MESSAGE"
    INVALID_SESSION_CONFIG = "INVALID_SESSION_CONFIG"
    UNSUPPORTED_LANGUAGE = "UNSUPPORTED_LANGUAGE"
    UNSUPPORTED_PIPELINE = "UNSUPPORTED_PIPELINE"
    UNSUPPORTED_AUDIO_FORMAT = "UNSUPPORTED_AUDIO_FORMAT"
    INVALID_AUDIO_DATA = "INVALID_AUDIO_DATA"
    MODEL_NOT_READY = "MODEL_NOT_READY"
    MODEL_ERROR = "MODEL_ERROR"
    SESSION_ERROR = "SESSION_ERROR"
    SESSION_TIMEOUT = "SESSION_TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# retryable: whether frontend should offer Try Again
ERROR_RETRYABLE: dict[str, bool] = {
    ErrorCode.INVALID_MESSAGE: False,
    ErrorCode.INVALID_SESSION_CONFIG: False,
    ErrorCode.UNSUPPORTED_LANGUAGE: False,
    ErrorCode.UNSUPPORTED_PIPELINE: False,
    ErrorCode.UNSUPPORTED_AUDIO_FORMAT: False,
    ErrorCode.INVALID_AUDIO_DATA: False,
    ErrorCode.MODEL_NOT_READY: True,
    ErrorCode.MODEL_ERROR: False,
    ErrorCode.SESSION_ERROR: False,
    ErrorCode.SESSION_TIMEOUT: True,
    ErrorCode.RATE_LIMITED: True,
    ErrorCode.INTERNAL_ERROR: False,
}

# Safe user-facing messages — never leak model names or stacks
ERROR_MESSAGES: dict[str, str] = {
    ErrorCode.INVALID_MESSAGE: "Invalid message format.",
    ErrorCode.INVALID_SESSION_CONFIG: "Invalid session configuration.",
    ErrorCode.UNSUPPORTED_LANGUAGE: "Selected language pair is not supported.",
    ErrorCode.UNSUPPORTED_PIPELINE: "Pipeline not available.",
    ErrorCode.UNSUPPORTED_AUDIO_FORMAT: "Unsupported audio format. Expected PCM S16LE mono 16 kHz.",
    ErrorCode.INVALID_AUDIO_DATA: "Invalid audio data.",
    ErrorCode.MODEL_NOT_READY: "Model is still loading. Please try again.",
    ErrorCode.MODEL_ERROR: "Processing error. Please try again.",
    ErrorCode.SESSION_ERROR: "Session error.",
    ErrorCode.SESSION_TIMEOUT: "Session timed out due to inactivity.",
    ErrorCode.RATE_LIMITED: "Too many requests. Please slow down.",
    ErrorCode.INTERNAL_ERROR: "Internal server error.",
}


def is_retryable(code: str) -> bool:
    return ERROR_RETRYABLE.get(code, False)


def safe_message(code: str, fallback: str | None = None) -> str:
    return ERROR_MESSAGES.get(code, fallback or "An error occurred.")
