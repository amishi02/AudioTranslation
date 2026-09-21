"""Translation providers — opus (real) and mocks."""

from app.providers.mocks.mock_translation import MockTranslationProvider
from app.providers.translation.nllb import NLLBTranslationProvider, get_nllb_singleton
from app.providers.translation.opus import OpusTranslationProvider, get_opus_singleton

__all__ = [
    "MockTranslationProvider",
    "OpusTranslationProvider",
    "NLLBTranslationProvider",
    "get_opus_singleton",
    "get_nllb_singleton",
]
