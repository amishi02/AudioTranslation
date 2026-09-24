"""P9-TEST-001: TTS provider init/synthesize."""

import io
import wave

import pytest

from app.providers.tts.piper import PiperTTSProvider


@pytest.mark.asyncio
async def test_tts_provider_load_and_synthesize():
    provider = PiperTTSProvider()
    await provider.initialize()
    assert provider.is_ready()
    wav = await provider.synthesize("Hello world", "en")
    assert isinstance(wav, (bytes, bytearray))
    assert wav.startswith(b"RIFF")
    # Validate WAV header
    with wave.open(io.BytesIO(wav), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() in (16000, 22050)
        assert wf.getnframes() > 0


@pytest.mark.asyncio
async def test_tts_provider_chunking():
    provider = PiperTTSProvider()
    await provider.initialize()
    long_text = "Hello world. " * 20  # >120 chars
    wav = await provider.synthesize(long_text, "en")
    assert wav.startswith(b"RIFF")
    with wave.open(io.BytesIO(wav), "rb") as wf:
        assert wf.getnframes() > 0


@pytest.mark.asyncio
async def test_tts_provider_error_empty():
    provider = PiperTTSProvider()
    await provider.initialize()
    with pytest.raises(Exception):
        await provider.synthesize("", "en")


@pytest.mark.asyncio
async def test_tts_provider_multilingual():
    provider = PiperTTSProvider()
    await provider.initialize()
    for lang in ["en", "hi", "es"]:
        wav = await provider.synthesize("Hello", lang)
        assert wav.startswith(b"RIFF")
