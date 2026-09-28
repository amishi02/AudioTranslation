"""Opus-MT translation provider (Helsinki-NLP/Marian) — P8-BE-001..006."""

from __future__ import annotations

import asyncio
import logging
from collections import OrderedDict

from app.core.config import settings
from app.providers.base import InferenceError, ModelError, ModelNotReady
from app.providers.interfaces import TranslationProvider

logger = logging.getLogger(__name__)

# Supported pairs for Phase 8 — multi-language (all combos via direct or pivot).
# Direct opus-mt checkpoints exist for en<->X (8). Cross pairs (hi<->es etc.) use pivot via English.
# This gives full 5-language mesh (20 directed pairs) without 20 separate checkpoints.
SUPPORTED_PAIRS: frozenset[tuple[str, str]] = frozenset(
    {
        ("en", "hi"),
        ("hi", "en"),
        ("en", "es"),
        ("es", "en"),
        ("en", "fr"),
        ("fr", "en"),
        ("en", "de"),
        ("de", "en"),
        ("hi", "es"),
        ("es", "hi"),
        ("hi", "fr"),
        ("fr", "hi"),
        ("hi", "de"),
        ("de", "hi"),
        ("es", "fr"),
        ("fr", "es"),
        ("es", "de"),
        ("de", "es"),
        ("fr", "de"),
        ("de", "fr"),
    }
)

# Direct opus checkpoints (only en<->X reliably on HF). Cross pairs use pivot.
DIRECT_OPUS_PAIRS: frozenset[tuple[str, str]] = frozenset(
    {
        ("en", "hi"),
        ("hi", "en"),
        ("en", "es"),
        ("es", "en"),
        ("en", "fr"),
        ("fr", "en"),
        ("en", "de"),
        ("de", "en"),
    }
)

# Allowed language codes (Phase 2 list + extended for NLLB 200). Used for validation.
ALLOWED_LANGS: frozenset[str] = frozenset({"en", "hi", "es", "fr", "de"})

CACHE_SIZE = 64


