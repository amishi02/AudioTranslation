"""Capabilities endpoint — P2-BE-006."""

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.capabilities import CapabilitiesResponse

router = APIRouter(prefix="/api/v1", tags=["capabilities"])


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities() -> CapabilitiesResponse:
    """Return supported languages and pipeline info (Phase 2 stub)."""
    return CapabilitiesResponse(
        supported_languages=settings.supported_languages,
        pipeline_types=["cascaded", "unified"],
        default_pipeline=settings.pipeline_type or "cascaded",
        version=settings.app_version,
    )
