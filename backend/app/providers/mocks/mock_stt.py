"""Mock STT — deterministic partial/final per session."""

from __future__ import annotations

from app.providers.interfaces import STTProvider


class MockSTTProvider(STTProvider):
    """Deterministic mock: every 2 push_audio → partial, every 5 → final."""

    def __init__(self) -> None:
        self._ready = False
        # session_id -> state
        self._states: dict[str, dict] = {}

    async def initialize(self) -> None:
        self._ready = True

    def is_ready(self) -> bool:
        return self._ready

    async def close(self) -> None:
        self._ready = False
        self._states.clear()

    async def start_session(self, session_id: str, source_language: str) -> None:
        self._states[session_id] = {
            "count": 0,
            "segment_id": 1,
            "source_language": source_language,
            "texts": ["Hello", "Hello my", "Hello my name", "Hello my name is", "Hello my name is John"],
        }

    async def push_audio(self, session_id: str, pcm: bytes) -> None:
        st = self._states.get(session_id)
        if st is None:
            return
        st["count"] += 1

    async def poll_events(self, session_id: str) -> list[dict]:
        st = self._states.get(session_id)
        if st is None:
            return []
        c = st["count"]
        if c == 0:
            return []
        texts = st["texts"]
        seg = st["segment_id"]
        # Every 5th count → final, else partial (cycling through texts)
        idx = min(c - 1, len(texts) - 1)
        text = texts[idx]
        is_final = c % 5 == 0
        # After final, increment segment_id for next utterance and reset count partially
        # For mock, just keep same seg until final, then bump
        event = {
            "session_id": session_id,
            "segment_id": seg,
            "text": text,
            "is_final": is_final,
        }
        if is_final:
            st["segment_id"] = seg + 1
            st["count"] = 0  # reset for next segment
        return [event]

    async def end_session(self, session_id: str) -> None:
        self._states.pop(session_id, None)
