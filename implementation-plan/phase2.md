# Phase 2: Backend Foundation & HTTP API

## Progress

| Status | Count |
|---|---:|
| Completed | 0 |
| Partially Completed | 0 |
| Remaining | 18 |
| Blocked | 0 |
| Total | 18 |

Progress: 0%

Status: Not Started

Last Updated: 2026-09-14

Related documentation: `AGENTS.md` (backend layers), `docs/architecture.md`, `docs/trd.md` §39-46, `docs/srs.md` §17-19 (API requirements, health check), `docs/prd.md` §18 (UI states)

---

## 1. Objective

Establish the modular FastAPI backend foundation and the basic HTTP surface area (`/health`, `/health/ready`, `/api/v1/capabilities`) so the frontend can reliably detect backend availability before any real-time work begins. Enforce a thin API layer with business logic in `services/` and provider isolation in `providers/`.

## 2. Prerequisites

- Phase 1 complete: repo structure, env loading, structured logging, lint/test harness
- Python 3.11+, FastAPI/Uvicorn/Pydantic installed (per `requirements.txt`)
- No model weights or GPU required

## 3. Expected Starting State

- `backend/app/main.py` creates a `FastAPI` app and includes only a `/health` router
- `backend/app/core/config.py` and `logging.py` exist; `.env.example` present
- `backend/app/{services,providers,schemas,models,utils}` exist but are mostly empty stubs
- No versioned API prefix, CORS, global error handling, or capabilities endpoint

## 4. Target State

- FastAPI app is assembled via `create_app()` factory with versioned prefix `/api/v1`, CORS for frontend origin, global exception handlers, and structured logging wired
- Endpoints implemented: `GET /health`, `GET /health/ready`, `GET /api/v1/capabilities` (languages + pipeline info, from config)
- Shared API error envelope (Pydantic `ErrorResponse`) is used for all HTTP errors; no stack traces leak to clients
- Frontend can call `GET {VITE_API_BASE_URL}/health` and determine backend readiness
- Backend tests cover health, ready, capabilities, and error format; lint/type checks still pass

## 5. Task Checklist

### Backend

- [ ] P2-BE-001 Create application factory `backend/app/main.py:create_app()` wiring config, logging, CORS, routers
- [ ] P2-BE-002 Implement `backend/app/schemas/common.py` error envelope `ErrorResponse` + success wrappers
- [ ] P2-BE-003 Add global exception handlers (HTTPException, validation, unhandled) returning `ErrorResponse`
- [ ] P2-BE-004 Implement `GET /health` in `backend/app/api/health.py` (liveness: always ok when process running)
- [ ] P2-BE-005 Implement `GET /health/ready` (readiness: config loaded, no model gate yet — stub `model_ready=True` for Phase 2)
- [ ] P2-BE-006 Implement `GET /api/v1/capabilities` (supported languages, pipeline stub, version)
- [ ] P2-BE-007 Configure CORS (`CORSMiddleware`) from `settings.cors_origins` with safe defaults
- [ ] P2-BE-008 Define backend API versioning convention (`/api/v1` prefix router) and mount health under it or alias
- [ ] P2-BE-009 Add Pydantic schemas for `HealthResponse`, `ReadyResponse`, `CapabilitiesResponse` in `schemas/`

### Integration

- [ ] P2-INT-001 Verify `curl http://localhost:8000/health` and `GET /health/ready` return expected JSON
- [ ] P2-INT-002 Verify CORS preflight from `http://localhost:5173` succeeds

### Testing

- [ ] P2-TEST-001 Add `tests/test_api_health.py`: `/health` returns 200 `{status: "ok"}`
- [ ] P2-TEST-002 Add `tests/test_api_ready.py`: `/health/ready` returns model readiness fields
- [ ] P2-TEST-003 Add `tests/test_api_capabilities.py`: `/api/v1/capabilities` returns languages & pipeline type
- [ ] P2-TEST-004 Add error-format test: unknown route returns `ErrorResponse` envelope with `code` & `message`

