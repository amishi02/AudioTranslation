"""P5-TEST-005: Backend audio streaming — bounded queue + backpressure."""

from fastapi.testclient import TestClient

from app.main import app


def test_audio_spam_no_crash_and_backpressure():
    """Spam 100 binary frames rapidly — should not crash, queue handles."""
    client = TestClient(app)
    with client.websocket_connect("/ws/v1/translate") as ws:
        ws.send_json(
            {"type": "start", "source_language": "en", "target_language": "hi"}
        )
        msg = ws.receive_json()
        assert msg["type"] == "session.ready"

        # Flood queue (max 64) with 100 frames of 1920 bytes each
        for _ in range(100):
            ws.send_bytes(b"\x00\x01" * 960)

        # Should still be able to stop; maybe some RATE_LIMITED errors interleaved
        # Drain any pending errors before stop
        # Try to collect up to 5 messages that might be RATE_LIMITED
        # Use try to avoid blocking
        ws.send_json({"type": "stop"})
        # The next message should be session.ended (maybe after some RATE_LIMITED)
        # Collect until ended or error
        found_ended = False
        for _ in range(10):
            try:
                m = ws.receive_json()
                if m.get("type") == "session.ended":
                    found_ended = True
                    break
                # If RATE_LIMITED, that's expected
                if m.get("code") == "RATE_LIMITED":
                    continue
            except Exception:
                break
        assert found_ended, "Expected session.ended after flood"


def test_audio_invalid_frames():
    """P5-BE-001: invalid frames return INVALID_AUDIO_DATA without disconnect."""
    client = TestClient(app)
    with client.websocket_connect("/ws/v1/translate") as ws:
        ws.send_json(
            {"type": "start", "source_language": "en", "target_language": "hi"}
        )
        ws.receive_json()
        # Odd length
        ws.send_bytes(b"\x01\x02\x03")
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "INVALID_AUDIO_DATA"
        # Empty frame
        ws.send_bytes(b"")
        msg2 = ws.receive_json()
        assert msg2["type"] == "error"
        assert msg2["code"] == "INVALID_AUDIO_DATA"
        # Oversize
        ws.send_bytes(b"\x00" * 70000)
        msg3 = ws.receive_json()
        assert msg3["type"] == "error"
        assert msg3["code"] == "INVALID_AUDIO_DATA"
        # Still able to stop
        ws.send_json({"type": "stop"})
        ended = ws.receive_json()
        assert ended["type"] == "session.ended"
