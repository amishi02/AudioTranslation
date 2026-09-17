"""TranslationSession model — P4-BE-003 (P4-BE-005 state machine)."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Literal

SessionState = Literal[
    "connecting", "ready", "listening", "processing", "ending", "ended", "failed"
]


@dataclass
class TranslationSession:
    """Per-connection session — owns audio queue and lifecycle state."""

    session_id: str
    source_language: str
    target_language: str
    state: SessionState = "connecting"
    audio_queue: asyncio.Queue[bytes] = field(
        default_factory=lambda: asyncio.Queue(maxsize=64)
    )
    created_at: float = field(default_factory=time.time)
    segment_counter: int = 0
    frames_received: int = 0
    bytes_received: int = 0
    dropped_frames: int = 0
    last_frame_at: float | None = None
    # Processor task — set by api/websocket handler
    processor_task: asyncio.Task[None] | None = None
    # Pipeline instance for this session (Phase 6) — avoids global
    pipeline: object | None = None
