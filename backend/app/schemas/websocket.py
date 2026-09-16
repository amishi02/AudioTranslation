"""WebSocket schemas — P4-BE-002."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SessionStart(BaseModel):
    """Client -> server: {type: start, source_language, target_language}."""

    type: Literal["start"]
    source_language: str = Field(min_length=1)
    target_language: str = Field(min_length=1)

    @field_validator("source_language", "target_language", mode="before")
    @classmethod
    def _normalize_lang(cls, v: object) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return str(v).strip().lower()


class SessionStop(BaseModel):
    """Client -> server: {type: stop}."""

    type: Literal["stop"]


class ErrorEvent(BaseModel):
    """Server -> client: error."""

    type: Literal["error"] = "error"
    code: str
    message: str
    details: dict[str, object] | None = None


class SessionReadyEvent(BaseModel):
    """Server -> client: session.ready."""

    type: Literal["session.ready"] = "session.ready"
    session_id: str
    source_language: str
    target_language: str


class SessionEndedEvent(BaseModel):
    """Server -> client: session.ended."""

    type: Literal["session.ended"] = "session.ended"
    session_id: str


class ConnectedEvent(BaseModel):
    """Server -> client: connected alias (for legacy protocol)."""

    type: Literal["connected"] = "connected"
    session_id: str | None = None
