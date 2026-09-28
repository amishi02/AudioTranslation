# ADR-001: Pipeline Selection — Cascaded vs Unified

**Status:** Accepted (Phase 10, 2026-09)

## Context

Phase 10 benchmarks both pipeline families on identical fixtures (`backend/tests/fixtures/hello_16k.pcm`, 5 langs) using `scripts/load_ws_sessions.py` harness measuring `p50/p95` end-to-end latency, CPU/VRAM via `psutil`/`nvidia-smi` stub, and qualitative language coverage.

- **Cascaded:** STT (`faster-whisper` base, CPU int8, ~150MB) -> Opus-MT per-pair (Helsinki-NLP, ~300MB per pair, pivot via en for 20 directed pairs) -> optional Piper TTS (ONNX ~30MB/voice). Mock fallback when weights absent. Fully streaming partials (`segment_id` replacement), de-duplication Strategy D, rate-limited translation. Env `PIPELINE_TYPE=cascaded`.
- **Unified:** SeamlessStreaming / SeamlessM4T direct speech translation. Mock buffered emulation (every 5 pushes -> final) in this repo; real weights require `STT_UNIFIED_MODEL=facebook/seamless-streaming` (~2GB+) + GPU. Env `PIPELINE_TYPE=unified`.

## Decision

**Recommend cascaded as default production pipeline for Phase-1.**

| Criterion | Cascaded | Unified |
|---|---|---|
| Latency (mock, 5 concurr, CPU) | p50 ~180ms, p95 ~420ms (dominant STT window 1.5s + beam 3) | p50 ~140ms, p95 ~350ms (buffered) — faster when model loaded, but unrealistic without GPU |
| VRAM / CPU | Base Whisper int8 + 1 Opus pair ~500MB RAM, CPU-ok, no GPU | Seamless requires >4GB VRAM, GPU strongly recommended; CPU inference too slow for real-time |
| Language coverage | 20 pairs (en<->hi/es/fr/de + pivots) — covers PRD 5 langs | Seamless claims 100+ langs but our adapter only mocks; real streaming WIP upstream |
| Licensing | MIT/Apache (faster-whisper, Opus-MT Marian), permissive | CC-BY-NC-4.0 (Seamless) — non-commercial only, blocks production use |
| Stability / maturity | Whisper + Marian battle-tested, streaming windowed decoding tunable via env | Seamless streaming API unstable, half-Duplex; requires large model download, frequent OOM |
| TTS | Piper MIT, CPU real-time, final-only avoids repeat | Unified may produce own speech — not implemented |

## Consequences

- Keep both pipelines behind `PipelineFactory` env switch; readiness (`/health/ready`) reports per-pipeline `stt_ready/translation_ready/tts_ready/unified_ready`. No frontend change to switch.
- Production deploys use `PIPELINE_TYPE=cascaded, STT_PROVIDER=whisper, TRANSLATION_PROVIDER=opus, TTS_PROVIDER=piper|mock`. `unified` remains opt-in for experiments (`UNIFIED_PROVIDER=seamless`).
- Future work can re-benchmark when Seamless streaming stabilizes or licensing changes; no re-architecture needed.
- Real `p95` at scale limited by CPU/GPU; initial benchmark on mocked + single fixture — expandable via `docs/benchmark.md`.
