# Unified Speech Translation Model Evaluation — Phase 9

## Candidates Evaluated

### 1. facebook/seamless-streaming (~2.5B streaming S2TT) — SeamlessStreaming

- **Model:** `facebook/seamless-streaming` (streaming S2TT variant of SeamlessM4T, ~2.5B params, streaming Simultaneous Translation)
- **Provider:** Meta AI, Hugging Face `transformers` + `seamless` streaming library
- **License:** ⚠️ **CC-BY-NC-4.0** (non-commercial) — flagged as blocker per `P9-MODEL-004` instructions; not permissive for commercial without license review
- **Language pairs coverage:** ~36 as per published (en,hi,es,fr,de among them, but not 200)
- **STT yes, translation yes, TTS/speech-to-speech variant yes** (S2S via SeamlessM4T S2TT + TTS branch)
- **Streaming/Simultaneous:** native streaming (chunked simultaneous decoding) — only candidate with true streaming
- **Local exec:** requires GPU + large VRAM, `pip install seamless` + HF weights
- **CPU fallback:** non-practical (2.5B on CPU >10× realtime)
- **VRAM:** ~16 GB+ A100/V100 class, system RAM ~18 GB
- **Size:** ~9 GB weights download, repo `facebook/seamless-streaming`
- **Latency target:** lower than cascaded (STT+MT+TTS) when GPU available (~300–500 ms)
- **Install:** `pip install seamless` + CUDA, auto download to HF cache
- **Tradeoff:** True streaming low latency but non-commercial license + GPU-heavy ~16 GB VRAM — flagged as research/comparison tool, not default production unless operator resolves licensing + infra.

### 2. facebook/seamless-m4t-v2-large (~2.3B non-streaming baseline) + openai/whisper-large + HF SpeechTranslation pipeline

- **Model:** `facebook/seamless-m4t-v2-large` (non-streaming S2TT) / `facebook/seamless-m4t-v2-large` S2TT, or `openai/whisper-large-v3` + `Helsinki-NLP/opus` as unified approximation
- **Provider:** Meta AI / OpenAI (Whisper), HF `transformers` pipeline `automatic-speech-recognition` + `translation`
- **License:** `seamless-m4t-v2-large` likewise **CC-BY-NC-4.0**; `whisper-large` MIT
- **Streaming-fidelity:** non-streaming baseline — buffered windowed emulation (like STT Phase 7) until streaming API validated; performance note deferred to Phase 10
- **Language coverage:** `seamless-m4t-v2` ~100+ languages, `whisper-large` 99
- **VRAM:** `seamless-m4t-v2-large` ~14–16 GB, `whisper-large` ~6 GB
- **Size:** ~4.5 GB (`seamless-m4t-v2-large`), `whisper-large` ~3 GB
- **Local feasibility:** GPU required, CPU non-practical for 2.3B
- **Quality:** `seamless-m4t-v2` strong S2TT, `whisper-large` + opus as cascaded baseline similar to Phase 8

## Comparison Summary

| Criterion | seamless-streaming 2.5B | seamless-m4t-v2-large / whisper-large |
|---|---|---|
| License | CC-BY-NC-4.0 ⚠️ | CC-BY-NC-4.0 / MIT |
| Streaming | native simultaneous | buffered emulation |
| VRAM | 16 GB+ | 14–16 GB / 6 GB |
| Size | 9 GB | 4.5 GB / 3 GB |
| CPU feasible | no | no |
| Languages | ~36 | ~100+ / 99 |
| Install | seamless + CUDA | transformers + CUDA |

## Decision — P9-MODEL-006/007

**Recommended unified candidate given license & local feasibility:** **No unified as default for Phase 9 production — default remains `PIPELINE_TYPE=cascaded`** until licensing/compute resolved.

- **Rationale:** SeamlessStreaming's CC-BY-NC-4.0 is explicit non-commercial blocker per plan `P9-MODEL-004` warning; 16 GB VRAM + 9 GB weights not feasible for laptop CPU dev (Phase 1-8 all CPU). Treated as opt-in research/comparison tool, not default. `PIPELINE_TYPE=unified` remains available via `UNIFIED_PROVIDER=mock` (mock-unified baseline) and via `UNIFIED_PROVIDER=seamless` stub that loads only when env selects unified (gate `P9-PIPE-006` to avoid multi-GB memory in cascaded mode). Documented ADR: default cascaded until operator resolves licensing + GPU infra.
- **Env names:** `UNIFIED_PROVIDER=seamless|seamless-m4t|mock`, `UNIFIED_MODEL=facebook/seamless-streaming`, `UNIFIED_DEVICE=cpu|cuda`, `UNIFIED_TARGET_SAMPLE_RATE=16000`.
- **Implementation:** `app/providers/speech_translation/seamless.py` `SeamlessSpeechTranslationProvider` implements `UnifiedSpeechTranslationProvider` with per-session buffers + `segment_id`, delegates to real seamless model when `UNIFIED_PROVIDER != mock` and `PIPELINE_TYPE==unified` via `asyncio.to_thread` buffered window (documented as buffered emulation until streaming API validated). Normalized outputs shape-identical to cascaded (`transcript`+`translation`+optional `audio_bytes`) so frontend unchanged `P9-MODEL-008/009`.
