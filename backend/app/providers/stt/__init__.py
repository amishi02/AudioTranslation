"""STT providers — whisper (real) and mock."""

from app.providers.mocks.mock_stt import MockSTTProvider
from app.providers.stt.whisper import WhisperSTTProvider

__all__ = ["MockSTTProvider", "WhisperSTTProvider"]
