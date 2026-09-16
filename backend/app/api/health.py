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
    """Readiness — Phase 2 stub: model_ready always true, pipeline from config."""
    pipeline = settings.pipeline_type or "not_configured"
    return ReadyResponse(
        status="ready",
        model_ready=True,
        pipeline=pipeline,
        version=settings.app_version,
    )
