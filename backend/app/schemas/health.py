"""Health schemas — P2-BE-009."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Liveness response."""

    status: str = "ok"
    version: str


class ReadyResponse(BaseModel):
    """Readiness response — Phase 7-8 includes STT/translation readiness."""

    status: str = "ready"
    model_ready: bool
    pipeline: str
    version: str
    stt_ready: bool | None = None
    stt_model: str | None = None
    stt_provider: str | None = None
    translation_ready: bool | None = None
    translation_model: str | None = None
    translation_provider: str | None = None
