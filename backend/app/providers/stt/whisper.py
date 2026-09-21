"""Whisper STT provider backed by faster-whisper."""

from __future__ import annotations

import asyncio
import logging
import time

from app.core.config import settings
from app.providers.base import InferenceError, ModelError, ModelNotReady
from app.providers.interfaces import STTProvider

logger = logging.getLogger(__name__)

# Segment boundary policy (P7-PIPE-003) — documented
WINDOWED_FINAL_EVERY_S = 2.5
SILENCE_THRESHOLD_MS = 700
PARTIAL_THROTTLE_MS = 200

# Whisper-supported ISO 639-1 codes (99 languages, per OpenAI Whisper).
# Used for P7-BE-007 language validation.
WHISPER_LANGS: frozenset[str] = frozenset(
    {
        "en",
        "zh",
        "de",
        "es",
        "ru",
        "ko",
        "fr",
        "ja",
        "pt",
        "tr",
        "pl",
        "ca",
        "nl",
        "ar",
        "sv",
        "it",
        "id",
        "hi",
        "fi",
        "vi",
        "he",
        "uk",
        "el",
        "ms",
        "cs",
        "ro",
        "da",
        "hu",
        "ta",
        "no",
        "th",
        "ur",
        "hr",
        "bg",
        "lt",
        "la",
        "mi",
        "ml",
        "cy",
        "sk",
        "te",
        "fa",
        "lv",
        "bn",
        "sr",
        "az",
        "sl",
        "kn",
        "et",
        "mk",
        "br",
        "eu",
        "is",
        "hy",
        "ne",
        "mn",
        "bs",
        "kk",
        "sq",
        "sw",
        "gl",
        "mr",
        "pa",
        "si",
        "km",
        "sn",
        "yo",
        "so",
        "af",
        "oc",
        "ka",
        "be",
        "tg",
        "sd",
        "gu",
        "am",
        "yi",
        "lo",
        "uz",
        "fo",
        "ht",
        "ps",
        "tk",
        "nn",
        "mt",
        "sa",
        "lb",
        "my",
        "bo",
        "tl",
        "mg",
        "as",
        "tt",
        "haw",
        "ln",
        "ha",
        "ba",
        "jw",
        "su",
    }
)


def _pcm_bytes_to_float32(pcm: bytes) -> list[float]:
    """PCM S16LE bytes -> float32 list in [-1,1]."""
    # Interpret as int16 little-endian
    import struct

    n = len(pcm) // 2
    fmt = "<" + "h" * n
    ints = struct.unpack(fmt, pcm[: n * 2])
    return [x / 32768.0 for x in ints]


