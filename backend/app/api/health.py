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
    """Readiness — Phase 7: reflect STT provider readiness (P7-CFG-002)."""
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
                # stt_ready is accurate (true only after lazy load); model_ready is optimistic
                # so /health/ready is 200 before first session while still truthfully reporting stt_ready
                stt_ready = singleton.is_ready()
                model_ready = has_faster_whisper
        except Exception:
            stt_ready = False
            model_ready = False
    return ReadyResponse(
        status="ready",
        model_ready=model_ready,
        pipeline=pipeline,
        version=settings.app_version,
        stt_ready=stt_ready,
        stt_model=settings.stt_model or "tiny",
        stt_provider=stt_provider,
    )
