"""Pipeline base — P6-PIPE-001."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.session import TranslationSession


class TranslationPipeline(ABC):
    """Common pipeline interface — cascaded or unified."""

    @abstractmethod
    async def start_session(self, session: TranslationSession) -> None:
        pass

    @abstractmethod
    async def push_audio(self, session_id: str, pcm: bytes) -> None:
        pass

    @abstractmethod
    async def poll_events(self, session_id: str) -> list[dict]:
        """Return list of normalized event dicts (transcript/translation)."""

    @abstractmethod
    async def end_session(self, session_id: str) -> None:
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        pass