class WhisperSTTProvider(STTProvider):
    """Real STT via faster-whisper.

    Env-driven: STT_PROVIDER=whisper|mock, STT_MODEL, STT_DEVICE, STT_COMPUTE_TYPE.
    Loads model lazily on first start_session (not at app startup) to keep cold start fast.
    Per-session buffer isolated via dict[session_id, state].
    """

    def __init__(self) -> None:
        self._model = None  # type: ignore[assignment]
        self._model_lock = asyncio.Lock()
        self._ready = False
        # Per-session state: {audio_buffer: bytearray, segment_id: int, last_text: str, count: int, last_partial_at: float, last_final_at: float}
        self._sessions: dict[str, dict] = {}
    async def initialize(self) -> None:
        async with self._model_lock:
            if self._model is not None:
                self._ready = True
                return
            try:
                from faster_whisper import WhisperModel

                model_name = settings.stt_model or "tiny"
                device = settings.stt_device or "cpu"
                compute = settings.stt_compute_type or "int8"
                logger.info(
                    "loading whisper model=%s device=%s compute=%s",
                    model_name,
                    device,
                    compute,
                )

                # Run in thread to avoid blocking event loop
                def _load() -> object:
                    return WhisperModel(model_name, device=device, compute_type=compute)

                self._model = await asyncio.to_thread(_load)
                self._ready = True
                logger.info("whisper model loaded")
            except ImportError as exc:
                raise ModelNotReady(
                    "faster-whisper is not installed; install backend requirements"
                ) from exc
            except Exception as exc:
                logger.exception("whisper model load failed: %s", exc)
                raise ModelNotReady(f"Whisper model failed to load: {exc}") from exc

    def is_ready(self) -> bool:
        return self._ready

    async def close(self) -> None:
        self._sessions.clear()
        self._model = None
        self._ready = False

    async def start_session(self, session_id: str, source_language: str) -> None:
        if not self.is_ready():
            # Auto-initialize lazily if not yet
            await self.initialize()
            if not self.is_ready():
                raise ModelNotReady("STT model not ready")
        # Language mapping per P7-BE-007
        lang = source_language.strip().lower()
        if lang not in WHISPER_LANGS:
            logger.warning(
                "unsupported_language session_id=%s lang=%s", session_id[:8], lang
            )
            raise ModelError(
                f"Language not supported: {lang}", code="UNSUPPORTED_LANGUAGE"
            )
        self._sessions[session_id] = {
            "audio_buffer": bytearray(),
            "segment_id": 1,
            "last_text": "",
            "count": 0,
            "last_partial_at": 0.0,
            "last_final_at": time.time(),
            "source_language": lang,
        }

    async def push_audio(self, session_id: str, pcm: bytes) -> None:
        if not self.is_ready():
            raise ModelNotReady("STT model not ready")
        st = self._sessions.get(session_id)
        if st is None:
            raise ModelNotReady(f"No STT session {session_id}")
        # Log every chunk received (visible at INFO)
        logger.debug(
            "stt push session_id=%s pcm_bytes=%s total_buffer=%s count=%s",
            session_id[:8],
            len(pcm),
            len(st["audio_buffer"]) + len(pcm),
            st["count"] + 1,
        )
        # Append to per-session buffer
        st["audio_buffer"].extend(pcm)
        st["count"] += 1

    async def poll_events(self, session_id: str) -> list[dict]:
        if not self.is_ready():
            raise ModelNotReady("STT model not ready")
        st = self._sessions.get(session_id)
        if st is None:
            return []
        # Throttle partial emissions
        now = time.time()
        if st["count"] == 0:
            return []

        # Real mode: windowed decoding — tuned for real-time (shorter window for faster partials)
        buf: bytearray = st["audio_buffer"]
        min_bytes = 8000  # 0.25s @16k S16LE — faster first partial for real-time use case
        if len(buf) < min_bytes:
            return []
        # Throttle
        if (now - st["last_partial_at"]) * 1000 < PARTIAL_THROTTLE_MS:
            return []

        # Check if we should emit final (silence or windowed time)
        should_final = False
        if (now - st["last_final_at"]) >= WINDOWED_FINAL_EVERY_S:
            should_final = True

        # Decode last ~2.5s window for better context
        window_bytes = bytes(buf[-int(2.5 * 16000 * 2) :])  # last 2.5s
        try:
            # Convert to float32 for faster-whisper
            float32 = _pcm_bytes_to_float32(window_bytes)
            import numpy as np

            audio_np = np.array(float32, dtype=np.float32)

            lang = st["source_language"]

            # faster-whisper transcribe
            def _transcribe() -> str:
                segments, _ = self._model.transcribe(
                    audio_np, language=lang, beam_size=1, without_timestamps=True
                )  # type: ignore[union-attr]
                texts = [s.text.strip() for s in segments]
                return " ".join(texts).strip() if texts else ""

            text: str = await asyncio.to_thread(_transcribe)
            logger.info(
                "stt transcribe real session_id=%s in_bytes=%s window_bytes=%s out_text='%s' final=%s",
                session_id[:8],
                len(buf),
                len(window_bytes),
                text,
                should_final,
            )
            if not text:
                return []
            # Suppress duplicate partials
            if text == st["last_text"] and not should_final:
                logger.info(
                    "stt duplicate suppressed session_id=%s text='%s'",
                    session_id[:8],
                    text,
                )
                return []
            st["last_text"] = text
            seg = st["segment_id"]
            is_final = should_final
            event = {
                "session_id": session_id,
                "segment_id": seg,
                "text": text,
                "is_final": is_final,
            }
            logger.info(
                "stt poll real session_id=%s seg=%s text='%s' final=%s",
                session_id[:8],
                seg,
                text,
                is_final,
            )
            if is_final:
                st["segment_id"] = seg + 1
                st["last_final_at"] = now
                # Keep last 0.5s for continuity, drop older
                keep = int(0.5 * 16000 * 2)
                st["audio_buffer"] = bytearray(buf[-keep:])
            else:
                st["last_partial_at"] = now
            return [event]
        except Exception as e:
            logger.exception(
                "whisper inference failed session_id=%s: %s", session_id, e
            )
            raise InferenceError(str(e)) from e

    async def end_session(self, session_id: str) -> None:
        st = self._sessions.get(session_id)
        if st is None:
            return
        # Flush remaining buffer as final if non-empty and not yet finalized
        buf = st["audio_buffer"]
        if len(buf) > 0 and self._model is not None:
            # Try to produce final from remaining buffer
            try:
                float32 = _pcm_bytes_to_float32(bytes(buf))
                import numpy as np

                audio_np = np.array(float32, dtype=np.float32)
                lang = st["source_language"]

                def _transcribe_final() -> str:
                    segments, _ = self._model.transcribe(
                        audio_np, language=lang, beam_size=1
                    )  # type: ignore[union-attr]
                    return " ".join(s.text.strip() for s in segments).strip()

                text = await asyncio.to_thread(_transcribe_final)
                if text:
                    # This final will be picked up by poll? For end, we don't push via poll, just clean
                    pass
            except Exception:
                pass
        self._sessions.pop(session_id, None)


# Module-level singleton for health/readiness (P7-CFG-002).
# Shared across factory-created instances to reflect actual loaded state
# without reloading weights per session. Factory should reuse this when
# STT_PROVIDER=whisper.
_whisper_singleton: WhisperSTTProvider | None = None


def get_whisper_singleton() -> WhisperSTTProvider:
    global _whisper_singleton
    if _whisper_singleton is None:
        _whisper_singleton = WhisperSTTProvider()
    return _whisper_singleton
