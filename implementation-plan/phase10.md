# Phase 10: Hardening, Performance, Testing & Production Readiness

## Progress

| Status | Count |
|---|---:|
| Completed | 0 |
| Partially Completed | 0 |
| Remaining | 31 |
| Blocked | 0 |
| Total | 31 |

Progress: 0%

Status: Not Started

Last Updated: 2026-09-14

Related documentation: `docs/trd.md` §47-48/55-58/64-72 (error, logging, benchmarking, cleanup, deployment, definition of completion), `docs/srs.md` §21-26 (security, logging, testing, performance), `docs/prd.md` §20-22/37 (error handling, real-time + latency, edge cases), `docs/architecture.md` (exclusions hold)

---

## 1. Objective

Harden the real-time system across error taxonomy, input validation, resource limits, performance instrumentation, and a full test pyramid so the application reaches **production-ready Phase-1 completion**: verifiably low-latency cascaded vs unified operation, 8+ edge cases handled, no stack-trace leaks, structured observability, and an explicit architecture selection benchmark.

## 2. Prerequisites

- Phases 7–9 complete: real STT, real translation, real TTS, real or mock unified — both pipeline families selectable and their readiness exposed
- Existing unit/WS/audio/integration tests from Phases 2–9 still green (or annotated slow when model required)
- No outstanding `P?-BE-0xx` provider interface drift between cascaded and unified

## 3. Expected Starting State

- Cascaded and unified pipelines switchable via env, audio path stable, UI supports transcript/translation stabilization and playback
- Error handling is functional (`INVALID_MESSAGE`, `UNSUPPORTED_LANGUAGE`, `RATE_LIMITED`, `MODEL_NOT_READY`) but taxonomy is not fully enumerated and input validation is partial
- No structured performance instrumentation beyond ad-hoc log lines; latency is not measured per-stage with timestamps
- Security rate/size guards are present for WS audio frames but not comprehensive; no explicit edge-case handling for silence, very short/long speech, pause, background noise
- Test pyramid stops at pipeline-level integration; no cross-browser frontend E2E or concurrent-session load harness

## 4. Target State

- Full error taxonomy (≥12 codes) is implemented, logged with `session_id+code+duration`, and mapped to user-friendly frontend messages with no stack traces; all error branches have tests
- Performance instrumentation records `T0..T5` timestamps per segment (capture, WS receive, STT result, translation result, TTS result, playback), producing per-event `latency_ms`, queue depth, and dropped-frame metrics — aggregated `p50/p95` benchmark for cascaded vs unified on fixed fixture set
- Hardened API/WS security: JSON size cap, binary frame cap, payload validation, CORS enforcement, early rejection of oversize/flooding, session timeout (idle), per-session rate limit, bounded queues with `drop-oldest` or `RATE_LIMITED` policy documented
- Frontend E2E verifies the canonical user journey (Start → speak fixture → partial replacement behavior → final stability → playback → Stop → cleanup) under both pipelines, and multi-session concurrency (≥5 sessions) confirmed against resource monitors (CPU/GPU VRAM)
- Phase-1 definition of completion satisfied; remaining future work (auth, DB, Redis, history) remains explicitly out-of-scope and guarded by ADR

## 5. Task Checklist

### Error Handling & Validation

- [ ] P10-ERR-001 Enumerate and document error codes: `INVALID_MESSAGE`, `INVALID_SESSION_CONFIG`, `UNSUPPORTED_LANGUAGE`, `UNSUPPORTED_PIPELINE`, `UNSUPPORTED_AUDIO_FORMAT`, `INVALID_AUDIO_DATA`, `MODEL_NOT_READY`, `MODEL_ERROR`, `SESSION_ERROR`, `SESSION_TIMEOUT`, `RATE_LIMITED`, `INTERNAL_ERROR`
- [ ] P10-ERR-002 Implement WS + HTTP validation layer mapping each code to `ErrorEvent/ErrorResponse` envelope `{code, message, details?, retryable}` with safe messages (no internal stack/model name leakage)
- [ ] P10-ERR-003 Add HTTP/WS `INVAILD_MESSAGE`/`INVALID_AUDIO_DATA` handling for empty JSON, oversize JSON (>64KB), non-UTF8 binary, odd-length PCM, zero-byte frame
- [ ] P10-ERR-004 Add session timeout: idle `NO_AUDIO_MS=15000` → emit `SESSION_TIMEOUT {retryable:true}` then auto-cleanup; hard cap `MAX_SESSION_MS=600_000` (10 min)
- [ ] P10-ERR-005 Add retry vs fatal classification on frontend `StatusBanner` (retry button for `SESSION_TIMEOUT` + `RATE_LIMITED` + `MODEL_NOT_READY`, fatal-only banner for `UNSUPPORTED_*`/`INTERNAL_ERROR`)
- [ ] P10-ERR-006 Guarantee no `raise` leaks raw exception to WS client — global handler catches and emits `INTERNAL_ERROR` generic message

