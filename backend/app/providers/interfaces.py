"""Provider interfaces — P6-MODEL-002..005."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from app.providers.base import BaseProvider

if TYPE_CHECKING:
    pass


class STTProvider(BaseProvider):
    """Streaming STT — per-session audio ingestion."""

    @abstractmethod
    async def start_session(self, session_id: str, source_language: str) -> None:
        """Create per-session state for STT."""

    @abstractmethod
    async def push_audio(self, session_id: str, pcm: bytes) -> None:
        """Feed PCM S16LE mono 16k bytes for session."""

    @abstractmethod
    async def poll_events(self, session_id: str) -> list[dict]:
        """Return raw model events for session (e.g., {text, is_final})."""

    @abstractmethod
    async def end_session(self, session_id: str) -> None:
        """Flush and release per-session STT state."""


class TranslationProvider(BaseProvider):
    """Text translation."""

    @abstractmethod
    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text; may be called for partial hypotheses."""

    # Optional batched variant for future
    async def translate_batch(
        self, texts: list[str], source_lang: str, target_lang: str
    ) -> list[str]:
        return [await self.translate(t, source_lang, target_lang) for t in texts]


class TTSProvider(BaseProvider):
    """Text-to-speech."""

    @abstractmethod
    async def synthesize(self, text: str, lang: str) -> bytes:
        """Return WAV/PCM bytes for text."""


class UnifiedSpeechTranslationProvider(BaseProvider):
    """Direct speech translation — audio in, transcript+translation out."""

    @abstractmethod
    async def start_session(
        self, session_id: str, source_language: str, target_language: str
    ) -> None:
        pass

    @abstractmethod
    async def push_audio(self, session_id: str, pcm: bytes) -> None:
        pass

    @abstractmethod
    async def poll_events(self, session_id: str) -> list[dict]:
        """Raw events with transcript+translation (and optional audio)."""

    @abstractmethod
    async def end_session(self, session_id: str) -> None:
        pass
