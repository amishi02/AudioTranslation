"""P10-TEST-001: error taxonomy matrix."""

from app.schemas.errors import ErrorCode, ERROR_RETRYABLE, ERROR_MESSAGES, is_retryable, safe_message


def test_all_codes_have_retryable_and_message():
    for code in ErrorCode:
        assert code.value in ERROR_RETRYABLE
        assert code.value in ERROR_MESSAGES
        assert isinstance(ERROR_RETRYABLE[code.value], bool)
        assert isinstance(ERROR_MESSAGES[code.value], str)


def test_retryable_set():
    assert is_retryable(ErrorCode.MODEL_NOT_READY.value) is True
    assert is_retryable(ErrorCode.SESSION_TIMEOUT.value) is True
    assert is_retryable(ErrorCode.RATE_LIMITED.value) is True
    assert is_retryable(ErrorCode.UNSUPPORTED_LANGUAGE.value) is False
    assert is_retryable(ErrorCode.INVALID_MESSAGE.value) is False
    assert is_retryable(ErrorCode.INTERNAL_ERROR.value) is False


def test_safe_message_fallback():
    assert safe_message(ErrorCode.INTERNAL_ERROR.value) == ERROR_MESSAGES[ErrorCode.INTERNAL_ERROR.value]
    assert safe_message("UNKNOWN_CODE", fallback="fallback") == "fallback"


def test_error_event_includes_retryable():
    from app.schemas.websocket import ErrorEvent

    ev = ErrorEvent(code="RATE_LIMITED", message="Too many", retryable=True, session_id="abc")
    d = ev.model_dump()
    assert d["code"] == "RATE_LIMITED"
    assert d["retryable"] is True
    assert d["session_id"] == "abc"
