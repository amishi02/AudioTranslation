# Real-Time Audio Translation

## Project Objective

Build an end-to-end real-time audio translation application.

The first development phase focuses only on the core real-time
audio translation functionality.

Authentication, user management, database persistence, billing,
and other user-specific functionality will be added in later phases.

## Repository Structure

The repository contains two independent applications:

- frontend: React application
- backend: Python FastAPI application

Do not combine frontend and backend code.

## Frontend

Technology:

- React
- Vite
- JavaScript
- JSX
- WebSocket API

Use JavaScript, not TypeScript.

Frontend responsibilities:

- microphone access
- audio capture
- audio playback
- WebSocket connection
- sending audio to backend
- receiving transcription
- receiving translations
- displaying connection state
- displaying source and translated text
- handling frontend errors

Keep WebSocket communication separate from UI components.

## Backend

Technology:

- Python
- FastAPI
- WebSockets

Backend responsibilities:

- WebSocket connection management
- receiving audio
- audio processing
- speech-to-text
- translation
- text-to-speech
- sending results back to the client

Keep API/WebSocket handlers thin.

Business and processing logic must live in services.

External AI/provider integrations must be isolated behind provider
interfaces or service classes.

## Backend Architecture

Use the following conceptual layers:

api
services
providers
models
schemas
core
utils

Responsibilities:

api:
    FastAPI routes and WebSocket endpoints.

services:
    Application/business logic.

providers:
    External STT, translation and TTS implementations.

models:
    Domain/data models required by the application.

schemas:
    Pydantic request/response schemas and internal data structures.

core:
    Application configuration and shared infrastructure.

utils:
    Small reusable utility functions.

Do not put business logic directly inside API endpoints.

## Real-Time Architecture

WebSockets are the primary communication mechanism for real-time
audio processing.

The real-time pipeline is:

Client
    -> WebSocket
    -> Audio Processing
    -> Speech-to-Text
    -> Translation
    -> Text-to-Speech
    -> WebSocket
    -> Client

Do not introduce Celery or Redis into the real-time processing path.

Do not introduce a database during the initial implementation.

## Authentication

Authentication is intentionally excluded from Phase 1.

Do not implement:

- registration
- login
- JWT
- sessions
- users
- permissions
- user profiles

The authentication layer will be introduced in a later phase.

The architecture should remain modular enough that authentication
can be added without rewriting the audio-processing pipeline.

## Database

There is intentionally no database in Phase 1.

Do not introduce PostgreSQL, SQLite, MongoDB or another database
unless explicitly requested.

## Code Quality

Follow production-quality engineering practices.

- Use type hints in Python.
- Use Pydantic for structured data.
- Keep functions focused.
- Keep classes focused on one responsibility.
- Avoid unnecessary abstractions.
- Use dependency injection where appropriate.
- Handle errors explicitly.
- Do not expose secrets.
- Never hardcode API keys.
- Use environment variables for configuration.
- Do not commit .env files.
- Use structured logging where appropriate.

## Testing

Tests should be added alongside significant functionality.

Backend tests should cover:

- services
- provider integrations where practical
- WebSocket behavior
- error handling

Frontend tests should cover important application behavior.

## Dependencies

Do not add a dependency simply because it is popular.

Before introducing a new package:

1. Determine whether the existing stack can solve the problem.
2. Determine whether the dependency is necessary.
3. Keep the dependency isolated where possible.

## Development Workflow

Before implementing a feature:

1. Read AGENTS.md.
2. Read the relevant documentation under docs/.
3. Inspect the existing implementation.
4. Plan the change.
5. Implement the smallest appropriate change.
6. Run tests.
7. Run linting/formatting.
8. Verify the application starts successfully.

Do not rewrite unrelated code.

Do not change architectural decisions without explicitly documenting
the reason.

## Implementation Plan Workflow

The authoritative phased roadmap lives in `implementation-plan/` (sibling to `docs/`):

```
implementation-plan/
├── README.md
├── phase1.md
├── phase2.md
├── ...
└── phaseN.md
```

Each phase file is a living progress tracker and contains: objective, prerequisites, task checklist with unique IDs (`P<phase>-<category>-<number>`), detailed instructions, architecture flow, acceptance criteria, and verification procedure.

