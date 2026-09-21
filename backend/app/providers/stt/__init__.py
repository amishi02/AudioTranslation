"""STT providers — whisper (real) and mock."""

from app.providers.mocks.mock_stt import MockSTTProvider
from app.providers.stt.whisper import WhisperSTTProvider, get_whisper_singleton

__all__ = ["MockSTTProvider", "WhisperSTTProvider", "get_whisper_singleton"]