class OpusTranslationProvider(TranslationProvider):
    """Real translation via Helsinki-NLP Opus-MT (Marian).

    Env-driven: TRANSLATION_PROVIDER=opus|mock, TRANSLATION_MODEL template,
    TRANSLATION_DEVICE=cpu|cuda, TRANSLATION_MAX_LENGTH, TRANSLATION_NUM_BEAMS.

    Lazy per-pair loading: first translate() for a new pair downloads
    Helsinki-NLP/opus-mt-{src}-{tgt} via transformers. Subsequent calls cached.
    If transformers is not installed, falls back to mock prefix translation so
    CI (P8-TEST-001) remains deterministic without 300 MB download.
    """

    def __init__(self) -> None:
        self._ready = False
        self._models: dict[tuple[str, str], tuple[object, object]] = {}
        # LRU cache for identical (src,tgt,text) -> translated
        self._cache: OrderedDict[tuple[str, str, str], str] = OrderedDict()
        self._cache_size = CACHE_SIZE

    async def initialize(self) -> None:
        # Mark ready even without loading a specific pair — lazy load keeps cold start fast.
        # If transformers is missing, we still mark ready with fallback mock logic.
        self._ready = True
        logger.info("opus translation provider initialized (lazy per-pair)")

    def is_ready(self) -> bool:
        return self._ready

    async def close(self) -> None:
        self._models.clear()
        self._cache.clear()
        self._ready = False

    async def prepare_pair(self, source_lang: str, target_lang: str) -> None:
        """Validate and load the selected pair before a session becomes ready."""
        if not self.is_ready():
            raise ModelNotReady("Translation model not ready")
        src = source_lang.strip().lower()
        tgt = target_lang.strip().lower()
        if (src, tgt) not in SUPPORTED_PAIRS:
            raise ModelError(
                f"Unsupported pair {src}->{tgt}", code="UNSUPPORTED_LANGUAGE"
            )
        pairs_to_load = (
            [(src, tgt)]
            if (src, tgt) in DIRECT_OPUS_PAIRS
            else [(src, "en"), ("en", tgt)]
        )
        for pair_src, pair_tgt in pairs_to_load:
            pair = await asyncio.to_thread(self._load_pair, pair_src, pair_tgt)
            if pair is None:
                raise ModelNotReady(
                    f"Translation model unavailable for {pair_src}->{pair_tgt}"
                )

    def _get_model_name(self, src: str, tgt: str) -> str:
        tmpl = settings.translation_model or "Helsinki-NLP/opus-mt-{src}-{tgt}"
        # If template contains {src} placeholder, format it
        if "{src}" in tmpl:
            try:
                return tmpl.format(src=src, tgt=tgt)
            except Exception:
                pass
        # If template is a full HF id like Helsinki-NLP/opus-mt-en-hi, use as-is for default pair
        # but for other pairs construct per-pair name
        default = f"Helsinki-NLP/opus-mt-{src}-{tgt}"
        # If settings provides a specific model that does not match requested pair, still try constructed
        if tmpl.startswith("Helsinki-NLP/opus-mt-") and "-" in tmpl:
            # If settings model matches requested pair exactly, use it
            expected = default
            if tmpl == expected:
                return tmpl
        return default

    def _load_pair(self, src: str, tgt: str) -> tuple[object, object] | None:
        # Try to load via transformers; return None if not installed or load fails
        key = (src, tgt)
        if key in self._models:
            return self._models[key]
        try:
            from transformers import (  # type: ignore[import-untyped]
                AutoModelForSeq2SeqLM,
                AutoTokenizer,
            )
        except ImportError:
            logger.warning(
                "transformers not installed — opus fallback mock for %s->%s", src, tgt
            )
            return None
        model_name = self._get_model_name(src, tgt)
        device = (settings.translation_device or "cpu").lower()
        logger.info("loading opus model %s device=%s", model_name, device)
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            # Device handling: move to cuda if requested and available
            if device == "cuda":
                try:
                    import torch  # type: ignore[import-untyped]

                    if torch.cuda.is_available():
                        model = model.to("cuda")  # type: ignore[union-attr]
                except Exception:
                    pass
            self._models[key] = (tokenizer, model)
            logger.info("opus model loaded %s", model_name)
            return self._models[key]
        except Exception as exc:
            logger.exception("opus model load failed %s: %s", model_name, exc)
            return None

    def _cache_get(self, key: tuple[str, str, str]) -> str | None:
        if key in self._cache:
            # Move to end for LRU
            val = self._cache.pop(key)
            self._cache[key] = val
            logger.debug("translation cache_hit key=%s", key)
            return val
        return None

    def _cache_set(self, key: tuple[str, str, str], val: str) -> None:
        if key in self._cache:
            self._cache.pop(key)
        self._cache[key] = val
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not self.is_ready():
            raise ModelNotReady("Translation model not ready")
        src = source_lang.strip().lower()
        tgt = target_lang.strip().lower()
        # Validation P8-BE-005
        if not src or not tgt:
            raise ModelError(
                "source and target required", code="INVALID_SESSION_CONFIG"
            )
        if src == tgt:
            raise ModelError(
                f"Unsupported pair {src}->{tgt} (same language)",
                code="UNSUPPORTED_LANGUAGE",
            )
        # Check allowed langs first
        if src not in ALLOWED_LANGS or tgt not in ALLOWED_LANGS:
            # If language code itself invalid
            if src not in ALLOWED_LANGS and tgt not in ALLOWED_LANGS:
                raise ModelError(
                    f"Invalid language codes {src}->{tgt}",
                    code="INVALID_SESSION_CONFIG",
                )
            # Otherwise pair unsupported
            raise ModelError(
                f"Unsupported pair {src}->{tgt}", code="UNSUPPORTED_LANGUAGE"
            )
        if (src, tgt) not in SUPPORTED_PAIRS:
            raise ModelError(
                f"Unsupported pair {src}->{tgt}", code="UNSUPPORTED_LANGUAGE"
            )
        if not text or not text.strip():
            return ""
        cache_key = (src, tgt, text)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        # Check if transformers is available — if not, skip pivot and use direct mock
        try:
            import importlib.util

            has_transformers = importlib.util.find_spec("transformers") is not None
        except Exception:
            has_transformers = False

        # Try real model — if direct pair missing and transformers available, pivot via English for cross pairs
        if (
            has_transformers
            and (src, tgt) not in DIRECT_OPUS_PAIRS
            and src != "en"
            and tgt != "en"
        ):
            # Pivot: src -> en -> tgt using two steps (e.g., hi->es via hi->en + en->es)
            try:
                intermediate = await self.translate(text, src, "en")
                # Avoid infinite recursion — second step is direct
                result = await self.translate(intermediate, "en", tgt)
                # For mock fallback intermediate would be [en] text — unwrap to avoid double prefix in real pivot
                # But for real model intermediate is proper English, so result is correct
                # Cache pivot result under original key as well
                self._cache_set(cache_key, result)
                logger.info("opus pivot translate %s->%s via en", src, tgt)
                return result
            except ModelError:
                raise
            except Exception as e:
                logger.warning("opus pivot failed %s->%s: %s", src, tgt, e)
                # fall through to direct attempt
        pair = self._load_pair(src, tgt)
        if pair is None:
            # Fallback mock (deterministic) for CI without weights — still multi-language via prefix
            translated = f"[{tgt}] {text}"
            self._cache_set(cache_key, translated)
            logger.debug(
                "opus fallback translate %s->%s text='%s' -> '%s'",
                src,
                tgt,
                text[:30],
                translated[:30],
            )
            return translated
        tokenizer, model = pair  # type: ignore[misc]
        max_len = int(getattr(settings, "translation_max_length", 128) or 128)
        num_beams = int(getattr(settings, "translation_num_beams", 1) or 1)

        # Blocking generate -> thread
        def _gen() -> str:
            try:
                inputs = tokenizer(
                    text,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=max_len,
                )  # type: ignore[union-attr]
                # Move to device if model on cuda
                try:
                    device = next(model.parameters()).device.type  # type: ignore[union-attr]
                    if device == "cuda":
                        inputs = {k: v.to("cuda") for k, v in inputs.items()}  # type: ignore[union-attr]
                except Exception:
                    pass
                gen = model.generate(**inputs, max_length=max_len, num_beams=num_beams)  # type: ignore[union-attr]
                decoded = tokenizer.batch_decode(gen, skip_special_tokens=True)  # type: ignore[union-attr]
                return decoded[0] if decoded else ""
            except Exception as e:
                raise InferenceError(str(e)) from e

        try:
            translated = await asyncio.to_thread(_gen)
        except InferenceError:
            raise
        except Exception as exc:
            logger.exception("opus inference failed %s->%s: %s", src, tgt, exc)
            raise InferenceError(str(exc)) from exc
        translated = (
            translated.strip()
            if isinstance(translated, str)
            else str(translated).strip()
        )
        self._cache_set(cache_key, translated)
        logger.info(
            "opus translate %s->%s chars %s -> %s", src, tgt, len(text), len(translated)
        )
        return translated


# Singleton for health/factory reuse (like whisper)
_opus_singleton: OpusTranslationProvider | None = None


def get_opus_singleton() -> OpusTranslationProvider:
    global _opus_singleton
    if _opus_singleton is None:
        _opus_singleton = OpusTranslationProvider()
    return _opus_singleton
