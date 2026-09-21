"""P7-TEST-001,006: faster-whisper provider lifecycle."""

import pytest

from app.providers.base import ModelError
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
    """P7-BE-007 / P7-TEST-006: unsupported lang -> UNSUPPORTED_LANGUAGE."""
    provider = WhisperSTTProvider()
    await provider.initialize()
    with pytest.raises(ModelError) as exc:
        await provider.start_session("s2", "xx_unknown")
    assert exc.value.code == "UNSUPPORTED_LANGUAGE"
    assert "s2" not in provider._sessions


@pytest.mark.asyncio
async def test_whisper_model_not_ready_before_init():
    provider = WhisperSTTProvider()
    # Force not ready state — poll/push should raise MODEL_NOT_READY
    provider._ready = False
    provider._model = None  # type: ignore[assignment]
    with pytest.raises(ModelError) as exc:
        await provider.push_audio("s3", b"\x00" * 8000)
    assert exc.value.code == "MODEL_NOT_READY"
    with pytest.raises(ModelError) as exc2:
        await provider.poll_events("s3")
    assert exc2.value.code == "MODEL_NOT_READY"


@pytest.mark.asyncio
async def test_whisper_supported_languages():
    """P7-BE-007: en, hi, es, fr, de all accepted."""
    provider = WhisperSTTProvider()
    await provider.initialize()
    for lang in ["en", "hi", "es", "fr", "de"]:
        sid = f"s-{lang}"
        await provider.start_session(sid, lang)
        assert sid in provider._sessions
        await provider.end_session(sid)
