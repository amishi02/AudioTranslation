"""P8-TEST-002/003: CascadedPipeline Strategy D + dedup + rate-limit."""

import asyncio

import pytest

from app.models.session import TranslationSession
from app.providers.mocks.mock_stt import MockSTTProvider
from app.providers.mocks.mock_translation import MockTranslationProvider
from app.providers.translation.opus import OpusTranslationProvider
from app.services.pipeline.cascaded import CascadedPipeline


class StubSTTProvider(MockSTTProvider):
    """Controllable STT returning queued raws."""

    def __init__(self, raws: list[dict]):
        super().__init__()
        self._queue = raws

    async def poll_events(self, session_id: str) -> list[dict]:
        if not self._queue:
            return []
        return [self._queue.pop(0)]


@pytest.mark.asyncio
async def test_strategy_d_final_always_translates():
    """P8-PIPE-006: final always emits even if same text as last partial."""
    stt = StubSTTProvider(
        [
            {"session_id": "s1", "segment_id": 1, "text": "Hello", "is_final": False},
            {"session_id": "s1", "segment_id": 1, "text": "Hello", "is_final": True},
        ]
    )
    trans = MockTranslationProvider()
    await stt.initialize()
    await trans.initialize()
    pipe = CascadedPipeline(stt, trans)
    session = TranslationSession(session_id="s1", source_language="en", target_language="hi")
    await pipe.start_session(session)
    ev1 = await pipe.poll_events("s1")
    # first partial -> transcript + translation
    assert any(e["type"] == "transcript" and e["status"] == "partial" for e in ev1)
    assert any(e["type"] == "translation" and e["status"] == "partial" for e in ev1)
    ev2 = await pipe.poll_events("s1")
    assert any(e["type"] == "translation" and e["status"] == "final" for e in ev2)


@pytest.mark.asyncio
async def test_dedup_identical_partial_no_reemit():
    """P8-PIPE-004: identical successive partials don't re-emit translation."""
    stt = StubSTTProvider(
        [
            {"session_id": "s2", "segment_id": 1, "text": "Hello my", "is_final": False},
            {"session_id": "s2", "segment_id": 1, "text": "Hello my", "is_final": False},
        ]
    )
    trans = MockTranslationProvider()
    await stt.initialize()
    await trans.initialize()
    pipe = CascadedPipeline(stt, trans)
    session = TranslationSession(session_id="s2", source_language="en", target_language="hi")
    await pipe.start_session(session)
    ev1 = await pipe.poll_events("s2")
    assert any(e["type"] == "translation" for e in ev1)
    # Second identical partial should be deduped or rate-limited -> no translation
    ev2 = await pipe.poll_events("s2")
    # ev2 should have transcript but no translation (dedup)
    assert any(e["type"] == "transcript" for e in ev2)
    assert not any(e["type"] == "translation" for e in ev2)


@pytest.mark.asyncio
async def test_rate_limit_partial():
    """P8-PIPE-005: partial rate limit ~250ms."""
    stt = StubSTTProvider(
        [
            {"session_id": "s3", "segment_id": 1, "text": "Hello", "is_final": False},
            {"session_id": "s3", "segment_id": 1, "text": "Hello my", "is_final": False},
        ]
    )
    trans = MockTranslationProvider()
    await stt.initialize()
    await trans.initialize()
    pipe = CascadedPipeline(stt, trans)
    session = TranslationSession(session_id="s3", source_language="en", target_language="hi")
    await pipe.start_session(session)
    ev1 = await pipe.poll_events("s3")
    assert any(e["type"] == "translation" for e in ev1)
    # immediate second poll should be rate-limited (since <250ms)
    ev2 = await pipe.poll_events("s3")
    assert not any(e["type"] == "translation" for e in ev2)
    # after sleep, should emit
    await asyncio.sleep(0.3)
    stt._queue.append({"session_id": "s3", "segment_id": 1, "text": "Hello my name", "is_final": False})
    ev3 = await pipe.poll_events("s3")
    assert any(e["type"] == "translation" for e in ev3)


@pytest.mark.asyncio
async def test_segment_id_status_alignment():
    """P8-TEST-002: transcript and translation share segment_id and status."""
    stt = StubSTTProvider(
        [
            {"session_id": "s4", "segment_id": 2, "text": "Next", "is_final": True},
        ]
    )
    trans = OpusTranslationProvider()
    await stt.initialize()
    await trans.initialize()
    pipe = CascadedPipeline(stt, trans)
    session = TranslationSession(session_id="s4", source_language="en", target_language="es")
    await pipe.start_session(session)
    evs = await pipe.poll_events("s4")
    tr = [e for e in evs if e["type"] == "transcript"][0]
    tl = [e for e in evs if e["type"] == "translation"][0]
    assert tr["segment_id"] == tl["segment_id"] == 2
    assert tr["status"] == tl["status"] == "final"
    assert tl["source_text"] == tr["text"]