### Rules

1. **Implement strictly from the plan.** When instructed to implement a phase (e.g., "Implement Phase 3"), read that phase file top-to-bottom and execute tasks in checklist order, respecting any `Depends on:` annotations. Do not redesign the architecture or introduce technologies not required by `docs/` and the phase file.

2. **Checklist state must be maintained.** Every task uses one of:
   - `[ ]` Not started
   - `[x]` Completed (implemented AND verified)
   - `[~]` Partially completed
   - `[!]` Blocked (with reason documented in the phase file)

   Do NOT mark `[x]` unless the implementation has been verified (tests/linting/manual verification per the phase's Verification Procedure).

3. **Update after every implementation pass.** Immediately after implementing tasks from a phase:
   - Mark completed tasks `[x]`, partially completed `[~]`, blocked `[!]`.
   - Update the `## Progress` table at the top of the phase file (Completed / Partially Completed / Remaining / Blocked / Total, `Progress: XX%`, `Status`, `Last Updated: YYYY-MM-DD`).
   - Update Acceptance Criteria checkboxes to reflect what is now satisfied.
   - If implementation revealed missing tasks, add them with new unique IDs. Never silently delete unfinished tasks.
   - Update `implementation-plan/README.md` Phase Overview + Overall Progress tables.

4. **Remove dead code after each implementation.** After each phase or logical increment:
   - Delete unused files, commented-out blocks, unreachable branches, and placeholder mocks that have been replaced (keep `mock` providers behind env switches where the plan requires them).
   - Remove unused imports, stale env keys, and orphaned tests/fixtures.
   - Verify with `ruff check`, `mypy`, and frontend `npm run lint` / `npm run build` that no dead references remain.

5. **Keep documentation in sync.** After each implementation:
   - Update the relevant phase file's Known Limitations / Risks / Notes if behavior diverges from the plan and explain why.
   - If the change affects system behavior, update `docs/` (e.g., `docs/websocket-protocol.md`, `docs/architecture.md`, `docs/srs.md`, `docs/trd.md`) or add an ADR under `docs/adr/`.
   - Ensure `implementation-plan/README.md` Architecture Progression and How to Use sections still accurately describe the actual system.

6. **Verification is mandatory.** Do not consider a phase complete until its Verification Procedure has been executed, required tests pass, and acceptance criteria are satisfied per the Phase Completion Rule defined in each phase file.

## Git

Keep commits small and logical.

Never discard existing user changes.

Do not use:

git reset --hard

unless explicitly instructed.

### Commit Format

All commits for implementation-plan work MUST use the following format:

```
<prefix>: <descriptive and precise change description>
```

Allowed prefixes:

- `feat` — new feature or phase implementation
- `fix` — bug fix
- `enhancement` — improvement to existing functionality
- `refactor` — code restructuring without behavior change (includes dead-code removal)
- `chore` — tooling, config, dependencies, scaffolding
- `docs` — documentation only (docs/, implementation-plan/, README)
- `test` — tests only
- `perf` — performance optimization

Rules:

- Description must be specific and precisely reflect what changed (include phase/task scope where relevant).
- Use imperative mood (e.g., "add", "implement", "remove", not "added" or "adds").
- One logical change per commit; do not bundle unrelated phases.
- Examples:
  - `feat(phase4): implement WebSocket endpoint /ws/v1/translate with session lifecycle and bounded audio queue`
  - `feat(phase5): add browser AudioWorklet pipeline with PCM S16LE mono 16kHz chunking and binary streaming`
  - `fix(websocket): handle malformed JSON frames with INVALID_MESSAGE error without disconnecting`
  - `refactor(backend): remove dead mock STT stub after real Whisper provider integration`
  - `docs(phase6): update event protocol and pipeline docs after provider abstraction`
  - `test(phase7): add streaming STT integration tests for partial/final transcript per segment`

Each commit that completes or advances a phase MUST be accompanied by the corresponding `implementation-plan/phaseN.md` checklist/progress update in the same commit (or an immediately following `docs:` commit if splitting is necessary).