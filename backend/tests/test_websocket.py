"""Phase 4 WebSocket tests — P4-TEST-001..006."""

from fastapi.testclient import TestClient

from app.main import app


def _connect():
    client = TestClient(app)
    return client.websocket_connect("/ws/v1/translate")


def test_ws_valid_start_returns_ready():
    """P4-TEST-001: valid session.start -> session.ready."""
    with _connect() as ws:
        ws.send_json(
            {"type": "start", "source_language": "en", "target_language": "hi"}
        )
        msg = ws.receive_json()
        assert msg["type"] == "session.ready"
        assert "session_id" in msg
        assert msg["source_language"] == "en"
        assert msg["target_language"] == "hi"
        # cleanup
        ws.send_json({"type": "stop"})
        ended = ws.receive_json()
        assert ended["type"] == "session.ended"


def test_ws_invalid_start_identical_languages():
    """P4-TEST-002: identical languages -> UNSUPPORTED_LANGUAGE."""
    with _connect() as ws:
        ws.send_json(
            {"type": "start", "source_language": "en", "target_language": "en"}
        )
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "UNSUPPORTED_LANGUAGE"


def test_ws_invalid_start_missing_fields():
    """P4-TEST-002 variant: missing target -> INVALID_SESSION_CONFIG."""
    with _connect() as ws:
        ws.send_json({"type": "start", "source_language": "en"})
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] in ("INVALID_SESSION_CONFIG", "INVALID_MESSAGE")


def test_ws_binary_audio_accepted():
    """P4-TEST-003: binary frames accepted and queued (no crash)."""
    with _connect() as ws:
        ws.send_json(
            {"type": "start", "source_language": "en", "target_language": "hi"}
        )
        ready = ws.receive_json()
        assert ready["type"] == "session.ready"
        # Send 5 valid audio frames (960*2 bytes = 1920)
        for _ in range(5):
            ws.send_bytes(b"\x00\x01" * 960)
        # Stop should still work
        ws.send_json({"type": "stop"})
        ended = ws.receive_json()
        assert ended["type"] == "session.ended"


def test_ws_stop_and_ended():
    """P4-TEST-004: session.stop -> session.ended; subsequent audio rejected."""
    with _connect() as ws:
        ws.send_json(
            {"type": "start", "source_language": "en", "target_language": "hi"}
        )
        ws.receive_json()
        ws.send_json({"type": "stop"})
        ended = ws.receive_json()
        assert ended["type"] == "session.ended"
        # After stop, sending audio without active session should error
        ws.send_bytes(b"\x00\x01" * 960)
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "SESSION_ERROR"


def test_ws_malformed_and_oversize():
    """P4-TEST-005: malformed JSON and oversize handling."""
    with _connect() as ws:
        # Malformed JSON
        ws.send_text("not json {")
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "INVALID_MESSAGE"
        # Oversize audio frame > max
        ws.send_json(
            {"type": "start", "source_language": "en", "target_language": "hi"}
        )
        ws.receive_json()
        oversize = b"\x00" * 70000  # >65536
        ws.send_bytes(oversize)
        msg2 = ws.receive_json()
        assert msg2["type"] == "error"
        assert msg2["code"] == "INVALID_AUDIO_DATA"
        # Odd length
        ws.send_bytes(b"\x00\x01\x02")
        msg3 = ws.receive_json()
        assert msg3["type"] == "error"
        assert msg3["code"] == "INVALID_AUDIO_DATA"
        ws.send_json({"type": "stop"})
        ws.receive_json()


def test_ws_disconnect_cleanup():
    """P4-TEST-006: disconnect triggers cleanup (no crash on reconnect)."""
    client = TestClient(app)
    with client.websocket_connect("/ws/v1/translate") as ws:
        ws.send_json(
            {"type": "start", "source_language": "en", "target_language": "hi"}
        )
        msg = ws.receive_json()
        assert msg["type"] == "session.ready"
        sid = msg["session_id"]
        # Disconnect by exiting context without stop — server should cleanup
    # Reconnect and ensure new session can start (proves old cleaned)
    with client.websocket_connect("/ws/v1/translate") as ws2:
        ws2.send_json(
            {"type": "start", "source_language": "en", "target_language": "hi"}
        )
        msg2 = ws2.receive_json()
        assert msg2["type"] == "session.ready"
        assert msg2["session_id"] != sid
        ws2.send_json({"type": "stop"})
        ws2.receive_json()
