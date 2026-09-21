"""Pipeline factory — P6-PIPE-004."""

from __future__ import annotations

from app.core.config import settings
from app.providers.mocks.mock_stt import MockSTTProvider
from app.providers.mocks.mock_translation import MockTranslationProvider
from app.providers.mocks.mock_unified import MockUnifiedProvider
from app.services.pipeline.base import TranslationPipeline
from app.services.pipeline.cascaded import CascadedPipeline
from app.services.pipeline.unified import UnifiedPipeline


def create_pipeline(pipeline_type: str | None = None) -> TranslationPipeline:
    """Select pipeline based on settings.pipeline_type or explicit arg."""
    pt = (pipeline_type or settings.pipeline_type or "cascaded").lower()
    if pt == "cascaded":
        stt_provider_name = (settings.stt_provider or "whisper").lower()
        if stt_provider_name in ("whisper", "faster_whisper", "faster-whisper"):
            from app.providers.stt.whisper import get_whisper_singleton

            stt = get_whisper_singleton()
        elif stt_provider_name == "mock":
            stt = MockSTTProvider()
        else:
            raise ValueError(f"UNSUPPORTED_STT_PROVIDER: {stt_provider_name}")
        trans = MockTranslationProvider()
        return CascadedPipeline(stt, trans)
    if pt == "unified":
        unified = MockUnifiedProvider()
        return UnifiedPipeline(unified)
    raise ValueError(f"UNSUPPORTED_PIPELINE: {pt} not supported")


async def create_and_init_pipeline(
    pipeline_type: str | None = None,
) -> TranslationPipeline:
    """Helper to create and initialize mock providers."""
    pipeline = create_pipeline(pipeline_type)
    # Initialize underlying providers
    if isinstance(pipeline, CascadedPipeline):
        await pipeline._stt.initialize()  # type: ignore[attr-defined]
        await pipeline._translation.initialize()  # type: ignore[attr-defined]
    elif isinstance(pipeline, UnifiedPipeline):
        await pipeline._unified.initialize()  # type: ignore[attr-defined]
    return pipeline
