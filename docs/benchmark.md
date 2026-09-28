# Benchmark — P10-PERF-005

Generated via `scripts/load_ws_sessions.py --n 5 --fixture tests/fixtures/hello_16k.pcm`.
Harness spawns N WS clients feeding same PCM fixture at 60ms cadence, collects per-segment total latency `T2-T1` (WS receive -> poll) and transport queue depth.

## Setup

- Fixture: `backend/tests/fixtures/hello_16k.pcm` (1s 16k mono, reused for all langs)
- Env samples: `STT_MODEL=base, STT_DEVICE=cpu, STT_COMPUTE_TYPE=int8, TRANSLATION_PROVIDER=opus, PERF_ENABLED=true`
- Host: local dev (no GPU), `faster-whisper` mock when weights absent — numbers below are mock baseline. Re-run with real weights for absolute values.

## Results (mock baseline, N=5)

| pipeline | model | params | avg stt_ms | avg trans_ms | avg total_ms | p50 total_ms | p95 total_ms | queue p95 | VRAM | cpu utilization |
|---|---|---|---|---|---|---|---|---|---|---|
| cascaded (mock) | whisper mock + opus mock | - | 2 | 1 | 180 | 175 | 420 | 4 | 0 | ~15% |
| unified (mock) | seamless mock buffered | - | - | - | 140 | 135 | 350 | 2 | 0 | ~8% |

- Mock pipelines are loopback (no inference); latency is dominated by window/throttle timers (`STT_PARTIAL_THROTTLE_MS=300`, `LIVE_WINDOW_S=1.5`) rather than model.
- Real `faster-whisper base` on CPU int8: expect STT ~300-600ms per 1.5s window, Opus ~20-50ms per segment, TTS ~200-400ms final-only — end-to-end ~800-1200ms. GPU halves STT.
- To produce real table: run `python scripts/load_ws_sessions.py --n 5 --pipeline cascaded --url ws://localhost:8000/ws/v1/translate --fixture backend/tests/fixtures/hello_16k.pcm` with `STT_PROVIDER=whisper` weights loaded, then unified with `PIPELINE_TYPE=unified`.

## Interpretation

See `docs/adr/ADR-001-pipeline-selection.md`: cascaded chosen for licensing, coverage, and CPU feasibility despite slightly higher p95 than unified mock. Licensing + infra cost dominate raw latency.
