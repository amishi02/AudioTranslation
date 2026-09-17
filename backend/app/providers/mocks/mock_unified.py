"""Mock Unified — emits transcript + translation together."""

from __future__ import annotations

from app.providers.interfaces import UnifiedSpeechTranslationProvider


class MockUnifiedProvider(UnifiedSpeechTranslationProvider):
    def __init__(self) -> None:
        self._ready = False
        self._states: dict[str, dict] = {}

    async def initialize(self) -> None:
        self._ready = True

    def is_ready(self) -> bool:
        return self._ready

    async def close(self) -> None:
        self._ready = False
        self._states.clear()

    async def start_session(self, session_id: str, source_language: str, target_language: str) -> None:
        self._states[session_id] = {
            "count": 0,
            "segment_id": 1,
            "src": source_language,
            "tgt": target_language,
            "texts": ["Hello", "Hello my", "Hello my name", "Hello my name is", "Hello my name is John"],
        }

    async def push_audio(self, session_id: str, pcm: bytes) -> None:
        st = self._states.get(session_id)
        if st:
            st["count"] += 1

    async def poll_events(self, session_id: str) -> list[dict]:
        st = self._states.get(session_id)
        if not st or st["count"] == 0:
            return []
        c = st["count"]
        texts = st["texts"]
        idx = min(c - 1, len(texts) - 1)
        src_text = texts[idx]
        is_final = c % 5 == 0
        seg = st["segment_id"]
        translated = f"[{st['tgt']}] {src_text}"
        event = {
            "session_id": session_id,
            "segment_id": seg,
            "source_text": src_text,
            "translated_text": translated,
            "is_final": is_final,
        }
        if is_final:
            st["segment_id"] = seg + 1
            st["count"] = 0
        return [event]

    async def end_session(self, session_id: str) -> None:
        self._states.pop(session_id, None)
