"""Cascaded pipeline — STT -> Translation (Phase 8 Strategy D)."""

from __future__ import annotations

import time

from app.models.session import TranslationSession
from app.providers.interfaces import STTProvider, TranslationProvider
from app.services.event_normalizer import normalize_transcript, normalize_translation
from app.services.pipeline.base import TranslationPipeline

# Strategy D (hybrid) params — P8-PIPE-001
PARTIAL_RATE_LIMIT_MS = 250
MIN_CHAR_DELTA = 2


class CascadedPipeline(TranslationPipeline):
    """Cascaded STT then translation with incremental Strategy D.

    Strategy D: always-translate final (P8-PIPE-006), rate-limited partials
    (P8-PIPE-005), de-duplication (P8-PIPE-004). Audio format (P7-BE-009) is
    PCM S16LE mono 16 kHz consumed by STT; translation operates on text
    segments sharing segment_id. Per-segment state (P8-PIPE-002) tracks
    last_translation_text, last_translated_at, last_char_len, last_word_count
    to decide action without blocking receive_task (P8-BE-008).
    """

    def __init__(self, stt: STTProvider, translation: TranslationProvider) -> None:
        self._stt = stt
        self._translation = translation
        self._langs: dict[str, tuple[str, str]] = {}
        # Per-segment state: segment_id -> dict
        self._states: dict[int, dict] = {}

    async def start_session(self, session: TranslationSession) -> None:
        self._langs[session.session_id] = (
            session.source_language,
            session.target_language,
        )
        await self._stt.start_session(session.session_id, session.source_language)

    async def push_audio(self, session_id: str, pcm: bytes) -> None:
        await self._stt.push_audio(session_id, pcm)

    def _should_translate(self, text: str, status: str, seg: int) -> bool:
        """Decide per Strategy D (P8-PIPE-001)."""
        state = self._states.get(seg)
        if state is None:
            # First time for this seg — translate partial/final
            return True
        if status == "final":
            return True
        # Partial: rate limit + char/word delta
        now = time.time()
        elapsed_ms = (now - state["last_translated_at"]) * 1000
        if elapsed_ms < PARTIAL_RATE_LIMIT_MS:
            return False
        char_delta = abs(len(text) - state.get("last_char_len", 0))
        word_count = len(text.split())
        word_delta = word_count - state.get("last_word_count", 0)
        if char_delta >= MIN_CHAR_DELTA or word_delta >= 1:
            return True
        return False

    async def poll_events(self, session_id: str) -> list[dict]:
        stt_raws = await self._stt.poll_events(session_id)
        events: list[dict] = []
        src_lang, tgt_lang = self._langs.get(session_id, ("en", "hi"))
        for raw in stt_raws:
            tr = normalize_transcript(raw, session_id)
            events.append(tr.model_dump())
            seg = tr.segment_id
            src = tr.text
            status = tr.status
            if not self._should_translate(src, status, seg):
                continue
            translated = await self._translation.translate(src, src_lang, tgt_lang)
            # De-duplication P8-PIPE-004: skip if partial and same as last
            state = self._states.get(seg)
            if state is not None and status == "partial" and translated == state.get("last_translation_text"):
                continue
            # Emit translation sharing segment_id and status (P8PIPE-003)
            trans_raw = {
                "session_id": session_id,
                "segment_id": seg,
                "source_text": src,
                "translated_text": translated,
                "is_final": status == "final",
            }
            tl = normalize_translation(trans_raw, session_id)
            events.append(tl.model_dump())
            # Update per-segment state P8-PIPE-002
            self._states[seg] = {
                "last_translation_text": translated,
                "last_translated_at": time.time(),
                "last_char_len": len(src),
                "last_word_count": len(src.split()),
                "last_source_text": src,
            }
        return events

    async def end_session(self, session_id: str) -> None:
        self._langs.pop(session_id, None)
        self._states.clear()
        await self._stt.end_session(session_id)

    def is_ready(self) -> bool:
        return self._stt.is_ready() and self._translation.is_ready()
