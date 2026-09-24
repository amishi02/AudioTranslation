"""TTS providers — piper (real) and mock."""

from app.providers.mocks.mock_tts import MockTTSProvider
from app.providers.tts.piper import PiperTTSProvider, get_piper_singleton

__all__ = ["MockTTSProvider", "PiperTTSProvider", "get_piper_singleton"]
