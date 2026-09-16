# Phase 1: Project & Development Foundation

## Progress

| Status | Count |
|---|---:|
| Completed | 9 |
| Partially Completed | 0 |
| Remaining | 9 |
| Blocked | 0 |
| Total | 18 |

Progress: 50%

Status: In Progress

Last Updated: 2026-09-16

Related documentation: `AGENTS.md`, `docs/architecture.md`, `docs/trd.md` §39-40, `docs/development.md`, `docs/srs.md` §7 (NFR-007), `docs/prd.md` §7

---

## 1. Objective

Establish the repository, development environment, and engineering conventions so every subsequent phase can be implemented without revisiting project setup. By the end of Phase 1 any developer/AI agent can clone the repo, run `backend` and `frontend`, pass linting/formatting, and run the initial test harness — all with no database, auth, Redis, or Celery.

## 2. Prerequisites

- Git installed; repo initialized (already exists)
- Python 3.11+ and Node 18+ available locally
- No required infrastructure beyond localhost for this phase
- Documentation under `docs/` and `AGENTS.md` reviewed

## 3. Expected Starting State

- `backend/` contains minimal FastAPI scaffolding (`app/main.py`, `app/api/health.py`, empty `core/config.py`, empty provider stubs, `requirements.txt`, `.venv/`)
- `frontend/frontend/` contains Vite+React scaffold (`App.jsx`, `vite.config.js`, `package.json`) with default HMR demo content
- No shared lint/format, no structured logging, no env template, no backend/frontend directory targets finalized, no dev scripts at repo root

## 4. Target State

- Repository has a stable directory contract with documented conventions
- Backend has: resolved env/config loading, structured logging, ruff/mypy config, pytest config, `.env.example`, and ignores secrets
- Frontend has: ESLint + Prettier (or equivalent), Vite dev/prod scripts verified, env handling, and component/hooks/services folder skeleton
- Root `README.md` (or supplement) describes `backend` vs `frontend` separation and `Ctrl+P` / feedback references (per platform)
- `make`/`npm`/`uvicorn`/`vite` dev commands run deterministically from documented entries
- `ruff check + ruff format --check` and `pytest` and `npm run build` pass on clean checkout

## 5. Task Checklist

### Development / Foundation

- [x] P1-DEV-001 Normalize repository structure and confirm frontend/backend separation
- [x] P1-DEV-002 Create root `.gitignore` entries for `backend/.venv`, `frontend/**/node_modules`, `frontend/**/dist`, local `.env` files, coverage artifacts
- [x] P1-DEV-003 Add `backend/.env.example` with all Phase-1-visible env keys and defaults (no secrets)
- [x] P1-DEV-004 Add root development script/makefile (`Makefile` or `package.json` scripts) for `dev:backend`, `dev:frontend`, `lint`, `format`, `test`

### Backend

- [x] P1-BE-001 Implement `backend/app/core/config.py` using `pydantic-settings` (app name, env, log level, CORS origins, host/port)
- [x] P1-BE-002 Implement `backend/app/core/logging.py` structured logging (level, format, request/session fields, no audio payloads)
- [x] P1-BE-003 Enforce backend directory contract: `app/{api,services,providers,models,schemas,core,utils}` with `__init__.py` and README comment
- [x] P1-BE-004 Configure `ruff` and `mypy` for backend (per `AGENTS.md` quality rules)
- [x] P1-BE-005 Configure `pytest` + `pytest-asyncio` with `backend/pytest.ini` or `pyproject.toml` section and verify `python -m pytest` runs

### Frontend

- [ ] P1-FE-001 Verify Vite config proxies API base or exposes `VITE_API_BASE_URL` / `VITE_WS_URL` via env
- [ ] P1-FE-002 Replace default Vite demo content with minimal app shell (`App.jsx`, `main.jsx`) with placeholder header/status
- [ ] P1-FE-003 Create frontend folder skeleton: `src/{components,hooks,services,config,utils}` (with placeholder `README.md` or index)
- [ ] P1-FE-004 Configure ESLint + formatting for JS/JSX and confirm `npm run lint` + `npm run build` pass