### Security / Input Guards

- [ ] P10-SEC-001 Enforce WS frame caps at boundary: `max_json_bytes=65536`, `max_audio_frame_bytes=65536`, `max_queue_depth=64`; update `config` docs
- [ ] P10-SEC-002 Enforce per-session rate-limit: max `frames_per_second=50` (≥20ms-equivalent floor) + `bytes_per_second` guard → `RATE_LIMITED` without disconnect
- [ ] P10-SEC-003 Enforce CORS strictly (reject unknown `Origin` on WS upgrade when `APP_ENV=production`) and verify `wss://` expectation in prod config docs
- [ ] P10-SEC-004 Ensure no raw audio logged — log only `bytes_len`, `sample_rate`, `session_id`, never `frame_bytes.hex()`; add lint rule comment or test that provider logs exclude PCM payload

### Performance Instrumentation

- [ ] P10-PERF-001 Define capture points: `T0` (mic `port.postMessage` → send), `T1` (WS `receive` bytes), `T2` (STT event emit), `T3` (translation event emit), `T4` (TTS emit / `audio.output.start`), `T5` (frontend playback `decodeAudioData` done); wire `perf.now()` on frontend and `time.monotonic()` on backend into event `timestamp` + `latency_ms` fields
- [ ] P10-PERF-002 Emit per-event `latencyBreakdown {transport_ms, stt_ms, translation_ms, tts_ms, total_ms}` in WS `transcript/translation/audio.output` `details` on `--perf` flag
- [ ] P10-PERF-003 Expose `/metrics` or log-aggregated counters: `sessions_started`, `sessions_ended`, `frames_received`, `dropped_frames`, `queue_depth_max`, `avg_stt_latency_ms`, `avg_translation_latency_ms`
- [ ] P10-PERF-004 Add concurrent-session harness: script `scripts/load_ws_sessions.py` spawning N WS clients feeding same fixture, measuring `p50/p95` total latency and CPU/GPU VRAM (via `psutil` / `nvidia-smi` or stub reads)
- [ ] P10-PERF-005 Execute benchmarking fixture set (same PCM fixture spoken by multiple languages if available) for both pipelines and produce `BENCHMARK.md` (when not present, create `implementation-plan/benchmark-template.md`) with cascaded vs unified latency/quality/resource table

### Frontend — Edge Cases & Resilience

- [ ] P10-FE-001 Handle PRD §37 edge cases: no speech (remain listening without emitting), very short speech (single word → still `final`), long continuous speech (segment splits), pause → `final`, intentional wrong-language mistranslation (quality noted, not error), background noise (transcript may degrade gracefully), network interruption → error/reconnect banner, model delay → "Translating…" indicator
- [ ] P10-FE-002 Implement reconnect helper: on unexpected WS close while mic was active, cease mic capture, show error, offer Try Again without requiring page reload
- [ ] P10-FE-003 Ensure playback queue handles `audio.output.start` with no following bytes gracefully (no infinite wait)

### Cleanup & Resource Management

- [ ] P10-BE-001 Verify session cleanup on every termination path: Stop button, timeout, WebSocketDisconnect, `MODEL_ERROR`, `INTERNAL_ERROR` — audio queue drained, pipeline `end_session()` called, provider per-session buffer cleared, log `session_ended`
- [ ] P10-BE-002 Model lifecycle: real STT/translation/TTS model weights remain shared across sessions (not reloaded per WS); per-session buffers alone are transient — document as hard invariant

### Testing — Pyramid

- [ ] P10-TEST-001 Backend unit: full error-taxonomy matrix → expected `code` + `retryable` boolean
- [ ] P10-TEST-002 WS integration: flood, oversize, malformed, invalid pair, drop-policy verification under `MAX_QUEUE_DEPTH`
- [ ] P10-TEST-003 WS integration: session timeout mid-session → `SESSION_TIMEOUT` emitted then cleanup
- [ ] P10-TEST-004 Frontend unit: error mapping + edge-case reducers (pause→commit, very-short, long-split, silent stream)
- [ ] P10-TEST-005 Frontend E2E: Playwright/Vitest browser E2E for canonical journey on both pipelines (real providers in `mock` mode) — assertion on transcript replacement streak and final stability + audio queue existence
- [ ] P10-TEST-006 Load harness E2E: N=5 concurrent WS sessions each streaming same fixture, assert no cross-session segment leak and aggregate latency table generated

