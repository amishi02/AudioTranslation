---
applyTo: "backend/**/*.py"
---

# Backend Instructions

Follow the root `AGENTS.md` and the active `implementation-plan/phaseN.md`. `AGENTS.md` and `docs/` are authoritative; this file only mirrors backend-relevant rules for Copilot.

## Stack & Layers

Use **Python + FastAPI + WebSockets**. Follow the conceptual layers:

```
api        — FastAPI routes and WebSocket endpoints (thin)
services   — Application / business logic
providers  — External STT, translation and TTS implementations
models     — Domain / data models
schemas    — Pydantic request/response schemas and internal structures
core       — Application configuration and shared infrastructure
utils      — Small reusable utilities
```

- Keep `api/` / WebSocket handlers **thin** — no business logic inside endpoints; delegate to `services/`.
- Put all business logic in `services/`; isolate external AI/provider integrations behind provider interfaces or service classes.
- Use `async` for I/O-bound operations.

## Real-Time Architecture

```
Client -> WebSocket -> Audio Processing -> Speech-to-Text -> Translation -> Text-to-Speech -> WebSocket -> Client
```

- Do not introduce **Celery or Redis** into the real-time processing path.
- Do not introduce **PostgreSQL / SQLite / MongoDB** or any database in Phase 1 unless explicitly requested.

## Implementation Plan Compliance

- Before touching `backend/`, read `AGENTS.md` § Implementation Plan Workflow, then `implementation-plan/README.md` and the target `phaseN.md` top-to-bottom. Implement tasks strictly in checklist order (`P<phase>-<category>-<number>`), respecting `Depends on:`.
- After each backend implementation pass:
  1. Update the phase file checklist: `[x]` completed (implemented **and** verified via the phase's Verification Procedure) / `[~]` partial / `[!]` blocked with reason.
  2. Update the phase's `## Progress` table (Completed / Partially / Remaining / Blocked / Total, `Progress: XX%`, `Status`, `Last Updated`) and Acceptance Criteria checkboxes; add any newly discovered tasks with unique IDs.
  3. Update `implementation-plan/README.md` tables if the phase scope changed.
  4. **Remove dead code:** unused files, commented blocks, unreachable branches, replaced placeholder mocks (keep `mock` providers only behind env switches where the plan requires), unused imports, stale env keys, orphaned fixtures. Verify with `ruff check`, `ruff format --check`, `mypy`, and backend `pytest`.
  5. **Sync docs:** if backend behavior diverges from the plan, update the phase file's Known Limitations / Risks / Notes and, when system behavior changes, update `docs/` (`docs/architecture.md`, `docs/trd.md`, `docs/websocket-protocol.md`, `docs/srs.md`) or add an ADR under `docs/adr/`.

## Code Quality

- Use type hints everywhere; use Pydantic for structured data.
- Keep functions and classes focused on one responsibility; avoid unnecessary abstractions.
- Use dependency injection where appropriate; handle errors explicitly.
- Never hardcode API keys or secrets; use environment variables (`backend/.env.example` as template, never commit `.env`).
- Use structured logging; never log raw audio bytes or provider credentials.

## Testing

Tests alongside significant functionality: `services`, provider integrations where practical, WebSocket behavior, error handling. Do not mark backend tasks `[x]` until `pytest`, `ruff check`/`ruff format --check`, and `mypy` pass.

## Dependencies

Do not add a dependency because it is popular. Verify (1) the existing stack cannot solve the problem, (2) it is necessary, (3) keep it isolated.

## Git (Backend)

Keep commits small and logical. Do not use `git reset --hard` unless instructed.

### Commit Authorization

No auto-commits. Do not run `git commit`/`commit --amend`/`push` or create PRs without explicit user confirmation — stage (`git add`) is allowed to prepare a diff.

### Commit Format

```
<prefix>: <descriptive and precise change description>
```

Allowed: `feat`, `fix`, `enhancement`, `refactor`, `chore`, `docs`, `test`, `perf`. Use imperative mood, include phase/task scope, one change per commit. Examples:

- `feat(phase4): implement WebSocket endpoint /ws/v1/translate with session lifecycle and bounded audio queue`
- `feat(phase7): add Whisper STT provider with partial/final transcript per segment`
- `refactor(backend): remove dead mock STT stub after real Whisper provider integration`
- `docs(phase6): update event protocol docs after provider abstraction`

Every phase-advancing commit MUST include its `implementation-plan/phaseN.md` checklist/progress update.

## Canonical Paths

Frontend lives at `frontend/frontend/` (nested per `phase1.md` P1-DEV-001) and backend at `backend/`. Do not combine them.
