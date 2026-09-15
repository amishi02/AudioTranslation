# Repository Instructions

Read and follow the root `AGENTS.md` before making changes. `AGENTS.md` is the authoritative source of truth; this file only mirrors it for GitHub Copilot.

## Project Objective

Build an end-to-end real-time audio translation application. Phase 1 focuses only on core real-time audio translation. Authentication, user management, database persistence, billing, and other user-specific functionality are deferred to later phases.

## Repository Structure

- `frontend/` — React + Vite + JavaScript + JSX (canonical app at `frontend/frontend/` — see AGENTS.md / phase1.md P1-DEV-001). Do not combine frontend and backend code.
- `backend/` — Python + FastAPI + WebSockets
- `docs/` — authoritative product / architecture docs (BRD, PRD, SRS, TRD, websocket-protocol, etc.)
- `implementation-plan/` — phased, implementation-ready roadmap (`README.md` + `phase1.md` … `phaseN.md`, sibling to `docs/`)

## General Guidelines

- Read `AGENTS.md`, then the relevant `docs/` file(s), then `implementation-plan/README.md` and the target `phaseN.md` before implementing.
- Follow existing architecture rather than introducing a new architecture for individual features.
- Keep frontend and backend independent.
- Do not introduce authentication, databases, Redis, or Celery during Phase 1 unless explicitly requested (see `docs/architecture.md` and `AGENTS.md` Database / Real-Time Architecture).
- Use JavaScript/JSX on the frontend (no TypeScript); use type hints + Pydantic on the backend.

## Implementation Plan Workflow

The authoritative phased roadmap is `implementation-plan/`:

```
implementation-plan/
├── README.md
├── phase1.md
├── phase2.md
├── ...
└── phaseN.md
```

Each phase file contains objective, prerequisites, task checklist with unique IDs (`P<phase>-<category>-<number>`), detailed instructions, architecture flow, acceptance criteria, and verification procedure.

1. **Implement strictly from the plan.** Execute tasks in checklist order, respecting `Depends on:`. Do not redesign the architecture or introduce technologies not required by `docs/` + the phase file.
2. **Maintain checklist state:** `[ ]` Not started · `[x]` Completed (implemented AND verified) · `[~]` Partially completed · `[!]` Blocked (document reason in phase file). Do NOT mark `[x]` without verification via the phase's Verification Procedure.
3. **Update after every implementation pass:**
   - Mark tasks `[x]`/`[~]`/`[!]`.
   - Update the `## Progress` table (Completed / Partially / Remaining / Blocked / Total, `Progress: XX%`, `Status`, `Last Updated`).
   - Update Acceptance Criteria checkboxes.
   - Add newly discovered tasks with new IDs; never silently delete unfinished tasks.
   - Update `implementation-plan/README.md` Phase Overview + Overall Progress.
4. **Remove dead code** after each phase/increment: unused files, commented blocks, unreachable branches, replaced placeholder mocks (keep `mock` providers only behind env switches where the plan requires), unused imports/stale env keys/orphaned tests. Verify with `ruff check`, `mypy`, `npm run lint` / `npm run build`.
5. **Keep documentation in sync:** update the phase file's Known Limitations / Risks / Notes if behavior diverges; if system behavior changes, update `docs/` or add an ADR under `docs/adr/`; ensure `implementation-plan/README.md` still describes the actual system.
6. **Verification is mandatory** per the phase's Phase Completion Rule — tests, linting, and manual verification must pass before considering the phase complete.

## Git

Keep commits small and logical. Never discard user changes. Do not use `git reset --hard` unless explicitly instructed.

### Commit Authorization

Agents MUST NOT run `git commit`, `git commit --amend`, `git push`, or create PRs without explicit user confirmation in the current session. Before committing, present `git status` and `git diff --staged` (or full diff if not yet staged), state the proposed message and what it does, then wait for an explicit "yes" / "commit" / "proceed".

Staging (`git add`) is allowed only to prepare a diff for review.

### Commit Format

All implementation-plan commits MUST use:

```
<prefix>: <descriptive and precise change description>
```

Allowed prefixes: `feat`, `fix`, `enhancement`, `refactor`, `chore`, `docs`, `test`, `perf`
- Use imperative mood, include phase/task scope where relevant, one logical change per commit.
- Examples:
  - `feat(phase4): implement WebSocket endpoint /ws/v1/translate with session lifecycle and bounded audio queue`
  - `feat(phase5): add browser AudioWorklet pipeline with PCM S16LE mono 16kHz chunking and binary streaming`
  - `fix(websocket): handle malformed JSON frames with INVALID_MESSAGE error without disconnecting`
  - `refactor(backend): remove dead mock STT stub after real Whisper provider integration`
  - `docs(phase6): update event protocol and pipeline docs after provider abstraction`
  - `test(phase7): add streaming STT integration tests for partial/final transcript per segment`

Each commit that advances a phase MUST be accompanied by the corresponding `implementation-plan/phaseN.md` checklist/progress update.

## Code Quality

Type hints, Pydantic, focused functions/classes, no unnecessary abstractions, dependency injection where appropriate, explicit error handling, no secrets, env vars via `.env.example`, structured logging (never log raw audio).

## Testing

Add tests alongside significant functionality (services, provider integrations where practical, WebSocket behavior, error handling on backend; important app behavior on frontend). Do not mark tasks `[x]` without running tests.