### Documentation & ADR

- [ ] P10-DOC-001 Add `docs/adr/ADR-001-pipeline-selection.md` documenting cascaded-vs-unified recommendation based on benchmark (license, VRAM, latency, language coverage) — named recommendation even if further infra work remains
- [ ] P10-DOC-002 Update `implementation-plan/phase10.md` completion status and mark Phase 1 definition fulfilled per `docs/trd.md §71`
- [ ] P10-DOC-003 Document known deferred items (multi-user rooms, history, auth, billing) as explicitly out-of-scope Phase-2+

### Production Hardening / Deployment Prep

- [ ] P10-DEV-001 Ensure `docker-compose` is **not** introduced as required infra yet; document that `uvicorn --ws websockets` local architecture is the production entry point and containerization (Phase-2) would wrap `backend` + `model runtime` image with GPU runtime flag
- [ ] P10-DEV-002 Verify that no `database`, `Redis`, or `Celery` code was introduced into the real-time path; if any was, refactor out and justify via ADR

---

## 6. Detailed Task Instructions

### P10-ERR-003 Validation examples
- Where: `app/api/websocket.py` binary branch and JSON branch before queue: assert `content_type`-aware branch distinguishes bytes vs str; for JSON, reject `len(text) > config.max_json_bytes` → `INVALID_MESSAGE` ("Message too large") without parsing; for bytes, reject `len(bytes) > config.max_audio_frame_bytes or len(bytes) %2 !=0 or len==0` → `INVALID_AUDIO_DATA`; for both, guard `msg_type not in ("start","stop","ping")` → `INVALID_MESSAGE`.

### P10-PERF-001 Capture points
- Where:
  - `T0` in `services/audio.js` just before `ws.send(pcmBuf)` (`performance.now()` placed into an in-band `audio.send_at` diagnostic JSON preceding frame if perf flag enabled, or kept client-side for later correlation).
  - `T1` at `await websocket.receive_bytes()` timestamp.
  - `T2` when `STTProvider.poll_events` returns a STT event (stt_ms = T2-T1).
  - `T3` when `TranslationProvider.translate` future completes.
  - `T4` when `TTSProvider.synthesize` or `audio.output.start` emitted.
  - `T5` when `audioPlayback.js` `ctx.decodeAudioData(done)`.
  Backend computes `latency_ms = time.monotonic() - T1` per event; frontend computes `T5-T0` `end_to_end_ms`. Emit both via event `metadata: {latencies:{stt_ms, translation_ms, tts_ms, total_ms}, queue_depth, session_id}` on perf-marked sessions.

### P10-PERF-004 Concurrent harness
- Where: `scripts/load_ws_sessions.py` (new) or `backend/tests/helpers/load.py`:
  ```python
  # spawn 5 WS clients, each feeds fixtures/hello_16k.pcm at 60ms cadence
  # collect per-segment end-to-end (from send to translation event) latency
  # summarize {p50, p95, max} per pipeline + dropped_frames sum
  ```
  Log within harness whether cascaded or unified is active from caps `PIPELINE_TYPE`. Run with `python scripts/load_ws_sessions.py --n 5 --pipeline cascaded --profile pcm.bin`.

### P10-PERF-005 Benchmark output
- Template: `implementation-plan/benchmark-results.md` or `docs/benchmark.md` containing table:
  | model | params | pipeline | avg stt_ms | avg trans_ms | avg total_ms | queue p95 | VRAM | cpu utilization |
  Cascaded runs compared vs unified (mock first, then real) using same 10-utterance fixture per language. Call out that model licensing and infra cost are decision criteria alongside raw latency.

### P10-TEST-005 Frontend E2E
- Where: `frontend/e2e/translation-flow.spec.js` (Playwright). Pseudocode:
  ```js
  test('cascaded mock fixture renders with replacement', async ({page})=>{
    await page.goto('/');
    await page.selectOption('[data-testid=source-lang]','en');
    await page.selectOption('[data-testid=target-lang]','hi');
    await page.click('[data-testid=start]');
    await page.evaluate(()=> window.__e2e_feedPCM(window.__fixturePCM));
    await expect(page.locator('[data-testid=transcript-active]')).toContainText('Hello my');
    await expect(page.locator('[data-testid=translation-final]')).toBeVisible({timeout:10000});
  });
  ```
  Inject PCM via `window.__e2e_feedPCM` hook bridging `useWebSocket.sendAudio` for CI. Keep real mic mock still valuable.

