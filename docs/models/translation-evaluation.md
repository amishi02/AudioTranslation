# Translation Model Evaluation — Phase 8

## Candidates Evaluated

### 1. Helsinki-NLP/opus-mt-* (MarianMT)

- **Model:** `Helsinki-NLP/opus-mt-en-hi` (and `Helsinki-NLP/opus-mt-hi-en` reverse), plus `opus-mt-en-es`, `opus-mt-en-fr`, `opus-mt-en-de` etc. One checkpoint per direction.
- **Provider/Runtime:** Helsinki-NLP, MarianNMT → Hugging Face `transformers` (`AutoModelForSeq2SeqLM` + `AutoTokenizer`, requires `sentencepiece`)
- **License:** Marian (Apache-2.0), model weights CC-BY-derived per OPUS corpus; commercially usable for phase 8 supported pairs
- **Pair coverage:** ~1000+ pre-trained pairs; en↔hi exists and scores well on OPUS benchmarks; our Phase 2 list (en,hi,es,fr,de) fully covered via 8 directions (en↔hi, en↔es, en↔fr, en↔de)
- **STT/TTS:** translation only
- **Streaming:** per-request `model.generate(tokenized)` — no simultaneous translation; incremental feeding is best-effort windowed (see Strategy D)
- **Local exec:** yes, Python `transformers` + `sentencepiece`, CPU and CUDA
- **CPU latency:** ~80–300 ms / sentence (short 5-10 tokens) on i5, batchable
- **GPU latency:** ~30–80 ms, VRAM ~500 MB per loaded pair (kept lazy)
- **Size:** ~300 MB per pair (e.g., en-hi 298 MB, en-de 310 MB) — lazy per-pair load keeps cold start ~0 MB until first translate()
- **Quality (en↔hi):** strong on OPUS Tatoeba/Benchmark, better than NLLB-600M per-pair for hi (BLEU +2-3), deterministic Marian decoding
- **Install:** `pip install transformers sentencepiece` (+ `torch` CPU), auto download from HF to `~/.cache/huggingface`
- **Operational tradeoff:** N pairs = N checkpoints to cache; lazy loading avoids 3 GB startup. Good for limited pair set.

### 2. facebook/nllb-200-distilled-600M (Meta NLLB)

- **Model:** `facebook/nllb-200-distilled-600M` (also 1.3B variant)
- **Provider:** Meta AI, Apache-2.0
- **License:** Apache-2.0 (weights + code)
- **Pair coverage:** 200 languages single checkpoint, including en,hi,es,fr,de (uses `__src__`/`__tgt__` language codes like `eng_Latn`, `hin_Deva`)
- **Streaming:** same per-call `generate`, not simultaneous
- **Local exec:** yes, HF `transformers`, CPU/GPU
- **CPU latency:** ~400–800 ms / sentence (600M) on i5, slower than Opus per-pair
- **GPU latency:** ~100–200 ms, VRAM ~4–6 GB (600M) / 8–12 GB (1.3B)
- **Size:** 600M ~2.3 GB, 1.3B ~3.3 GB single file for all pairs (operationally simpler, one cache)
- **Quality:** broader coverage (200) but slightly lower per-pair BLEU vs Opus for en↔hi; still good for multilingual phase
- **Install:** `pip install transformers sentencepiece` + `torch` + `accelerate`
- **Tradeoff:** one weight for all pairs vs larger resident memory; simpler ops but higher latency on CPU.

## Comparison Summary

| Criterion | opus-mt per-pair | NLLB-200 600M |
|---|---|---|
| License | Apache-2.0 (Marian) / CC-BY weights | Apache-2.0 |
| Languages | ~1000 pairs (pairwise) | 200 languages single |
| Pairs for Phase 2 | 8 checkpoints | 1 checkpoint |
| CPU latency (short) | 80–300 ms | 400–800 ms |
| VRAM | 0.5 GB per loaded pair (lazy) | 4–6 GB resident |
| Size | 300 MB/pair | 2.3 GB total |
| Quality en↔hi | Strong (BLEU +) | Good (slightly lower) |
| Install | pip simple | pip + larger download |
| Ops complexity | lazy per-pair | single model |

## Decision — P8-MODEL-003

**Selected for Phase 8 production:** `Helsinki-NLP/opus-mt-*` (`TRANSLATION_PROVIDER=opus`) via `MarianMT` (`transformers`).

- **Rationale:** Lower CPU latency (critical for incremental Strategy D where every partial may translate), smaller per-pair memory, Apache-2.0, pip install, better en↔hi quality for our Phase 2 list. NLLB’s single-model simplicity is attractive for future multilingual (Phase 10 benchmark), but 400–800 ms + 2.3 GB is heavy for real-time cascaded path on CPU dev laptops.
- **Env switch:** `TRANSLATION_PROVIDER=opus` (real) vs `TRANSLATION_PROVIDER=mock` (CI) vs `TRANSLATION_PROVIDER=nllb` (future alt, code path stubbed). `TRANSLATION_MODEL=Helsinki-NLP/opus-mt-en-hi` (fallback template `Helsinki-NLP/opus-mt-{src}-{tgt}`), `TRANSLATION_DEVICE=cpu|cuda`, `TRANSLATION_MAX_LENGTH=128`, `TRANSLATION_NUM_BEAMS=1`.
- **Supported pairs (Phase 8):** `en↔hi`, `en↔es`, `es↔en`, `en↔fr`, `fr↔en`, `en↔de`, `de↔en`, `hi↔en`. Adding a new pair is: download `Helsinki-NLP/opus-mt-{src}-{tgt}` → no code change, just pair list update (see `providers/translation/opus.py` `SUPPORTED_PAIRS`).
- **Where to add pair-model files:** `app/providers/translation/opus.py` `SUPPORTED_PAIRS` set + document new `TRANSLATION_MODEL` template if needed; no pipeline/frontend change.

## Segment Boundary / Incremental Note (P8-PIPE-001)

Opus/NLLB are not simultaneous-translation models — Phase 8 uses best-effort incremental feeding. Very short prefixes (1-2 words) may have lower quality than final; `final` is canonical. Strategy D (hybrid: always-translate final, rate-limited partial) is documented in `app/services/pipeline/cascaded.py` header.

## Open Issues

- First translate() for a new pair cold-start downloads ~300 MB; subsequent calls cached.
- Hindi requires Devanagari; tokenizer (sentencepiece) already handles unicode — smoke test with `नमस्ते` ensures no encode error.
- NLLB stub remains available for benchmark in Phase 10; switching requires only `TRANSLATION_PROVIDER=nllb` env change after adding `nllb.py`.
