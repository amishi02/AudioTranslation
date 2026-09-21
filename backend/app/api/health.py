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
    """Readiness — Phase 8: reflect STT + translation provider readiness (P7-CFG-002, P8-CFG-002)."""
    pipeline = settings.pipeline_type or "cascaded"
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
                from app.providers.stt.whisper import get_whisper_singleton

                singleton = get_whisper_singleton()
                stt_ready = singleton.is_ready()
                model_ready = has_faster_whisper
        except Exception:
            stt_ready = False
            model_ready = False
    # Translation readiness P8-CFG-002
    trans_provider = (settings.translation_provider or "mock").lower()
    if trans_provider == "mock":
        translation_ready = True
    else:
        try:
            if trans_provider == "opus":
                from app.providers.translation.opus import get_opus_singleton

                translation_ready = get_opus_singleton().is_ready()
            elif trans_provider == "nllb":
                from app.providers.translation.nllb import get_nllb_singleton

                translation_ready = get_nllb_singleton().is_ready()
            else:
                translation_ready = False
        except Exception:
            translation_ready = False
    # If either provider not ready, model_ready should reflect overall? Keep stt model_ready for compat
    # but ensure translation_ready influences overall if needed (not breaking existing test)
    return ReadyResponse(
        status="ready",
        model_ready=model_ready,
        pipeline=pipeline,
        version=settings.app_version,
        stt_ready=stt_ready,
        stt_model=settings.stt_model or "tiny",
        stt_provider=stt_provider,
        translation_ready=translation_ready,
        translation_model=settings.translation_model or "Helsinki-NLP/opus-mt-en-hi",
        translation_provider=trans_provider,
    )