### P10-DEV-001 No DB/Redis guard
- Where: `backend/app/main.py` must not import `celery`, `redis`, `sqlalchemy`, or `alembic` — add a `P10-TEST-001`-adjacent sanity `grep` test:
  ```python
  def test_no_forbidden_imports():
      tree = pathlib.Path("app/main.py").read_text()
      assert "celery" not in tree.lower()
  ```
  Update will require ADR `ADR-002-no-redux-queue-for-realtime-path`.

## 7. Architecture / Data Flow

Phase 10 instruments the **already dual-architecture system** without creating a third pipeline:

```
Browser mic  →  T0 capture
       ↓ binary PCM
WS receive  →  T1
       ↓ queue
  Pipeline (cascaded: STT→TRANS; unified: speech→translation)
       ↓ T2 STT         T3 TRANSLATION        T4 TTS/audio
  EventNormalizer adds metadata {T1,T2,T3,T4,queue_depth}
       ↓ WS JSON+binary interleaved
  React: Transcript/Translation + audioPlayback → T5 decode done
       ↓ aggregated latencies → console / /metrics log snapshot
       ↓ concurrent sessions (N) → per-pipeline p50/p95 table → docs/adr/ADR-001
```

All metrics are additive, not disruptive to the hot path.

## 8. Files Expected to Be Created/Modified

Backend:
- `backend/app/schemas/errors.py` (new: centralized error code enum + `retryable` map)
- `backend/app/api/websocket.py` (modified: exhaustive error guards, timeout, rate-limit)
- `backend/app/services/session_service.py` (modified: timeout task, cleanup invariant, detailed logging)
- `backend/app/services/pipeline/cascaded.py` (modified: latency instrumentation hooks)
- `backend/app/services/pipeline/unified.py` (modified)
- `backend/app/providers/base.py` (modified: add `perf_tag` optional)
- `backend/app/core/config.py` (modified: timeout/rate caps, `metrics_enabled`, `perf_flag`)
- `backend/app/api/metrics.py` (new optional: `GET /metrics` or log-only metrics sink)
- `backend/scripts/load_ws_sessions.py` (new)
- `backend/tests/test_errors.py` (new)
- `backend/tests/test_timeouts_rate_limits.py` (new)
- `backend/tests/test_perf_instrumentation.py` (new)
- `backend/tests/helpers/fixtures/` (expanded: multi-language PCM fixtures)

Frontend:
- `frontend/src/utils/errorMessages.js` (new: `code→message` + retryable map `ERROR_CONFIG`)
- `frontend/src/services/websocket.js` (modified: emit `TIMEOUT`, classify `retryable` in `onError` handling)
- `frontend/src/hooks/useSessionState.js` (modified: edge-case handling, retry vs fatal)
- `frontend/src/components/StatusBanner.jsx` (modified: Try Again button wired only for `retryable`)
- `frontend/e2e/translation-flow.spec.js` (new: Playwright E2E)
- `frontend/e2e/helpers/feedPCM.js` (new)

Docs:
- `docs/adr/ADR-001-pipeline-selection.md` (new)
- `docs/benchmark.md` or `implementation-plan/benchmark-results.md` (new)
- `docs/security.md` or update `docs/development.md` with error taxonomy table

## 9. Testing Requirements

