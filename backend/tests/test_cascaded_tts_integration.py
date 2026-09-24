"""P9-TEST-002/004: Cascaded TTS wiring emits audio triple on final only."""

import io
import wave

import pytest

from app.models.session import TranslationSession
from app.providers.mocks.mock_stt import MockSTTProvider
from app.providers.mocks.mock_translation import MockTranslationProvider
from app.providers.mocks.mock_tts import MockTTSProvider
from app.providers.tts.piper import PiperTTSProvider
from app.services.pipeline.cascaded import CascadedPipeline


class StubSTT(MockSTTProvider):
    def __init__(self, raws):
        super().__init__()
        self._queue = raws

    async def poll_events(self, session_id: str) -> list[dict]:
        if not self._queue:
            return []
        return [self._queue.pop(0)]


@pytest.mark.asyncio
async def test_cascaded_tts_final_only():
    """P9-TTS-004 stable-only: synthesize only final."""
    stt = StubSTT(
        [
            {"session_id": "s1", "segment_id": 1, "text": "Hello", "is_final": False},
            {"session_id": "s1", "segment_id": 1, "text": "Hello world", "is_final": True},
        ]
    )
    trans = MockTranslationProvider()
    tts = MockTTSProvider()
    await stt.initialize()
    await trans.initialize()
    await tts.initialize()
    pipe = CascadedPipeline(stt, trans, tts)
    session = TranslationSession(session_id="s1", source_language="en", target_language="hi")
    await pipe.start_session(session)
    ev1 = await pipe.poll_events("s1")
    # First partial -> transcript + translation, no audio
    assert any(e["type"] == "transcript" for e in ev1)
    assert any(e["type"] == "translation" for e in ev1)
    assert not any(e.get("type") == "audio.output.start" for e in ev1 if isinstance(e, dict))
    ev2 = await pipe.poll_events("s1")
    # Final -> transcript + translation + audio triple
    assert any(e.get("type") == "audio.output.start" for e in ev2 if isinstance(e, dict))
    assert any(isinstance(e, (bytes, bytearray)) for e in ev2)
    assert any(e.get("type") == "audio.output.end" for e in ev2 if isinstance(e, dict))
    # Check audio is WAV
    audio_bytes = [e for e in ev2 if isinstance(e, (bytes, bytearray))][0]
    assert audio_bytes.startswith(b"RIFF")


@pytest.mark.asyncio
async def test_cascaded_tts_partial_no_audio():
    stt = StubSTT(
        [
            {"session_id": "s2", "segment_id": 1, "text": "Hello", "is_final": False},
            {"session_id": "s2", "segment_id": 1, "text": "Hello my", "is_final": False},
        ]
    )
    trans = MockTranslationProvider()
    tts = PiperTTSProvider()
    await stt.initialize()
    await trans.initialize()
    await tts.initialize()
    pipe = CascadedPipeline(stt, trans, tts)
    session = TranslationSession(session_id="s2", source_language="en", target_language="hi")
    await pipe.start_session(session)
    ev1 = await pipe.poll_events("s2")
    assert not any(isinstance(e, (bytes, bytearray)) for e in ev1)
    # Even second partial should not produce audio (stable-only)
    ev2 = await pipe.poll_events("s2")
    assert not any(isinstance(e, (bytes, bytearray)) for e in ev2)


@pytest.mark.asyncio
async def test_cascaded_tts_piper_fallback():
    stt = StubSTT([{"session_id": "s3", "segment_id": 1, "text": "Hello", "is_final": True}])
    trans = MockTranslationProvider()
    tts = PiperTTSProvider()
    await stt.initialize()
    await trans.initialize()
    await tts.initialize()
    pipe = CascadedPipeline(stt, trans, tts)
    session = TranslationSession(session_id="s3", source_language="en", target_language="hi")
    await pipe.start_session(session)
    evs = await pipe.poll_events("s3")
    audio = [e for e in evs if isinstance(e, (bytes, bytearray))][0]
    with wave.open(io.BytesIO(audio), "rb") as wf:
        assert wf.getnchannels() == 1
