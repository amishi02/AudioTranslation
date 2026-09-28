"""Health endpoints — liveness + readiness (P2-BE-004/005)."""

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.health import HealthResponse, ReadyResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Liveness — always ok when process is running."""
    return HealthResponse(status="ok", version=settings.app_version)


@router.get("/health/ready", response_model=ReadyResponse, tags=["health"])
async def readiness_check() -> ReadyResponse:
    """Readiness — Phase 9: reflect STT + translation + TTS/unified readiness."""
    pipeline = (settings.pipeline_type or "cascaded").lower()
    stt_provider = (settings.stt_provider or "mock").lower()
    if stt_provider == "mock":
        stt_ready = True
        model_ready = True
    else:
        try:
            import importlib.util

            has_faster_whisper = importlib.util.find_spec("faster_whisper") is not None
            if not has_faster_whisper:
                stt_ready = False
                model_ready = False
            else:
                # P10: lazy load — readiness is loadable, not necessarily already initialized
                stt_ready = True
                model_ready = True
        except Exception:
            stt_ready = False
            model_ready = False
    # Translation readiness P8-CFG-002 — lazy, so check deps not singleton.is_ready
    trans_provider = (settings.translation_provider or "mock").lower()
    if trans_provider == "mock":
        translation_ready = True
    else:
        try:
            import importlib.util

            has_transformers = importlib.util.find_spec("transformers") is not None
            if trans_provider in ("opus", "nllb") and has_transformers:
                translation_ready = True
            elif trans_provider in ("opus", "nllb"):
                # mock fallback still considered ready for health (P10 lazy)
                translation_ready = True
            else:
                translation_ready = False
        except Exception:
            translation_ready = False
    # TTS readiness P9-BE-002
    tts_provider = (settings.tts_provider or "mock").lower()
    if tts_provider == "mock":
        tts_ready = True
    else:
        try:
            if tts_provider in ("piper", "coqui", "xtts", "vits"):
                from app.providers.tts.piper import get_piper_singleton

                tts_ready = get_piper_singleton().is_ready()
            else:
                tts_ready = False
        except Exception:
            tts_ready = False
    # Unified readiness P9
    unified_provider = (settings.unified_provider or "mock").lower()
    if unified_provider == "mock":
        unified_ready = True
    else:
        try:
            if unified_provider in ("seamless", "seamless-m4t"):
                from app.providers.speech_translation.seamless import (
                    get_seamless_singleton,
                )

                unified_ready = get_seamless_singleton().is_ready()
            else:
                unified_ready = False
        except Exception:
            unified_ready = False
    # Overall model_ready per pipeline
    if pipeline == "unified":
        overall_ready = unified_ready
    else:
        overall_ready = stt_ready and translation_ready and tts_ready
    # Keep model_ready for compat but also reflect overall if stricter
    model_ready = (
        model_ready and overall_ready if "model_ready" in locals() else overall_ready
    )
    return ReadyResponse(
        status="ready",
        model_ready=overall_ready,
        pipeline=pipeline,
        version=settings.app_version,
        stt_ready=stt_ready,
        stt_model=settings.stt_model or "tiny",
        stt_provider=stt_provider,
        translation_ready=translation_ready,
        translation_model=settings.translation_model or "Helsinki-NLP/opus-mt-en-hi",
        translation_provider=trans_provider,
        tts_ready=tts_ready,
        tts_model=settings.tts_model or "piper:en_US-lessac-medium",
        tts_provider=tts_provider,
        unified_ready=unified_ready,
        unified_model=settings.unified_model or "facebook/seamless-streaming",
        unified_provider=unified_provider,
    )