- Unit: error code enum completeness, input-validation guards (empty JSON, odd PCM, oversize), WS `MODEL_ERROR`→`INTERNAL_ERROR` mapping, frontend error-message map, latency timestamp computation.
- WS integration: session timeout auto-cleanup, `RATE_LIMITED` under queue flood, `UNSUPPORTED_LANGUAGE`/`UNSUPPORTED_PIPELINE`, concurrent N-session isolation (segments don't cross).
- Frontend unit: reducer edge cases (PRD §37: no-speech silence → no new segment, very-short → final, long→split, pause→final).
- E2E: cached fixture full journey on both pipelines (mock providers on CI) verifying transcript replacement streak and final stability plus playback triple existence; when real pipeline runnable, latency `p95 < SLA.defined`.
- Non-functional: extend `PYTEST_SLOW` marker gating real weights (`pytest.mark.skipIf(mockOnly)`).

## 10. Acceptance Criteria

- [ ] Full error code taxonomy (≥12 codes) implemented with `retryable` flag, safe messages (no stack traces), and tests proving every code is producible from a single fixture/session input.
- [ ] Input validation at WS boundary rejects oversize/malformed JSON and odd/zero-length PCM as the correct code with connection intact.
- [ ] Session timeout (`NO_AUDIO_MS` idle + `MAX_SESSION_MS`) emits `SESSION_TIMEOUT` and cleans up; metrics or logs show the event and session removal.
- [ ] Per-session rate-limit / queue-depth policy documented and enforced (rate excess → `RATE_LIMITED` without disconnect).
- [ ] Performance instrumentation emits per-event `latencies` (T1–T5) observable for both pipelines; aggregated `p50/p95` benchmark report produced comparing cascaded vs unified on identical fixture set.
- [ ] Frontend handles all PRD §37 edge cases and reconnect pattern; playback queue cancels on every termination path.
- [ ] E2E journey (Start → fixture stream → progressive transcript replacement → stable final → translation shown → optional audio → Stop) passes on both pipelines in `mock` mode, and real-provider mode at least shows STT+translation together.
- [ ] `ADRs`: pipeline selection recommendation recorded with licensing/VRAM caveats; Phase-1 "definition of completion" criteria from `docs/trd.md §71` all satisfied.
- [ ] CI contains no `database/Redis/Celery` hard dependencies in the hot path.

## 11. Verification Procedure

```bash
# Backend taxonomy + guards
cd backend
python -m pytest tests/test_errors.py tests/test_timeouts_rate_limits.py tests/test_perf_instrumentation.py -v
ruff check .; ruff format --check .; mypy app

# Manual guard smoke — oversize JSON via wscat
python - << 'PY'
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app).websocket_connect("/ws/v1/translate") as ws:
    ws.send_text('x'*70000)  # >max_json_bytes
    print(ws.receive_json())  # expect INVALID_MESSAGE
    ws.send_bytes(b"\x01")    # odd len
    print(ws.receive_json())  # expect INVALID_AUDIO_DATA
PY

# Perf harness (mock mode — fast)
python scripts/load_ws_sessions.py --n 5 --pipeline cascaded --mock --fixture tests/fixtures/hello_16k.pcm
# produces perf summary lines + docs/benchmark.md when wired

# Frontend
cd ../frontend/frontend
npm run test         # unit (error map, reducers, transcript replacement)
npx playwright test e2e/translation-flow.spec.js --project=chromium  # when configured

# Check definition of completion
cat docs/adr/ADR-001-pipeline-selection.md  # must exist
```

## 12. Known Limitations

- Hardening does not introduce authentication or persistent storage — those remain Phase-2+ only.
- Real `p95` latency at scale is limited by available GPU/CPU; initial benchmark is on mocked + one single-model fixture, not multi-language large test set — expandable via later `docs/benchmark.md` data.
- WSS production deployment (reverse proxy/TLS termination) is documented, not implemented locally; `CORS` enforcement differs between `APP_ENV=development` vs `production` by config docs only.
- Live mic E2E in CI still relies on injected fixture PCM (microphone device unavailable in headless bots).

## 13. Risks / Notes

- **Don't inflate Phase 10**: This phase is hardening — resist re-opening provider abstractions or re-tuning STT window logic heavily; keep remaining model-quality iteration behind small tuning tickets with ADRs rather than extending scope.
- **Timeout vs TTS drain**: Idle timeout must fire only when `audio_queue` empty and no pipeline poll is mid-translation; otherwise a `TIMEOUT` mid-TTS could discard just-generated audio. Add `while queue.qsize()>0 or pipeline.is_translating(): wait` grace before cleanup.
- **Load harness correctness**: Concurrent fixture streaming may saturate one core — ensure harness spawns WS clients across processes not single thread when stressing CPU-bound `model.generate`; otherwise observed `p95` is artifact.
- **Same fixture fairness**: Benchmark both pipelines on identical PCM — do not compare cascaded English-only vs unified Hindi-only fixture and conclude unfairly.

## 14. Phase Completion Status

- Total tasks: 31
- Completed tasks: 0
- Partially completed tasks: 0
- Remaining tasks: 31
- Blocked tasks: 0
- Overall progress: 0%
- Acceptance criteria status: 0 / 9 satisfied

