"""P8-TEST-001/006: Opus translation provider unit."""

import importlib.util

import pytest

from app.providers.base import ModelError
from app.providers.translation.opus import OpusTranslationProvider


@pytest.mark.asyncio
async def test_opus_provider_mock_fallback():
    """P8-TEST-001: mock fallback translates fixture deterministically without HF download."""
    provider = OpusTranslationProvider()
    await provider.initialize()
    assert provider.is_ready()
    out = await provider.translate("Hello my name is John", "en", "hi")
    assert out
    if importlib.util.find_spec("transformers") is None:
        assert out == "[hi] Hello my name is John"
    else:
        assert out != "[hi] Hello my name is John"
    # cache hit second call
    out2 = await provider.translate("Hello my name is John", "en", "hi")
    assert out2 == out
    await provider.close()


@pytest.mark.asyncio
async def test_opus_unsupported_pair():
    """P8-TEST-006: unsupported pair -> UNSUPPORTED_LANGUAGE."""
    provider = OpusTranslationProvider()
    await provider.initialize()
    with pytest.raises(ModelError) as exc:
        await provider.translate("Hello", "en", "xx_unknown")
    assert exc.value.code == "UNSUPPORTED_LANGUAGE"
    with pytest.raises(ModelError) as exc2:
        await provider.translate("Hello", "en", "en")
    assert exc2.value.code == "UNSUPPORTED_LANGUAGE"


@pytest.mark.asyncio
async def test_opus_invalid_language_code():
    provider = OpusTranslationProvider()
    await provider.initialize()
    with pytest.raises(ModelError) as exc:
        await provider.translate("Hello", "xx", "yy")
    assert exc.value.code in ("INVALID_SESSION_CONFIG", "UNSUPPORTED_LANGUAGE")


@pytest.mark.asyncio
async def test_opus_cache_separate_pairs():
    provider = OpusTranslationProvider()
    await provider.initialize()
    out_en_hi = await provider.translate("Hello", "en", "hi")
    out_en_es = await provider.translate("Hello", "en", "es")
    assert out_en_hi
    assert out_en_es
    if importlib.util.find_spec("transformers") is None:
        assert out_en_hi == "[hi] Hello"
        assert out_en_es == "[es] Hello"
    # different cache entries
    assert out_en_hi != out_en_es
