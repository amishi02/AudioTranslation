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

- Backend env parsed by `app/core/config.py` (`pydantic-settings`, `extra="ignore"`). Key Phase 1 vars: `APP_NAME`, `APP_ENV`, `LOG_LEVEL`, `HOST`, `PORT`, `CORS_ORIGINS`. Future `PIPELINE_TYPE`, `STT_PROVIDER`, etc. are optional placeholders.
- Frontend env read via `import.meta.env` in `src/config/environment.js` (`VITE_API_BASE_URL`, `VITE_WS_URL`).

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

## Testing

- Backend: `backend/tests/` — `pytest` + `pytest-asyncio` (configured in `backend/pyproject.toml`, `asyncio_mode=auto`). Smoke test `test_health.py` verifies app import/title/config. Future phases add services / WS / provider integration tests.
- Frontend: component/hook behavior; `npm run build` must pass. Phase 3+ adds Vitest where needed.

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

## Architecture & Docs

- `docs/architecture.md` — Phase 1 scope, system `Browser ↔ WebSocket ↔ FastAPI ↔ STT → Translation → TTS`.
- `docs/trd.md` — cascaded vs unified, provider abstraction, `TranslationPipeline` interface.
- `docs/websocket-protocol.md` — `/ws/v1/translate` JSON + binary framing.
- `docs/srs.md` / `docs/prd.md` — requirements, partial/final semantics.
- `implementation-plan/` — authoritative phased tasks and progress tracker.

## HTTP API (Phase 2)

- `GET /health` → `{"status":"ok","version":"0.1.0"}` — liveness.
- `GET /health/ready` → `{"status":"ready","model_ready":true,"pipeline":"not_configured|cascaded","version":"0.1.0"}` — readiness stub (`model_ready` true until real model gating in Phase 7+).
- `GET /api/v1/capabilities` → `{"supported_languages":["en","hi","es","fr","de"],"pipeline_types":["cascaded","unified"],"default_pipeline":"cascaded","version":"0.1.0"}` — sourced from `app/core/config.py` (`SUPPORTED_LANGUAGES`).
- Versioning: `/api/v1` prefix for capabilities; `/health` aliases stay unversioned per `phase2.md` Risks.
- Docs: `/docs` (Swagger) and `/openapi.json` reflect typed `response_model` schemas.

CORS is configured via `CORS_ORIGINS` (default `http://localhost:5173,http://127.0.0.1:5173`) through `CORSMiddleware` in `app/main.py:create_app()`.

## Error Envelope

All HTTP errors return standardized `ErrorResponse` (never HTML or stack traces):

```json
{
  "error": "http_error",
  "code": "NOT_FOUND",
  "message": "Not Found",
  "details": null
}
```

Codes in use (Phase 2):

| Code | HTTP | When |
|---|---|---|
| `INVALID_MESSAGE` | 422 | `RequestValidationError` |
| `NOT_FOUND` | 404 | unknown route |
| `HTTP_4xx/5xx` | 4xx/5xx | other `StarletteHTTPException` |
| `INTERNAL_ERROR` | 500 | unhandled `Exception` |

Handlers live in `app/main.py:create_app()` (see `app/schemas/common.py`). Validation handlers log at `WARNING`, 5xx at `ERROR`, never log raw audio or PII.

## Git

- Small logical commits, never discard user changes, never `git reset --hard` unless instructed.
- **No auto-commits** — present `git status` + `git diff --staged` + proposed message and wait for explicit `yes`/`commit`/`proceed`.
- Format: `<prefix>: <descriptive and precise change>` — prefixes: `feat`, `fix`, `enhancement`, `refactor`, `chore`, `docs`, `test`, `perf`. Examples:
  - `feat(phase4): implement WebSocket endpoint /ws/v1/translate with session lifecycle and bounded audio queue`
  - `docs(phase6): update event protocol and pipeline docs after provider abstraction`
- Every phase-advancing commit must include its `implementation-plan/phaseN.md` progress update.