### Testing

- [ ] P1-TEST-001 Add backend smoke test: `tests/test_health.py` importing FastAPI app and checking importability
- [ ] P1-TEST-002 Add frontend build verification (npm build exits 0) documented as verification step

### Documentation

- [ ] P1-DOC-001 Update root `README.md` with prerequisites, setup, and development commands (or confirm dedicated doc)
- [ ] P1-DOC-002 Add `docs/development.md` content: commands, lint/format, testing, env, architecture references

---

## 6. Detailed Task Instructions

### P1-DEV-001 Normalize repository structure and confirm frontend/backend separation
- Where: repo root. Confirm actual paths are `backend/` and `frontend/frontend/` (current scaffold nests a second `frontend/`). Either (a) keep `frontend/frontend` and document it explicitly, or (b) move contents to repo-root `frontend/`. Document decision in `P1-DOC-001`.
- Why: Every phase references file paths; inconsistency causes repeated setup churn.
- Verify: `ls backend/app`, `ls frontend` (or `frontend/frontend`) produce expected listing; `AGENTS.md` rule "do not combine frontend and backend code" satisfied.

### P1-DEV-002 Create root .gitignore entries
- Where: repo root `.gitignore`. Must ignore: `backend/.venv/`, `backend/.pytest_cache/`, `backend/.mypy_cache/`, `backend/.ruff_cache/`, `frontend/**/node_modules/`, `frontend/**/dist/`, `**/.env`, `**/.env.local`, coverage `htmlcov/`, `.coverage`.
- Verify: `git status --ignored` shows `.venv` as ignored.

### P1-DEV-003 Add backend/.env.example
- Where: `backend/.env.example`. Include (with safe defaults, no real secrets):
  ```
  APP_NAME=Real-Time Audio Translation API
  APP_ENV=development
  LOG_LEVEL=INFO
  HOST=0.0.0.0
  PORT=8000
  CORS_ORIGINS=http://localhost:5173
  # Phase-2+ placeholders (commented):
  # PIPELINE_TYPE=cascaded
  # STT_PROVIDER=mock
  ```
- Verify: File committed; `backend/.env` remains gitignored.

### P1-DEV-004 Add root development scripts
- Where: repo root `Makefile` (preferred) or document commands in `README.md`. Provide at least:
  - `make dev-backend` → `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` from `backend/`
  - `make dev-frontend` → `npm run dev -- --host` from `frontend/frontend` (or `frontend`)
  - `make lint` → `ruff check backend && ruff format --check backend`
  - `make test-backend` → `python -m pytest`
- Verify: Each command runs without manual path editing.

### P1-BE-001 Implement core/config.py
- Where: `backend/app/core/config.py`. Use `pydantic_settings.BaseSettings` with `model_config = SettingsConfigDict(env_file=".env", extra="ignore")`. Fields: `app_name`, `app_env: Literal["development","production","test"] = "development"`, `log_level: str = "INFO"`, `host`, `port`, `cors_origins: list[str]`, optional future fields as `Optional` with `None` default.
- Dependencies: `pydantic-settings` already in `requirements.txt`.
- Verify: `python -c "from app.core.config import settings; print(settings.app_name)"` works inside `backend/`.

### P1-BE-002 Implement core/logging.py
- Where: `backend/app/core/logging.py` — function `configure_logging(level: str)` setting up `logging` with structured formatter (include `asctime`, `levelname`, `name`, `message`; leave room for `session_id` via `logging.LoggerAdapter` or `extra`). Must not log raw audio bytes (document decision).
- Verify: Importing `app.main` triggers `configure_logging(settings.log_level)` and `pytest -s` shows structured log line.

