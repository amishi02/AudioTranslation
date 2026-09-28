# Development Guide

Reference: `AGENTS.md` (§ Development Workflow, Code Quality, Testing, Dependencies, Git) and `implementation-plan/README.md`.

## Prerequisites

- Python 3.11+, Node 18+
- `backend/.venv` and `frontend/frontend/node_modules` (see README Quick Start)

## Project Structure

```
backend/app/
  api/        # Thin FastAPI routes + WebSocket endpoints
  services/   # Business / application logic
  providers/  # STT / translation / TTS integrations (mock ↔ real via env)
  models/     # Domain models
  schemas/    # Pydantic schemas
  core/       # config.py (pydantic-settings) + logging.py
  utils/      # Small helpers

frontend/frontend/src/
  components/ # Presentational UI (no WS/audio logic)
  hooks/      # useWebSocket, useAudioRecorder, etc.
  services/   # websocket.js, audio.js, api.js
  config/     # environment.js (VITE_API_BASE_URL / VITE_WS_URL)
  utils/      # Constants, helpers
```

Canonical frontend path is `frontend/frontend/` per `phase1.md` P1-DEV-001. Keep frontend and backend independent.

## Environment

Copy templates (never commit `.env`):

```bash
cp backend/.env.example backend/.env
cp frontend/frontend/.env.example frontend/frontend/.env
```

- Backend env parsed by `app/core/config.py` (`pydantic-settings`, `extra="ignore"`). All dynamic values env-configurable per AGENTS.md: `APP_*`, `HOST/PORT`, `CORS_ORIGINS`, `WS_V1_PATH`, `PIPELINE_TYPE`, `STT_*`, `TRANSLATION_*`, `TTS_*`, `UNIFIED_*`, `AUDIO_*`, `SESSION_IDLE_TIMEOUT_MS`, `SESSION_MAX_DURATION_MS`, `WS_MAX_QUEUE_DEPTH`, `RATE_LIMIT_*`, `PERF_ENABLED`, `METRICS_ENABLED`.
- Frontend env read via `import.meta.env` in `src/config/environment.js` (`VITE_API_BASE_URL`, `VITE_WS_URL`, etc.).

## Dev Commands

```bash
make help              # list
make dev-backend       # uvicorn app.main:app --reload @ 8000 (uses backend/.venv)
make dev-frontend      # vite --host @ 5173
make lint              # ruff check + mypy + eslint
make format            # ruff format (backend)
make test              # pytest -q (backend)
make build-frontend    # vite build

# Direct equivalents
cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy app
cd backend && .venv/bin/python -m pytest -q
cd frontend/frontend && npm run lint && npm run build
```

## Quality Bars

Per `AGENTS.md`:

- Type hints everywhere (Python); Pydantic for structured data.
- Focused functions/classes, single responsibility, avoid unnecessary abstractions.
- Env vars for config; never commit secrets; structured logging (never log raw audio bytes).
- Thin `api/` handlers → `services/` → `providers/` layering.

Verify locally before committing:

```bash
cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy app && .venv/bin/python -m pytest -q
cd frontend/frontend && npm run lint && npm run build
```

## Testing (Phase 10 Current)

- Backend: `backend/tests/` — `pytest` + `pytest-asyncio` (`asyncio_mode=auto`). Covers: health/readiness, capabilities, WebSocket lifecycle, audio streaming, STT/translation/TTS/unified integration, error taxonomy (`test_errors.py`), WS guards/timeouts/rate-limits/metrics (`test_timeouts_rate_limits.py`, `test_perf_instrumentation.py`), event normalizer, pipeline mocks.
- Frontend: Vitest (`frontend/frontend/src/__tests__/` + `e2e/`): `useSessionState` stabilization, `useAudioRecorder`, `ConnectionStatus`, `Transcript`, `audioPlayback`, `errorMessages` taxonomy + edge-case reducers, `audio` PCM chunking, copy buttons.
- Load harness: `backend/scripts/load_ws_sessions.py --n 5` for concurrent sessions, produces `p50/p95` table for `docs/benchmark.md`.
- Coverage: Phase 10 pyramid includes unit (taxonomy matrix, validation guards), WS integration (flood/oversize/malformed/timeout), frontend unit (edge cases), E2E (canonical journey mock providers), load (N=5 concurrent isolation).

Run all tests via `make test` or the commands above.

## Development Workflow

Per `AGENTS.md`:

1. Read `AGENTS.md` and relevant `docs/` (architecture, websocket-protocol, trd).
2. Read `implementation-plan/README.md` and the target `phaseN.md` top-to-bottom.
3. Inspect existing implementation; plan the smallest appropriate change.
4. Implement tasks in checklist order (`P<phase>-<category>-<number>`), respecting `Depends on:`.
5. After implementation:
   - Update checklist `[ ]`→`[x]`/`[~]`/`[!]` and `## Progress` table (`Progress: XX%`, `Status`, `Last Updated`) + Acceptance Criteria + `README.md` tables.
   - Remove dead code (unused files/imports, replaced mocks, stale env keys) and verify with lint/type/build.
   - Update `docs/` if system behavior changed (or add ADR under `docs/adr/`).
6. Run tests + lint/format + verify app starts.

## Architecture & Docs (Phase 10 Current)

