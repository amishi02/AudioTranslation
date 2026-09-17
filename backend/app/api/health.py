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
    """Readiness — Phase 7: reflect STT provider readiness."""
    pipeline = settings.pipeline_type or "cascaded"
    # For Phase 7, model_ready reflects STT provider readiness; mock is always ready
    stt_provider = (settings.stt_provider or "mock").lower()
    if stt_provider == "mock":
        stt_ready = True
        model_ready = True
    else:
        # For real provider, check if model is ready (lazy load may not yet have happened, so false until first session)
        # We report True if provider would be ready after initialize, else False
        # To avoid loading model on health check, we report based on whether faster-whisper is installed
        try:
            import importlib.util

            has_faster_whisper = importlib.util.find_spec("faster_whisper") is not None
            # If installed, we consider ready as True (will load lazily)
            stt_ready = has_faster_whisper
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
