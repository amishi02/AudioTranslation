"""Unified pipeline — direct speech translation (mock-backed)."""

from __future__ import annotations

from app.models.session import TranslationSession
from app.providers.interfaces import UnifiedSpeechTranslationProvider
from app.services.event_normalizer import normalize_unified
from app.services.pipeline.base import TranslationPipeline


class UnifiedPipeline(TranslationPipeline):
    def __init__(self, unified: UnifiedSpeechTranslationProvider) -> None:
        self._unified = unified

    async def start_session(self, session: TranslationSession) -> None:
        await self._unified.start_session(session.session_id, session.source_language, session.target_language)

    async def push_audio(self, session_id: str, pcm: bytes) -> None:
        await self._unified.push_audio(session_id, pcm)

    async def poll_events(self, session_id: str) -> list[dict]:
        raws = await self._unified.poll_events(session_id)
        events: list[dict] = []
        for raw in raws:
            tr, tl = normalize_unified(raw, session_id)
            events.append(tr.model_dump())
            events.append(tl.model_dump())
            # Optional audio output would be here in Phase 9
        return events

    async def end_session(self, session_id: str) -> None:
        await self._unified.end_session(session_id)

    def is_ready(self) -> bool:
        return self._unified.is_ready()