### Documentation

- [ ] P2-DOC-001 Document HTTP error codes & envelope in `docs/development.md` or `implementation-plan/phase2.md` appendix

---

## 6. Detailed Task Instructions

### P2-BE-001 Create application factory
- Where: `backend/app/main.py`. Export `def create_app() -> FastAPI:` that (a) calls `configure_logging(settings.log_level)`, (b) creates `FastAPI(title, version)` from settings, (c) mounts routers, (d) adds exception handlers, (e) adds CORS middleware. Top-level `app = create_app()` for `uvicorn app.main:app`.
- Why: Testability (`TestClient(create_app())`) and avoids global import-time side effects.
- Verify: `python -c "from app.main import create_app; print(create_app().routes)"` lists health/capabilities routes.

### P2-BE-002 Implement ErrorResponse envelope
- Where: `backend/app/schemas/common.py`. Define:
  ```python
  class ErrorResponse(BaseModel):
      error: str
      code: str
      message: str
      details: dict | None = None
  ```
  And helper `def error_response(code, message, status=400)`. Use consistent `code` values that later WebSocket layer will reuse (`INVALID_MESSAGE`, `UNSUPPORTED_LANGUAGE`, etc.) but HTTP scope is smaller for this phase.
- Verify: Importable; used by exception handler.

### P2-BE-003 Global exception handlers
- Where: `backend/app/main.py` inside `create_app()`. Handlers for `RequestValidationError`, `StarletteHTTPException`, and generic `Exception` → return `JSONResponse(status_code, content=ErrorResponse(...).model_dump())`. Log with `extra={"code": code}`; never log PII/audio.
- Verify: `curl http://localhost:8000/api/v1/nonexistent` returns JSON envelope, not HTML.

### P2-BE-004 GET /health
- Where: `backend/app/api/health.py` (existing file). Return `{"status": "ok", "version": settings.app_version}` with status 200. Keep handler thin — no service call beyond maybe `health_service`.
- Verify: `curl localhost:8000/health | jq .` shows ok.

### P2-BE-005 GET /health/ready
- Where: same `health.py` or `ready.py`. For Phase 2 readiness is `{"status": "ready", "model_ready": true, "pipeline": settings.pipeline_type or "not_configured"}`. Later phases will gate `model_ready` on real model load.
- Verify: `curl localhost:8000/health/ready` returns ready JSON.

### P2-BE-006 GET /api/v1/capabilities
- Where: `backend/app/api/capabilities.py` + router mounted at `/api/v1`. Response includes `supported_languages` (from config or hard-coded minimal `["en","hi","es","fr","de"]` for Phase 2), `pipeline_types: ["cascaded","unified"]`, `default_pipeline`, `version`. Thin handler — values come from config/schemas.
- Verify: `curl localhost:8000/api/v1/capabilities` returns languages list.

### P2-BE-007 Configure CORS
- Where: `app.main:create_app()` adds `CORSMiddleware(allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])`. Default `cors_origins = ["http://localhost:5173","http://127.0.0.1:5173"]`.
- Verify: `curl -H "Origin: http://localhost:5173" -H "Access-Control-Request-Method: GET" -X OPTIONS http://localhost:8000/health -i` includes `Access-Control-Allow-Origin`.

### P2-BE-009 Add response schemas
- Where: `backend/app/schemas/health.py` (new) and `capabilities.py`. Define `HealthResponse`, `ReadyResponse`, `CapabilitiesResponse` with typed fields. Use `response_model=` in route decorators.
- Verify: `http://localhost:8000/docs` shows typed responses.

### P2-TEST-001..004 Testing
- Where: `backend/tests/test_api_health.py`, `test_api_ready.py`, `test_api_capabilities.py`, `test_error_format.py`. Use `from fastapi.testclient import TestClient; from app.main import app`. Assert status codes and body shapes. Use `pytest-asyncio` not strictly needed yet but fixture-friendly.
- Verify: `python -m pytest -q` all pass.

