"""Capabilities schemas — P2-BE-009."""

from pydantic import BaseModel, Field


class CapabilitiesResponse(BaseModel):
    """Capabilities exposed at GET /api/v1/capabilities."""

    supported_languages: list[str] = Field(
        description="Minimal hard-coded list for Phase 2"
    )
    pipeline_types: list[str] = Field(description="Supported pipeline types")
    default_pipeline: str = Field(description="Default pipeline")
    version: str
