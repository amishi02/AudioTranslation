"""P7-TEST-001,006: faster-whisper provider lifecycle."""

import pytest

from app.providers.stt.whisper import WhisperSTTProvider


@pytest.mark.asyncio
async def test_whisper_provider_real_lifecycle():
    provider = WhisperSTTProvider()
    await provider.initialize()
    assert provider.is_ready() is True
    await provider.start_session("s1", "en")
    await provider.push_audio("s1", b"\x00" * 8000)
    events = await provider.poll_events("s1")
    assert isinstance(events, list)
    await provider.end_session("s1")
    assert "s1" not in provider._sessions


@pytest.mark.asyncio
async def test_whisper_unsupported_language_handling():
    provider = WhisperSTTProvider()
    await provider.initialize()
    await provider.start_session("s2", "xx_unknown")
    assert "s2" in provider._sessions
    await provider.end_session("s2")


@pytest.mark.asyncio
async def test_whisper_model_not_ready_before_init():
    provider = WhisperSTTProvider()
    # Force not ready state
    provider._ready = False
    await provider.start_session("s3", "en")
    assert provider.is_ready() is True
    await provider.end_session("s3")
