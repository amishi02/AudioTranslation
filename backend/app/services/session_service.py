"""SessionService — P4-BE-001, P4-BE-004/005/006."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from app.core.config import settings
from app.models.session import TranslationSession

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)


class SessionService:
    """Manages in-memory TranslationSession map (per AGENTS.md, no DB in Phase 1)."""

    def __init__(self) -> None:
        self._sessions: dict[str, TranslationSession] = {}
        self._lock = asyncio.Lock()
        # Map websocket id -> session_id for cleanup on disconnect
        self._ws_index: dict[int, str] = {}

    async def create_session(
        self,
        session_id: str,
        source_language: str,
        target_language: str,
        websocket: WebSocket,
    ) -> TranslationSession:
        """Validate and create session.

        Raises ValueError with code-like message on validation failure.
        """
        # Validation per PRD §15
        if not source_language or not target_language:
            raise ValueError("INVALID_SESSION_CONFIG: source and target required")
        if source_language == target_language:
            raise ValueError("UNSUPPORTED_LANGUAGE: source and target must differ")
        # Supported combination stub — check against config list
        supported = set(settings.supported_languages)
        if supported and (
            source_language not in supported or target_language not in supported
        ):
            raise ValueError(
                f"UNSUPPORTED_LANGUAGE: {source_language}->{target_language}"
            )

        qsize = settings.audio_queue_maxsize or 64
        queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=qsize)
        session = TranslationSession(
            session_id=session_id,
            source_language=source_language,
            target_language=target_language,
            state="ready",
            audio_queue=queue,
            created_at=time.time(),
        )
        # Create pipeline per session (Phase 6-7) — env-driven via PIPELINE_TYPE
        try:
            from app.providers.base import ModelError
            from app.services.pipeline.factory import create_and_init_pipeline

            pipeline = await create_and_init_pipeline()
            session.pipeline = pipeline
            await pipeline.start_session(session)
        except ValueError as ve:
            # Unsupported pipeline
            raise ValueError(str(ve)) from ve
        except (
            ModelError
        ) as me:  # P7-BE-007/008: preserve code (UNSUPPORTED_LANGUAGE, MODEL_NOT_READY)
            raise ValueError(f"{me.code}: {me}") from me
        except Exception as e:
            raise ValueError(f"MODEL_ERROR: {e}") from e
        async with self._lock:
            self._sessions[session_id] = session
            self._ws_index[id(websocket)] = session_id
        logger.info(
            "session_created session_id=%s src=%s tgt=%s pipeline=%s",
            session_id,
            source_language,
            target_language,
            settings.pipeline_type or "cascaded",
        )
        return session

    async def get_session(self, session_id: str) -> TranslationSession | None:
        async with self._lock:
            return self._sessions.get(session_id)

    def get_by_websocket(self, websocket: WebSocket) -> TranslationSession | None:
        # No lock needed for sync read of _ws_index after creation — but use best effort
        sid = self._ws_index.get(id(websocket))
        if sid is None:
            return None
        return self._sessions.get(sid)

    async def end_session(self, session_id: str) -> None:
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            # Remove ws_index entries pointing to this sid
            to_del = [k for k, v in self._ws_index.items() if v == session_id]
            for k in to_del:
                self._ws_index.pop(k, None)
        if session is not None:
            session.state = "ended"
            # Pipeline cleanup
            pipeline = session.pipeline
            if pipeline is not None:
                try:
                    await pipeline.end_session(session_id)  # type: ignore[attr-defined]
                except Exception:
                    pass
            # Cancel processor task if present
            task = session.processor_task
            if task is not None and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            # Drain queue
            while not session.audio_queue.empty():
                try:
                    session.audio_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            logger.info("session_ended session_id=%s", session_id)

    async def cleanup_on_disconnect(self, websocket: WebSocket) -> None:
        sid = self._ws_index.get(id(websocket))
        if sid is not None:
            await self.end_session(sid)
            logger.info("websocket_disconnected session_id=%s", sid)


# Singleton instance — imported by api/websocket handler
session_service = SessionService()
