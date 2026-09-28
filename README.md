# Real-Time Audio Translation

Browser-based real-time audio translation: microphone → WebSocket → FastAPI → STT → Translation → TTS → WebSocket → Browser.

See `AGENTS.md` for project rules and `docs/` for architecture.

## Repository Structure

```
.
├── backend/            # Python FastAPI (see backend/app/{api,services,providers,models,schemas,core,utils})
├── frontend/frontend/  # React + Vite + JS/JSX (canonical frontend per phase1.md P1-DEV-001)
├── docs/               # BRD, PRD, SRS, TRD, websocket-protocol, architecture
├── implementation-plan/ # Phased roadmap (README + phase1..phase10) — authoritative task tracker
├── Makefile            # dev/lint/test shortcuts
└── AGENTS.md           # Working instructions
```

> Frontend lives at `frontend/frontend/` (nested) — all phase docs reference that path. Do not combine frontend and backend code.

## Prerequisites

- Python 3.11+ (`backend/.venv` via `python -m venv .venv`)
- Node 18+ (`frontend/frontend` via `npm install`)
- Git

## Quick Start

```bash
# 1. Backend env
cp backend/.env.example backend/.env   # edit if needed (CORS_ORIGINS, LOG_LEVEL)
# 2. Frontend env
cp frontend/frontend/.env.example frontend/frontend/.env

# 3. Install + run (two terminals)
make dev-backend   # → http://localhost:8000  (health: /health, docs: /docs)
make dev-frontend  # → http://localhost:5173

# Or manually:
# cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000
# cd frontend/frontend && npm run dev -- --host
```

## Environment

- `backend/.env.example` — all dynamic values env-configurable per AGENTS.md: `APP_*`, `HOST/PORT`, `CORS_ORIGINS`, `WS_V1_PATH`, `PIPELINE_TYPE`, `STT_*`, `TRANSLATION_*`, `TTS_*`, `UNIFIED_*`, `AUDIO_*`, `SESSION_IDLE_TIMEOUT_MS`, `SESSION_MAX_DURATION_MS`, `WS_MAX_QUEUE_DEPTH`, `RATE_LIMIT_*`, `PERF_ENABLED`, `METRICS_ENABLED`. Never commit `.env`.
- `frontend/frontend/.env.example` — `VITE_API_BASE_URL`, `VITE_WS_URL`, `VITE_WS_URL` must match `WS_V1_PATH`.
- All env is loaded via `pydantic-settings` (backend) and `import.meta.env` (frontend) — see `backend/app/core/config.py` and `frontend/frontend/src/config/environment.js`.

## Development Commands

```bash
make help            # list targets
make dev-backend     # backend dev server
make dev-frontend    # frontend dev server
make lint            # ruff check + mypy + eslint
make format          # ruff format (backend)
make test            # pytest -q (backend)
make build-frontend  # vite build

# Direct:
cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy app && .venv/bin/python -m pytest -q
cd frontend/frontend && npm run lint && npm run build
```

## Architecture (Phase 10 Current)

- See `docs/architecture.md` for full Phase 10 system diagram (dual pipelines, metrics, timeout, rate-limit).
- See `docs/trd.md` / `docs/srs.md` / `docs/prd.md` for requirements; implementation behind provider abstractions.
- See `docs/websocket-protocol.md` for `/ws/v1/translate` contract (12 error codes, PCM framing, TTS markers, metrics).
- See `docs/benchmark.md` and `docs/adr/ADR-001-pipeline-selection.md` for cascaded vs unified decision (cascaded default, CC-BY-NC-4.0 caveat).
- See `implementation-plan/README.md` for phased implementation order and progress tracking (10 phases complete, 100%).

## Code Quality

Per `AGENTS.md`: type hints, Pydantic, single-responsibility, no unnecessary abstractions, env vars, structured logging (never log raw audio), thin `api/` handlers, `services/` for business logic, `providers/` for AI integrations.

Check before committing: `ruff check`, `ruff format --check`, `mypy`, `pytest` (backend); `npm run lint`, `npm run build` (frontend).
See `docs/development.md` for full development workflow.

## Implementation Plan

The plan in `implementation-plan/` is the authoritative roadmap. After each implementation:

1. Update `phaseN.md` checklist `[ ]`→`[x]`/`[~]`/`[!]` and `## Progress` table.
2. Update `implementation-plan/README.md` Phase Overview + Overall Progress.
3. Remove dead code and verify with lint/type/build.
4. Commit with `<prefix>: <descriptive>` (e.g., `feat(phase4): implement WebSocket ...`) — see `AGENTS.md` Git.

## Feedback / Actions

- `Ctrl+P` to list available actions (per platform).
- To give feedback, report at `https://github.com/anomalyco/opencode`.
