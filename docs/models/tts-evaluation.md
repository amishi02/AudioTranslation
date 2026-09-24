# TTS Model Evaluation — Phase 9

## Candidates Evaluated

### 1. Coqui TTS — XTTS-v2 / VITS (`coqui-ai/TTS`)

- **Model:** `tts_models/multilingual/multi-dataset/xtts_v2` (XTTS-v2, ~1.8 GB) and `tts_models/en/ljspeech/vits` (~100 MB), `tts_models/en/ljspeech/tacotron2-DDC` (baseline)
- **Provider/Runtime:** Coqui AI, `TTS` pip (`coqui-tts`), PyTorch
- **License:** MPL-2.0 for code, model weights under Coqui Public Model License + voice-cloning restriction per XTTS (non-commercial cloning flag); VITS Apache-2.0 friendly per sub-model
- **Languages:** many (en,hi,es,fr,de via multilingual XTTS); VITS monolingual per checkpoint
- **STT/Translation/TTS:** TTS only, no STT/translation; needs transcript input
- **Streaming:** per-request `tts.tts(text)` — no true streaming, buffered synthesis
- **Local exec:** yes, Python, CPU and CUDA; `pip install TTS` or `coqui-tts`
- **CPU latency:** VITS ~2–3× realtime on i5 (short sentence ~300–600 ms), XTTS ~4–6× realtime on CPU (slow), GPU preferred for XTTS (~0.5× realtime)
- **VRAM:** VITS ~1 GB, XTTS ~8 GB, Tacotron ~0.5 GB
- **Size:** VITS ~100–400 MB per voice, XTTS ~1.8 GB
- **Quality:** XTTS high naturalness with reference speaker, VITS good for en but robotic for hi
- **Install:** `pip install TTS` + `torch`, auto download to `~/.cache/coqui`
- **Tradeoff:** High quality but slower/heavier;mpl licensing ok for phase 9 but voice cloning restriction flagged.

### 2. Piper TTS (`OHF-Voice/piper1-gpl`) — Rhasssta Piper

- **Model:** `en_US-lessac-medium` (~60 MB ONNX), `hi_IN-pratham-medium` (~60 MB), `es_ES-sharvard-medium` etc. per voice
- **Provider:** Rhasspy / Piper, ONNX Runtime, `piper-tts` + `onnxruntime`
- **License:** MIT for code, voice models GPL/CC-derived (per voice, permissive for self-hosted)
- **Languages:** en,hi,es,fr,de each separate ONNX checkpoint (multilingual via per-voice)
- **TTS only:** per-request `piper --model voice.onnx --output_file out.wav`
- **Streaming:** buffered per sentence, chunked >120 chars by sentence boundary
- **Local exec:** yes, extremely fast CPU (~real-time or faster on i5 via ONNX), no GPU needed, `pip install piper-tts`
- **CPU latency:** ~100–250 ms / sentence (short), fastest among candidates
- **VRAM:** <100 MB, RAM ~200 MB
- **Size:** <60 MB per voice, 5 voices ~300 MB total for phase 8 languages
- **Quality:** Good intelligibility, slightly robotic vs XTTS but excellent for laptop fallback, deterministic ONNX
- **Install:** `pip install piper-tts onnxruntime` + voice download per lang
- **Tradeoff:** Per-voice monolingual, lower naturalness than XTTS but operationally simplest for CPU-real-time.

## Comparison Summary

| Criterion | Coqui VITS / XTTS-v2 | Piper ONNX |
|---|---|---|
| License | MPL-2.0 / CPML | MIT / GPL voices |
| Languages | many (XTTS multilingual) | 5 voices separate |
| CPU latency (short) | 300–600 ms / 800–1500 ms | 100–250 ms |
| VRAM | 1 GB / 8 GB | <100 MB |
| Size | 0.1–1.8 GB | 60 MB/voice |
| Quality | High (XTTS) | Good (robotic) |
| Install | pip + torch heavy | pip + onnx light |
| Ops | heavy | light |

## Decision — P9-MODEL-003

**Selected for Phase 9 production:** `Piper TTS` (`TTS_PROVIDER=piper` fallback `mock`) via ONNX.

- **Rationale:** CPU-real-time (<250 ms) on laptop, <60 MB per voice, MIT license, pip simple, aligns with AGENTS.md open-source free and `Known Limitations` XTTS too slow on CPU. Coqui VITS/XTTS flagged as research alt for Phase 10 voice naturalness benchmark. Piper per-voice monolingual is acceptable for phase 8 language set (en,hi,es,fr,de) — add voice per language via `TTS_MODEL` template `en_US-lessac-medium`.
- **Env switch:** `TTS_PROVIDER=piper` (real) vs `TTS_PROVIDER=mock` (CI) vs `TTS_PROVIDER=coqui` (future alt, stub). `TTS_MODEL=piper:en_US-lessac-medium` (or voice file path), `TTS_DEVICE=cpu` (onnx CPU/GPU flag), `TTS_SAMPLE_RATE=22050` (per voice, actual rate in `audio.output.start` marker).
- **Stable-only policy:** Synthesize only `translation status=="final"` (rate-limited stable partial off by default `tts_on_partial=false` to avoid repeat-speech), chunk >120 chars by sentence boundary `P9-TTS-005`.
- **Audio format:** WAV PCM16 16/22.05 kHz mono `P9-TTS-003` for `AudioContext.decodeAudioData` easiest; header embedded, `sample_rate` + `encoding:"wav"` in JSON marker.
