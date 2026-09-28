"""Cascaded pipeline — STT -> Translation (Phase 8 Strategy D)."""

from __future__ import annotations

import logging
import time

from app.core.config import settings
from app.models.session import TranslationSession
from app.providers.interfaces import STTProvider, TranslationProvider
from app.services.event_normalizer import normalize_transcript, normalize_translation
from app.services.pipeline.base import TranslationPipeline

logger = logging.getLogger(__name__)

# Strategy D (hybrid) params — P8-PIPE-001 tuned for multi-language visibility
# Hard defaults; perf tuning remains env-driven where applicable via settings
PARTIAL_RATE_LIMIT_MS = 100
MIN_CHAR_DELTA = 1


class CascadedPipeline(TranslationPipeline):
    """Cascaded STT then translation with incremental Strategy D.

    Strategy D: always-translate final (P8-PIPE-006), rate-limited partials
    (P8-PIPE-005), de-duplication (P8-PIPE-004). Audio format (P7-BE-009) is
    PCM S16LE mono 16 kHz consumed by STT; translation operates on text
    segments sharing segment_id. Per-segment state (P8-PIPE-002) tracks
    last_translation_text, last_translated_at, last_char_len, last_word_count
    to decide action without blocking receive_task (P8-BE-008).
    """

    def __init__(
        self, stt: STTProvider, translation: TranslationProvider, tts=None
    ) -> None:
        self._stt = stt
        self._translation = translation
        self._tts = tts  # TTSProvider | None, injected by factory
        self._langs: dict[str, tuple[str, str]] = {}
        # Per-segment state: segment_id -> dict
        self._states: dict[int, dict] = {}

    async def start_session(self, session: TranslationSession) -> None:
        self._langs[session.session_id] = (
            session.source_language,
            session.target_language,
        )
        await self._stt.start_session(session.session_id, session.source_language)
        prepare_pair = getattr(self._translation, "prepare_pair", None)
        if prepare_pair is not None:
            await prepare_pair(session.source_language, session.target_language)

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

    async def poll_events(self, session_id: str) -> list[dict | bytes]:
        t_start = time.monotonic()
        stt_raws = await self._stt.poll_events(session_id)
        stt_ms = (time.monotonic() - t_start) * 1000 if stt_raws else None
        events: list[dict | bytes] = []
        src_lang, tgt_lang = self._langs.get(session_id, ("en", "hi"))
        for raw in stt_raws:
            tr = normalize_transcript(raw, session_id)
            # P10-PERF-001: attach per-event perf if enabled
            if settings.perf_enabled and stt_ms is not None:
                tr_dump = tr.model_dump()
                tr_dump["perf"] = {"stt_ms": round(stt_ms, 2)}
                events.append(tr_dump)
            else:
                events.append(tr.model_dump())
            seg = tr.segment_id
            src = tr.text
            status = tr.status
            if not self._should_translate(src, status, seg):
                continue
            t_tr = time.monotonic()
            translated = await self._translation.translate(src, src_lang, tgt_lang)
            trans_ms = (time.monotonic() - t_tr) * 1000
            # De-duplication P8-PIPE-004: skip if partial and same as last
            state = self._states.get(seg)
            if (
                state is not None
                and status == "partial"
                and translated == state.get("last_translation_text")
            ):
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
            tl_dump = tl.model_dump()
            if settings.perf_enabled:
                tl_dump["perf"] = {
                    "stt_ms": round(stt_ms or 0, 2),
                    "translation_ms": round(trans_ms, 2),
                }
            events.append(tl_dump)
            # Update per-segment state P8-PIPE-002
            self._states[seg] = {
                "last_translation_text": translated,
                "last_translated_at": time.time(),
                "last_char_len": len(src),
                "last_word_count": len(src.split()),
                "last_source_text": src,
            }
            # TTS wiring P9-PIPE-001: synthesize only on final (stable-only P9-TTS-004)
            if status == "final" and self._tts is not None and self._tts.is_ready():
                try:
                    # Chunking P9-TTS-005 handled inside provider
                    tts_bytes = await self._tts.synthesize(translated, tgt_lang)
                    # P9-PIPE-002 framing: start marker -> binary -> end marker
                    # Determine sample_rate from settings or wav header
                    sample_rate = int(
                        getattr(settings, "tts_sample_rate", 22050) or 22050
                    )
                    # Try to parse actual rate from WAV header if piper fallback 16000
                    if tts_bytes.startswith(b"RIFF"):
                        try:
                            import io
                            import wave

                            with wave.open(io.BytesIO(tts_bytes), "rb") as wf:
                                sample_rate = wf.getframerate()
                        except Exception:
                            pass
                    events.append(
                        {
                            "type": "audio.output.start",
                            "session_id": session_id,
                            "segment_id": seg,
                            "sample_rate": sample_rate,
                            "encoding": "wav",
                        }
                    )
                    events.append(tts_bytes)  # raw bytes on WS
                    # Duration hint
                    duration_ms = 0
                    try:
                        import io
                        import wave

                        with wave.open(io.BytesIO(tts_bytes), "rb") as wf:
                            frames = wf.getnframes()
                            rate = wf.getframerate()
                            duration_ms = int(frames / rate * 1000) if rate else 0
                    except Exception:
                        pass
                    events.append(
                        {
                            "type": "audio.output.end",
                            "session_id": session_id,
                            "segment_id": seg,
                            "duration_ms": duration_ms,
                        }
                    )
                except Exception as e:
                    # Map errors P9-TTS-007: do not crash pipeline, emit error via processor loop
                    logger = __import__("logging").getLogger(__name__)
                    logger.warning("tts synthesize failed seg %s: %s", seg, e)
        return events

    async def end_session(self, session_id: str) -> None:
        self._langs.pop(session_id, None)
        self._states.clear()
        await self._stt.end_session(session_id)

    def is_ready(self) -> bool:
        tts_ok = True if self._tts is None else self._tts.is_ready()
        return self._stt.is_ready() and self._translation.is_ready() and tts_ok
