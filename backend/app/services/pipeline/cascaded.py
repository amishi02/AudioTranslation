"""Cascaded pipeline — STT -> Translation (mock-backed for Phase 6)."""

from __future__ import annotations

from app.models.session import TranslationSession
from app.providers.interfaces import STTProvider, TranslationProvider
from app.services.event_normalizer import normalize_transcript, normalize_translation
from app.services.pipeline.base import TranslationPipeline


class CascadedPipeline(TranslationPipeline):
    """Cascaded STT then translation."""

    def __init__(self, stt: STTProvider, translation: TranslationProvider) -> None:
        self._stt = stt
        self._translation = translation
        self._langs: dict[str, tuple[str, str]] = {}

    async def start_session(self, session: TranslationSession) -> None:
        self._langs[session.session_id] = (session.source_language, session.target_language)
        await self._stt.start_session(session.session_id, session.source_language)

    async def push_audio(self, session_id: str, pcm: bytes) -> None:
        await self._stt.push_audio(session_id, pcm)

    async def poll_events(self, session_id: str) -> list[dict]:
        stt_raws = await self._stt.poll_events(session_id)
        events: list[dict] = []
        src_lang, tgt_lang = self._langs.get(session_id, ("en", "hi"))
        for raw in stt_raws:
            tr = normalize_transcript(raw, session_id)
            events.append(tr.model_dump())
            src = tr.text
            translated = await self._translation.translate(src, src_lang, tgt_lang)
            # Build translation raw for normalizer
            trans_raw = {
                "session_id": session_id,
                "segment_id": tr.segment_id,
                "source_text": src,
                "translated_text": translated,
                "is_final": tr.status == "final",
            }
            tl = normalize_translation(trans_raw, session_id)
            events.append(tl.model_dump())
        return events

    async def end_session(self, session_id: str) -> None:
        self._langs.pop(session_id, None)
        await self._stt.end_session(session_id)

    def is_ready(self) -> bool:
        return self._stt.is_ready() and self._translation.is_ready()
