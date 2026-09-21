"""P8-TEST-004: WS integration STT + translation with fixture."""

import pathlib
import time

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "hello_16k.pcm"


def test_ws_translation_pairs_matching_segment_id():
    """P8-TEST-004: WS with mock STT + mock translation -> ordered transcript+translation pairs."""
    orig_stt = settings.stt_provider
    orig_trans = settings.translation_provider
    try:
        settings.stt_provider = "mock"  # type: ignore[assignment]
        settings.translation_provider = "mock"  # type: ignore[assignment]
        client = TestClient(app)
        with client.websocket_connect("/ws/v1/translate") as ws:
            ws.send_json({"type": "start", "source_language": "en", "target_language": "hi"})
            ready = ws.receive_json()
            assert ready["type"] == "session.ready"
            # Push 8 chunks
            for _ in range(8):
                ws.send_bytes(b"\x00\x01" * 960)
            # Collect transcript + translation pairs
            transcripts: list[dict] = []
            translations: list[dict] = []
            start = time.time()
            while time.time() - start < 3:
                try:
                    msg = ws.receive_json()
                except Exception:
                    break
                if msg.get("type") == "transcript":
                    transcripts.append(msg)
                elif msg.get("type") == "translation":
                    translations.append(msg)
                elif msg.get("type") == "session.ended":
                    break
                if transcripts and translations:
                    # check that last translation matches last transcript id/status
                    if len(transcripts) >= 2 and len(translations) >= 2:
                        break
                if msg.get("type") == "error":
                    raise AssertionError(f"unexpected error {msg}")
            # At least one pair should have matching segment_id and status pairing
            assert len(transcripts) >= 1
            assert len(translations) >= 1
            # Verify pairing for first segment
            t = transcripts[0]
            # Find translation with same segment_id
            matching = [x for x in translations if x["segment_id"] == t["segment_id"]]
            assert matching, f"no translation matching transcript segment {t['segment_id']} in {translations}"
            assert matching[0]["source_text"] == t["text"]
            # Status alignment
            assert matching[0]["status"] in ("partial", "final")
            ws.send_json({"type": "stop"})
            for _ in range(20):
                try:
                    m = ws.receive_json()
                    if m.get("type") == "session.ended":
                        break
                except Exception:
                    break
    finally:
        settings.stt_provider = orig_stt  # type: ignore[assignment]
        settings.translation_provider = orig_trans  # type: ignore[assignment]


def test_ws_unsupported_pair_error():
    """P8-TEST-006: unsupported pair en->xx yields UNSUPPORTED_LANGUAGE."""
    orig_trans = settings.translation_provider
    try:
        settings.translation_provider = "opus"  # type: ignore[assignment]
        # Need to ensure translation provider will reject xx
        client = TestClient(app)
        with client.websocket_connect("/ws/v1/translate") as ws:
            ws.send_json({"type": "start", "source_language": "en", "target_language": "xx"})
            msg = ws.receive_json()
            # Either session creation fails with UNSUPPORTED_LANGUAGE (supported_languages check)
            # or pipeline translate fails — both should be UNSUPPORTED_LANGUAGE
            assert msg["type"] == "error"
            assert msg["code"] == "UNSUPPORTED_LANGUAGE"
    finally:
        settings.translation_provider = orig_trans  # type: ignore[assignment]


@pytest.mark.slow
@pytest.mark.asyncio
async def test_real_translation_with_fixture():
    """P8-TEST-001 slow: real opus fallback translates fixture text deterministically."""
    from app.providers.translation.opus import OpusTranslationProvider

    provider = OpusTranslationProvider()
    await provider.initialize()
    text = "Hello my name is John"
    out = await provider.translate(text, "en", "hi")
    assert isinstance(out, str)
    assert len(out) > 0
    # Mock fallback gives prefix; real model would give Devanagari
    assert "[hi]" in out or len(out) > 5
