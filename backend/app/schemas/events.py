"""Normalized application events — P6-BE-001."""

from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel, Field


class TranscriptEvent(BaseModel):
    type: Literal["transcript"] = "transcript"
    session_id: str
    segment_id: int
    status: Literal["partial", "final"]
    text: str
    timestamp: float = Field(default_factory=time.time)


class TranslationEvent(BaseModel):
    type: Literal["translation"] = "translation"
    session_id: str
    segment_id: int
    status: Literal["partial", "final"]
    source_text: str
    translated_text: str
    timestamp: float = Field(default_factory=time.time)


class AudioOutputEvent(BaseModel):
    type: Literal["audio.output.start", "audio.output.end"] = "audio.output.start"
    session_id: str
    segment_id: int
    timestamp: float = Field(default_factory=time.time)


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    code: str
    message: str
    session_id: str | None = None
    timestamp: float = Field(default_factory=time.time)


class SessionReadyEvent(BaseModel):
    type: Literal["session.ready"] = "session.ready"
    session_id: str
    source_language: str
    target_language: str
    timestamp: float = Field(default_factory=time.time)


class SessionEndedEvent(BaseModel):
    type: Literal["session.ended"] = "session.ended"
    session_id: str
    timestamp: float = Field(default_factory=time.time)