### P1-BE-003 Enforce backend directory contract
- Where: `backend/app/{api,services,providers,models,schemas,core,utils}`. Ensure each has `__init__.py`. Optionally add inline comments referencing `AGENTS.md` layers. No business logic inside `api/`.
- Verify: `find backend/app -type f | sort` matches documented structure.

### P1-BE-004 Configure ruff and mypy
- Where: `backend/pyproject.toml` (or `ruff.toml` + `mypy.ini`). Enforce ruff `line-length = 100`, `target-version = "py311"`, `lint.select = ["E","F","I","B"]` minimum; mypy `strict = true` with `ignore_missing_imports` only where needed. Document `ruff check` and `ruff format`.
- Verify: `ruff check backend` and `ruff format --check backend` both exit 0 on clean code.

### P1-BE-005 Configure pytest
- Where: `backend/pyproject.toml` `[tool.pytest.ini_options]` with `asyncio_mode = "auto"`, `testpaths = ["tests"]`. Ensure tests import `app`.
- Verify: `python -m pytest -q` runs (even if only collecting zero/one test) without error.

### P1-FE-001 Verify Vite env handling
- Where: `frontend/frontend/vite.config.js` and `frontend/frontend/src/config/environment.js` (create). `environment.js` should read `import.meta.env.VITE_API_BASE_URL` (default `http://localhost:8000`) and `VITE_WS_URL` (default `ws://localhost:8000/ws/v1/translate`). Define these in `.env.example` for frontend.
- Verify: `npm run dev` prints correct env; `import.meta.env.VITE_API_BASE_URL` resolves in code.

### P1-FE-002 Replace default demo content
- Where: `frontend/frontend/src/App.jsx`, `src/main.jsx`. Replace Vite counter/demo with minimal shell: header `Real-Time Audio Translation`, placeholder sections for Language Selector / Transcript / Translation / Status, and no business logic yet. Keep `useState` removed unless needed.
- Verify: `npm run dev` shows new shell; `npm run build` succeeds.

### P1-FE-003 Create frontend folder skeleton
- Where: `frontend/frontend/src/{components,hooks,services,config,utils}`. Add `README.md` in each explaining purpose. No real component logic needed yet — placeholder files prevent later "where to put it?" churn.
- Verify: `ls -R frontend/frontend/src` shows all five directories.

### P1-FE-004 Configure ESLint + formatting
- Where: Use existing `eslint.config.js` (already present) — ensure `eslint` for JS/JSX and format script (Prettier or ESLint + stylistic). Add `npm run lint` script and `npm run build` already present. Document command.
- Verify: `npm run lint` exit code 0; `npm run build` exit code 0.

### P1-TEST-001 Backend smoke test
- Where: `backend/tests/test_health.py` — import `app.main.app` and assert `app.title` equals expected string; no server needed.
- Verify: `python -m pytest tests/test_health.py -q` → passed.

### P1-DOC-001 Update README
- Where: repo root `README.md`. Sections: prerequisites, `AGENTS.md` reference, frontend vs backend separation, quick start (`make dev-backend`, `make dev-frontend`), env config, lint/test commands. No duplicate architecture spec — link to `docs/`.
- Verify: New clone + `README.md` instructions succeed.

### P1-DOC-002 Add docs/development.md
- Where: `docs/development.md`. Summarize commands, project structure, quality bars (type hints, Pydantic, single-responsibility), and workflow from `AGENTS.md` § Development Workflow (read AGENTS.md, read docs/, inspect, plan, smallest change, tests, lint, verify startup). Link to `implementation-plan/README.md`.
- Verify: File committed with at least sections: Dev Commands, Architecture Layers, Quality, Testing, Env.

## 7. Architecture / Data Flow

Phase 1 introduces no real-time path. System remains:

