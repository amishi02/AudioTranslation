"""Health schemas — P2-BE-009."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Liveness response."""

    status: str = "ok"
    version: str


class ReadyResponse(BaseModel):
    """Readiness response — Phase 2 stub (model_ready always true)."""

    status: str = "ready"
    model_ready: bool
    pipeline: str
    version: str