- `docs/architecture.md` — full Phase 10 diagram: dual pipelines (cascaded STT→Translation→TTS + unified Seamless), metrics, timeout/rate-limit guards.
- `docs/trd.md` — cascaded vs unified, provider abstraction, `TranslationPipeline` (push_audio/poll_events), lifecycle, resource management, benchmarking T0-T5.
- `docs/websocket-protocol.md` — `/ws/v1/translate` JSON + binary framing, 12-code taxonomy, PCM caps, audio.output.start/end, metrics.
- `docs/benchmark.md` / `docs/adr/ADR-001-pipeline-selection.md` — cascaded default selection (latency/VRAM/licensing).
- `docs/srs.md` / `docs/prd.md` — requirements, partial/final semantics, PRD §37 edge cases.
- `implementation-plan/` — authoritative phased tasks and progress tracker (10 phases, all complete).

## HTTP API (Phase 10 Current)

- `GET /health` → `{"status":"ok","version":"0.1.0"}` — liveness.
- `GET /health/ready` → `{status,model_ready,pipeline,version,stt_ready,translation_ready,tts_ready,unified_ready,...}` — readiness reflects actual provider loadability (faster-whisper/transformers presence, lazy per-pair).
- `GET /api/v1/capabilities` → `{"supported_languages":["en","hi","es","fr","de"],"pipeline_types":["cascaded","unified"],"default_pipeline":"cascaded","version":"0.1.0"}` — sourced from `app/core/config.py` (`SUPPORTED_LANGUAGES`).
- `GET /metrics` → `{sessions_started,sessions_ended,frames_received,dropped_frames,queue_depth_max,rate_limited_events,timeouts,avg_stt_latency_ms,...}` — P10 perf aggregation.
- Versioning: `/api/v1` prefix for capabilities; `/health` aliases stay unversioned per `phase2.md` Risks.
- Docs: `/docs` (Swagger) and `/openapi.json` reflect typed `response_model` schemas.

CORS is configured via `CORS_ORIGINS` (default `http://localhost:5173,http://127.0.0.1:5173`) through `CORSMiddleware` in `app/main.py:create_app()`; WS upgrade enforces CORS strictly when `APP_ENV=production` (unknown Origin → close 1008).

## Error Envelope (Phase 10)

All HTTP errors return standardized `ErrorResponse` (never HTML or stack traces):

```json
{
  "error": "http_error",
  "code": "NOT_FOUND",
  "message": "Not Found",
  "details": null
}
```

WS errors return `ErrorEvent {type:error,code,message,retryable,session_id,timestamp}` with safe messages (no stacks). Full taxonomy (12 codes): `INVALID_MESSAGE`, `INVALID_SESSION_CONFIG`, `UNSUPPORTED_LANGUAGE`, `UNSUPPORTED_PIPELINE`, `UNSUPPORTED_AUDIO_FORMAT`, `INVALID_AUDIO_DATA`, `MODEL_NOT_READY`, `MODEL_ERROR`, `SESSION_ERROR`, `SESSION_TIMEOUT`, `RATE_LIMITED`, `INTERNAL_ERROR`. Retryable: `MODEL_NOT_READY`, `SESSION_TIMEOUT`, `RATE_LIMITED`. See `app/schemas/errors.py` + `frontend/src/utils/errorMessages.js`.

Codes in use:

| Code | HTTP/WS | When |
|---|---|---|
| `INVALID_MESSAGE` | 422/WS | `RequestValidationError`, malformed/oversize/empty JSON, unknown msg type |
| `INVALID_SESSION_CONFIG` | WS | invalid start payload |
| `UNSUPPORTED_LANGUAGE/PIPELINE` | WS | language/pipeline not in `SUPPORTED_LANGUAGES`/factory |
| `INVALID_AUDIO_DATA` | WS | empty/odd-length/oversize PCM, non-UTF8 binary |
| `RATE_LIMITED` | WS | `frames_per_second`/`bytes_per_second` exceeded, queue saturated |
| `SESSION_TIMEOUT` | WS | idle `SESSION_IDLE_TIMEOUT_MS` or max `SESSION_MAX_DURATION_MS` |
| `MODEL_NOT_READY` | WS | provider not initialized |
| `INTERNAL_ERROR` | 500/WS | unhandled `Exception` (generic message only) |
| `NOT_FOUND` | 404 | unknown route |
| `HTTP_4xx/5xx` | 4xx/5xx | other `StarletteHTTPException` |

Handlers live in `app/main.py:create_app()` (HTTP) and `app/api/websocket.py:_send_error` + global guard (WS). Handlers log `session_id+code+retryable`, never raw audio.

## Git

- Small logical commits, never discard user changes, never `git reset --hard` unless instructed.
- **No auto-commits** — present `git status` + `git diff --staged` + proposed message and wait for explicit `yes`/`commit`/`proceed`.
- Format: `<prefix>: <descriptive and precise change>` — prefixes: `feat`, `fix`, `enhancement`, `refactor`, `chore`, `docs`, `test`, `perf`. Examples:
  - `feat(phase4): implement WebSocket endpoint /ws/v1/translate with session lifecycle and bounded audio queue`
  - `docs(phase6): update event protocol and pipeline docs after provider abstraction`
- Every phase-advancing commit must include its `implementation-plan/phaseN.md` progress update.