```
Developer
  ├── backend/  →  uvicorn app.main:app  (FastAPI, no WS logic yet beyond health)
  └── frontend/frontend/  →  vite dev server (React shell)
```

No session, pipeline, or model is loaded. This phase's job is purely engineering foundation.

## 8. Files Expected to Be Created/Modified

Backend:
- `backend/app/core/config.py` (new/expanded)
- `backend/app/core/logging.py` (new/expanded)
- `backend/.env.example` (new)
- `backend/pyproject.toml` (new/updated: ruff, mypy, pytest)
- `backend/tests/test_health.py` (new)

Frontend:
- `frontend/frontend/src/config/environment.js` (new)
- `frontend/frontend/src/App.jsx` (modified: replace demo)
- `frontend/frontend/.env.example` (new)
- `frontend/frontend/src/components/README.md` (new)
- `frontend/frontend/src/hooks/README.md` (new)
- `frontend/frontend/src/services/README.md` (new)

Repo:
- `.gitignore` (modified)
- `README.md` (modified)
- `docs/development.md` (new/expanded)
- `Makefile` or equivalent scripts (new)

## 9. Testing Requirements

- Backend unit: smoke import test for `app.main` and `app.core.config` (valid defaults load without `.env`).
- Lint/format: `ruff check backend` and `ruff format --check backend` must pass in CI/local.
- Type check: `mypy backend/app` must pass (or warn only on allowed `ignore` lines).
- Frontend: `npm run lint` (ESLint) and `npm run build` must pass.

## 10. Acceptance Criteria

- [ ] Repo structure matches documented layout; frontend and backend remain independent.
- [ ] `backend/.env.example` exists and is committed; local `.env` is gitignored.
- [ ] `backend/app/core/config.py` loads via `pydantic-settings` in dev and test without errors.
- [ ] Structured logging is configured and emits formatted logs (no audio payloads).
- [ ] `ruff check` + `ruff format --check` + `mypy` pass on backend.
- [ ] `pytest` runs (≥1 test passing or collecting) with `pytest-asyncio`.
- [ ] Frontend has Vite env handling, folder skeleton, and minimal shell replacing demo.
- [ ] `npm run lint` and `npm run build` pass on frontend.
- [ ] Root `README.md` + `docs/development.md` describe setup and dev workflow accurately.

## 11. Verification Procedure

```bash
# Backend
cd backend
python -m pytest -q
ruff check .
ruff format --check .
mypy app
python -c "from app.core.config import settings; print(settings.app_name)"

# Frontend (use correct path frontend/ vs frontend/frontend/)
cd ../frontend/frontend   # or ../frontend
npm run lint
npm run build
npm run dev -- --host  # expect shell UI at http://localhost:5173

# Repo
git status --ignored   # .venv, node_modules ignored
cat .gitignore
```

Expected: `pytest` passes, `ruff`/`mypy` pass, frontend builds and dev server shows header shell.

## 12. Known Limitations

- No HTTP endpoints beyond later phases (even `/health` is deferred to Phase 2).
- No WebSocket, audio, or model code.
- No environment-driven model config yet (only scaffolding placeholders).
- Frontend shell has no real logic (language selector, transcript, WebSocket hooks arrive in Phases 3–5).

## 13. Risks / Notes

- **Nested frontend path**: Current repo has `frontend/frontend/`; this phase must decide and document the canonical path. If left nested, every later phase's file list must consistently use `frontend/frontend/`.
- **Don't add database/auth/Redis/Celery**: Explicitly out of scope until later product phases (per `AGENTS.md` + `docs/architecture.md`).
- **Assume JS/JSX only**: Do not convert to TypeScript unless a future doc explicitly requires it.

## 14. Phase Completion Status

- Total tasks: 18
- Completed tasks: 0
- Partially completed tasks: 0
- Remaining tasks: 18
- Blocked tasks: 0
- Overall progress: 0%
- Acceptance criteria status: 0 / 9 satisfied

