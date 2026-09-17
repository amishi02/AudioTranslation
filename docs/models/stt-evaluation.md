# STT Model Evaluation — Phase 7

## Candidates Evaluated

### 1. faster-whisper (Systran) + openai/whisper-small

- **Model:** `openai/whisper-small` (39M params, ~1GB VRAM small, 244M for small?) / `distil-whisper/distil-small.en` alternative
- **Provider/Runtime:** `Systran/faster-whisper` (CTranslate2, MIT license)
- **Model license:** MIT (OpenAI Whisper weights MIT)
- **Languages:** ~99 languages (whisper-small), including `en`, `hi`, `es`, `fr`, `de` (our Phase2 list). Quality good for en/hi with small.
- **STT:** yes, **Translation:** no (only en translation in some variants), **TTS:** no
- **Streaming:** No true frame-streaming; windowed chunked decoding via buffered incremental (last window) — workaround documented as “windowed final every 2.5s + partial every 200ms”
- **Local exec:** Yes, Python, CPU and CUDA GPU, `pip install faster-whisper`
- **CPU:** Yes (small ~200-600ms per 1s window on i5, near real-time for 60ms chunks windowed)
- **GPU:** Helpful, ~4x faster, VRAM ~1-2GB for small, 8GB for medium
- **Size:** small ~500MB, medium ~1.5GB
- **Latency:** ~200-600ms per decode window on CPU, plus chunk accumulation
- **Quality:** Good for en/hi, flicker acceptable, final stable
- **Install:** `pip install faster-whisper` + auto weight download to `~/.cache/huggingface`

### 2. Vosk (Alphacep) — `vosk-model-small-en-us-0.15`

- **Model:** `vosk-model-small-en-us-0.15` (50MB) + `vosk-model-small-hi-0.22` (separate per language)
- **Provider:** `alphacep/vosk` (Apache 2.0)
- **License:** Apache 2.0 (model) + MIT (code)
- **Languages:** ~20 small models, not 99; hi model exists but larger
- **STT:** yes, per-language model, no translation/TTS
- **Streaming:** Native true streaming via `KaldiRecognizer` AcceptWaveform (frame-level partial)
- **Local exec:** Yes, very lightweight, CPU only, no GPU needed
- **CPU:** Very fast (<100ms), low RAM
- **Size:** 50MB per language
- **Latency:** Excellent, true streaming
- **Quality:** Lower than Whisper for hi/hi, but acceptable for en; limited language coverage vs Whisper
- **Tradeoff:** Per-language model management, less accurate for hi, but smallest.

### 3. openai/whisper.cpp (ggml)

- **Model:** Same Whisper weights converted to `ggml` (MIT)
- **Provider:** `ggerganov/whisper.cpp` (MIT)
- **Streaming:** Similar windowed, not true streaming, via `whisper.cpp` streaming example
- **Local:** Yes, C++ with Python bindings, CPU/GPU (Metal/CUDA)
- **Size:** Similar to faster-whisper
- **Latency:** Similar
- **Note:** More setup (compile), less Pythonic than faster-whisper.

## Comparison Summary

| Criterion | faster-whisper small | Vosk small | whisper.cpp |
|---|---|---|---|
| License | MIT | Apache 2.0 | MIT |
| Languages | 99 | ~20 per model | 99 |
| Streaming | Windowed (emulated) | True frame | Windowed |
| CPU latency (1s window) | 200-600ms | <100ms | 200-600ms |
| VRAM | 1-2GB | <100MB | 1GB |
| Size | 500MB | 50MB/lang | 500MB |
| Quality (en/hi) | Good | Fair (hi weak) | Good |
| Install | pip simple | pip simple | compile |

## Decision — P7-MODEL-004

**Selected for Phase 7 production:** `faster-whisper` + `openai/whisper-small` (fallback `distil-whisper/distil-small.en` for en-only speed).

- **Rationale:** Best language coverage (99 vs 20), MIT license, pip install, reasonable CPU latency, well-documented, aligns with `AGENTS.md` open-source requirement. Vosk’s true streaming is attractive for latency, but hi quality and language coverage are weaker for our Phase2 language list (en,hi,es,fr,de). Whisper.cpp adds compile complexity without benefit over faster-whisper.
- **Env switch:** `STT_PROVIDER=whisper` (real) vs `STT_PROVIDER=mock` (CI/test fallback, no weights). `STT_MODEL=openai/whisper-small`, `STT_DEVICE=cpu|cuda`, `STT_COMPUTE_TYPE=int8|float16`.
- **Fallback:** Mock provider remains available via `STT_PROVIDER=mock` for CI, tests, and local dev without download (no GPU needed). Real provider lazily loads on first `start_session` (documented in `providers/stt/whisper.py`), not at app startup, to keep cold start fast.

## Segment Boundary Policy (P7-PIPE-003)

- For Whisper windowed decoding: `windowed_final_every_N_seconds=2.5` + `silence_threshold_ms=700` (if VAD unavailable) + hard max `segment_chars=200`.
- `partial` emitted at most every 200ms (throttled), `final` on silence or 2.5s window or on `end_session` flush.
- Documented in `providers/stt/whisper.py` header; tunable via `STT_PARTIAL_THROTTLE_MS` env (future).

## Open Issues

- Whisper is not truly streaming — flicker (partial hypothesis changes) is expected; frontend must handle replacement (Phase 7 already handles via `segment_id`).
- GPU not required for Phase 7; CPU small is acceptable for local dev, though ~real-time. Benchmark in Phase 10 will compare Vosk vs Whisper for latency/quality tradeoff if needed.
