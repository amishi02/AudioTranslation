"""NLLB translation stub — future multilingual alternative (Phase 8 placeholder)."""

from __future__ import annotations

import logging

from app.providers.translation.opus import OpusTranslationProvider

logger = logging.getLogger(__name__)


class NLLBTranslationProvider(OpusTranslationProvider):
    """Stub for facebook/nllb-200-distilled-600M.

    Phase 8 selects Opus-MT; NLLB is reserved for Phase 10 benchmark.
    This stub inherits Opus fallback logic so TRANSLATION_PROVIDER=nllb
    works with same env switch without code changes in pipeline/factory.
    """

    async def initialize(self) -> None:
        self._ready = True
        logger.info("nllb translation provider initialized (stub, opus fallback)")


_nllb_singleton: NLLBTranslationProvider | None = None


def get_nllb_singleton() -> NLLBTranslationProvider:
    global _nllb_singleton
    if _nllb_singleton is None:
        _nllb_singleton = NLLBTranslationProvider()
    return _nllb_singleton
