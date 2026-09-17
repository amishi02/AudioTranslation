"""Mock Translation — deterministic suffix per target language."""

from __future__ import annotations

from app.providers.interfaces import TranslationProvider


class MockTranslationProvider(TranslationProvider):
    def __init__(self) -> None:
        self._ready = False
        self._cache: dict[tuple[str, str, str], str] = {}

    async def initialize(self) -> None:
        self._ready = True

    def is_ready(self) -> bool:
        return self._ready

    async def close(self) -> None:
        self._ready = False

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        key = (text, source_lang, target_lang)
        if key in self._cache:
            return self._cache[key]
        # Simple deterministic mock: prefix with target lang code
        translated = f"[{target_lang}] {text}"
        self._cache[key] = translated
        return translated
