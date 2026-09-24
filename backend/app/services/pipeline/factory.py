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
        trans_provider_name = (settings.translation_provider or "mock").lower()
        if trans_provider_name == "opus":
            from app.providers.translation.opus import get_opus_singleton

            trans = get_opus_singleton()
        elif trans_provider_name == "nllb":
            from app.providers.translation.nllb import get_nllb_singleton

            trans = get_nllb_singleton()
        elif trans_provider_name == "mock":
            trans = MockTranslationProvider()
        else:
            raise ValueError(f"UNSUPPORTED_TRANSLATION_PROVIDER: {trans_provider_name}")
        # TTS provider P9-PIPE-006 gating: only load when cascaded (avoid heavy in unified)
        tts_provider_name = (settings.tts_provider or "mock").lower()
        if tts_provider_name == "piper":
            from app.providers.tts.piper import get_piper_singleton

            tts = get_piper_singleton()
        elif tts_provider_name in ("coqui", "xtts", "vits"):
            # Coqui stub falls back to piper for Phase 9
            from app.providers.tts.piper import get_piper_singleton

            tts = get_piper_singleton()
        elif tts_provider_name == "mock":
            from app.providers.mocks.mock_tts import MockTTSProvider

            tts = MockTTSProvider()
        else:
            raise ValueError(f"UNSUPPORTED_TTS_PROVIDER: {tts_provider_name}")
        return CascadedPipeline(stt, trans, tts)
    if pt == "unified":
        # Gate unified model load on PIPELINE_TYPE==unified (P9-PIPE-006)
        unified_provider_name = (settings.unified_provider or "mock").lower()
        if unified_provider_name in ("seamless", "seamless-m4t", "seamless_streaming"):
            from app.providers.speech_translation.seamless import get_seamless_singleton

            unified = get_seamless_singleton()
        elif unified_provider_name == "mock":
            unified = MockUnifiedProvider()
        else:
            raise ValueError(f"UNSUPPORTED_UNIFIED_PROVIDER: {unified_provider_name}")
        return UnifiedPipeline(unified)
    raise ValueError(f"UNSUPPORTED_PIPELINE: {pt} not supported")


async def create_and_init_pipeline(
    pipeline_type: str | None = None,
) -> TranslationPipeline:
    """Helper to create and initialize providers."""
    pipeline = create_pipeline(pipeline_type)
    # Initialize underlying providers
    if isinstance(pipeline, CascadedPipeline):
        await pipeline._stt.initialize()  # type: ignore[attr-defined]
        await pipeline._translation.initialize()  # type: ignore[attr-defined]
        if getattr(pipeline, "_tts", None) is not None:
            await pipeline._tts.initialize()  # type: ignore[attr-defined]
    elif isinstance(pipeline, UnifiedPipeline):
        await pipeline._unified.initialize()  # type: ignore[attr-defined]
    return pipeline
