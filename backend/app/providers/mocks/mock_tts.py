"""Mock TTS — returns tiny WAV-like bytes."""

from __future__ import annotations

from app.providers.interfaces import TTSProvider


class MockTTSProvider(TTSProvider):
    def __init__(self) -> None:
        self._ready = False

    async def initialize(self) -> None:
        self._ready = True

    def is_ready(self) -> bool:
        return self._ready

    async def close(self) -> None:
        self._ready = False

    async def synthesize(self, text: str, lang: str) -> bytes:
        # Minimal WAV header + text bytes as payload (not real audio, but non-empty)
        # For Phase 6, frontend will not play, just verify bytes exist
        header = b"RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80\x3e\x00\x00\x00\x7d\x00\x00\x02\x00\x10\x00data\x00\x08\x00\x00"
        return header + text.encode("utf-8")[:100]