## 7. Architecture / Data Flow

Phase 2 is strictly request/response HTTP — no WebSocket or audio yet:

```
Browser / curl
      ↓  GET /health, /health/ready, /api/v1/capabilities
FastAPI (api layer, thin handlers)
      ↓
Pydantic schemas / config (no services/providers yet)
      ↓
JSON response (ErrorResponse on failure)
```

This layer will later be consumed by the frontend's health-gating logic and the WebSocket-capability negotiation.

## 8. Files Expected to Be Created/Modified

Backend:
- `backend/app/main.py` (modified → `create_app` factory, lifespan stub, CORS)
- `backend/app/api/health.py` (modified → liveness + readiness)
- `backend/app/api/capabilities.py` (new)
- `backend/app/schemas/common.py` (new)
- `backend/app/schemas/health.py` (new)
- `backend/app/schemas/capabilities.py` (new)
- `backend/app/core/config.py` (modified → `app_version`, `cors_origins`, `supported_languages`)
- `backend/tests/test_api_health.py` (new)
- `backend/tests/test_api_ready.py` (new)
- `backend/tests/test_api_capabilities.py` (new)
- `backend/tests/test_error_format.py` (new)

## 9. Testing Requirements

- Unit: config loads with defaults and with env overrides (`APP_ENV=test`).
- Integration (HTTP): `/health` → 200; `/health/ready` → 200 with `model_ready`; `/api/v1/capabilities` → languages + pipeline info.
- Contract: unknown route returns `ErrorResponse` (`error`, `code`, `message`).
- Verify docs: `/docs` and `/openapi.json` reflect new routes.

## 10. Acceptance Criteria

- [ ] `GET /health` returns `{status: "ok"}` with 200.
- [ ] `GET /health/ready` returns readiness payload with `status` and `model_ready`.
- [ ] `GET /api/v1/capabilities` returns supported languages and pipeline types.
- [ ] All HTTP errors return standardized `ErrorResponse` JSON (no stack traces).
- [ ] CORS allows `http://localhost:5173` (configurable via env).
- [ ] Backend tests for health/ready/capabilities/error-format all pass.
- [ ] `ruff`/`mypy`/`pytest` still green.

## 11. Verification Procedure

```bash
cd backend
uvicorn app.main:app --reload --port 8000 &
sleep 2
curl -s http://localhost:8000/health | jq .
curl -s http://localhost:8000/health/ready | jq .
curl -s http://localhost:8000/api/v1/capabilities | jq .
curl -s http://localhost:8000/api/v1/nonexistent | jq .   # must be ErrorResponse
curl -s http://localhost:8000/docs | head -n 5
python -m pytest -q
ruff check .; ruff format --check .
```

Expected: three successful JSON payloads, error envelope for unknown route, docs page available.

## 12. Known Limitations

- No WebSocket, audio, or model — readiness `model_ready` is a stub that always returns true.
- Capabilities languages are config-driven stubs (real language lists derived from model evaluation in Phases 7–9).
- No authentication, persistence, or rate limiting.

## 13. Risks / Notes

- **Versioned prefix**: Mount capabilities under `/api/v1` so later WS at `/ws/v1/translate` shares the versioning convention; keep `/health` unversioned as alias for simplicity.
- **Thin handlers**: `api/` handlers must delegate to services or config lookups only; no provider instantiation here.
- **Do not block on model**: Readiness must not attempt to load model weights in this phase; that would make local dev brittle.

## 14. Phase Completion Status

- Total tasks: 18
- Completed tasks: 0
- Partially completed tasks: 0
- Remaining tasks: 18
- Blocked tasks: 0
- Overall progress: 0%
- Acceptance criteria status: 0 / 7 satisfied

