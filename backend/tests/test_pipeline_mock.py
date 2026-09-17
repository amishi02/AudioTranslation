"""P6-TEST-002/003: Pipeline mock integration."""

import pytest

from app.services.pipeline.factory import create_and_init_pipeline


@pytest.mark.asyncio
async def test_cascaded_pipeline_mock(monkeypatch):
    monkeypatch.setattr("app.services.pipeline.factory.settings.stt_provider", "mock")
    pipeline = await create_and_init_pipeline("cascaded")
    assert pipeline.is_ready()
    # Create a fake session
    from app.models.session import TranslationSession

    session = TranslationSession(
        session_id="test1", source_language="en", target_language="hi"
    )
    await pipeline.start_session(session)
    await pipeline.push_audio("test1", b"\x00\x01" * 960)
    await pipeline.push_audio("test1", b"\x00\x01" * 960)
    events = await pipeline.poll_events("test1")
    # Should have transcript + translation
    assert any(e["type"] == "transcript" for e in events)
    assert any(e["type"] == "translation" for e in events)
    await pipeline.end_session("test1")


@pytest.mark.asyncio
async def test_unified_pipeline_mock():
    pipeline = await create_and_init_pipeline("unified")
    assert pipeline.is_ready()
    from app.models.session import TranslationSession

    session = TranslationSession(
        session_id="test2", source_language="en", target_language="hi"
    )
    await pipeline.start_session(session)
    await pipeline.push_audio("test2", b"\x00\x01" * 960)
    events = await pipeline.poll_events("test2")
    assert any(e["type"] == "transcript" for e in events)
    assert any(e["type"] == "translation" for e in events)
    await pipeline.end_session("test2")


@pytest.mark.asyncio
async def test_pipeline_factory_invalid():
    from app.services.pipeline.factory import create_pipeline

    try:
        create_pipeline("invalid")
        raise AssertionError("Should have raised")
    except ValueError as e:
        assert "UNSUPPORTED_PIPELINE" in str(e)
