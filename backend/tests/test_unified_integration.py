"""P9-TEST-003/005: Unified pipeline mock + WS integration."""

import time

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.models.session import TranslationSession
from app.providers.mocks.mock_unified import MockUnifiedProvider
from app.services.pipeline.unified import UnifiedPipeline


@pytest.mark.asyncio
async def test_unified_pipeline_mock():
    provider = MockUnifiedProvider()
    await provider.initialize()
    pipe = UnifiedPipeline(provider)
    session = TranslationSession(session_id="u1", source_language="en", target_language="hi")
    await pipe.start_session(session)
    await pipe.push_audio("u1", b"\x00\x01" * 960)
    await pipe.push_audio("u1", b"\x00\x01" * 960)
    evs = await pipe.poll_events("u1")
    assert any(e["type"] == "transcript" for e in evs)
    assert any(e["type"] == "translation" for e in evs)
    # Unified mock does not yet produce audio, so no audio markers
    assert not any(e.get("type") == "audio.output.start" for e in evs if isinstance(e, dict))


def test_ws_unified_mock():
    orig_pipe = settings.pipeline_type
    orig_unified = settings.unified_provider
    try:
        settings.pipeline_type = "unified"  # type: ignore[assignment]
        settings.unified_provider = "mock"  # type: ignore[assignment]
        client = TestClient(app)
        with client.websocket_connect("/ws/v1/translate") as ws:
            ws.send_json({"type": "start", "source_language": "en", "target_language": "hi"})
            ready = ws.receive_json()
            assert ready["type"] == "session.ready"
            for _ in range(5):
                ws.send_bytes(b"\x00\x01" * 960)
            # Collect transcript/translation
            got_transcript = False
            got_translation = False
            start = time.time()
            while time.time() - start < 2:
                try:
                    m = ws.receive_json()
                except Exception:
                    break
                if m.get("type") == "transcript":
                    got_transcript = True
                if m.get("type") == "translation":
                    got_translation = True
                if got_transcript and got_translation:
                    break
                if m.get("type") == "error":
                    raise AssertionError(f"unexpected error {m}")
            assert got_transcript
            assert got_translation
            ws.send_json({"type": "stop"})
            # Drain
            for _ in range(10):
                try:
                    m = ws.receive_json()
                    if m.get("type") == "session.ended":
                        break
                except Exception:
                    break
    finally:
        settings.pipeline_type = orig_pipe  # type: ignore[assignment]
        settings.unified_provider = orig_unified  # type: ignore[assignment]


def test_ws_invalid_pipeline():
    """P9-TEST-007: invalid PIPELINE_TYPE yields UNSUPPORTED_PIPELINE error."""
    orig = settings.pipeline_type
    try:
        settings.pipeline_type = "invalid_pipe"  # type: ignore[assignment]
        client = TestClient(app)
        with client.websocket_connect("/ws/v1/translate") as ws:
            ws.send_json({"type": "start", "source_language": "en", "target_language": "hi"})
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert "UNSUPPORTED_PIPELINE" in msg["code"]
    finally:
        settings.pipeline_type = orig  # type: ignore[assignment]
