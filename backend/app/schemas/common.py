"""Common schemas — Error envelope (P2-BE-002).

Used for all HTTP errors; never expose stack traces.
See implementation-plan/phase2.md P2-BE-002.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    error: str = Field(description="High-level error type, e.g. 'error'")
    code: str = Field(description="Machine code, e.g. INVALID_MESSAGE")
    message: str = Field(description="Human-readable message")
    details: dict[str, object] | None = Field(default=None)


class SuccessResponse(BaseModel):
    """Generic success wrapper (unused in Phase 2 but placeholder for future)."""

    status: str = "ok"
