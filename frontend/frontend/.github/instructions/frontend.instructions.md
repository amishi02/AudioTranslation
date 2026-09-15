---
applyTo: "frontend/**/*.{js,jsx}"
---

# Frontend Instructions

Follow the root `AGENTS.md` and the active `implementation-plan/phaseN.md`. `AGENTS.md` and `docs/` are authoritative; this file only mirrors frontend-relevant rules for Copilot.

## Stack

Use **React + Vite + JavaScript + JSX**. Do **not** introduce TypeScript unless `docs/` / the phase file explicitly requires it.

## Responsibilities & Separation

- Microphone access, audio capture, audio playback, WebSocket connection, sending audio, receiving transcription/translation, displaying connection state and source/translated text, frontend error handling.
- Keep **WebSocket communication separate from UI components** — put WebSocket logic in dedicated `services/` / `hooks/` (e.g., `services/websocket.js`, `hooks/useWebSocket.js`, `hooks/useAudioRecorder.js`), not inside `App.jsx`.
- Isolate audio recording/playback logic from UI components.
- Do not put the entire application inside `App.jsx`; reuse existing `components/` and `services/` before creating duplicates.

## Implementation Plan Compliance

- Before touching `frontend/`, read `AGENTS.md` § Implementation Plan Workflow, then `implementation-plan/README.md` and the target `phaseN.md`. Implement strictly in checklist order (`P<phase>-FE-*` / `P<phase>-INT-*`), respecting `Depends on:`.
- After each frontend implementation pass:
  1. Update the phase file checklist: `[x]` completed (implemented **and** verified) / `[~]` partial / `[!]` blocked with reason. Do NOT mark `[x]` before running the phase's Verification Procedure.
  2. Update the phase's `## Progress` table and Acceptance Criteria; add newly discovered tasks with unique IDs; update `implementation-plan/README.md` if needed.
  3. **Remove dead code:** unused components, hooks, services, commented blocks, unreachable branches, and temporary scaffolding that the phase replaced. Verify with `npm run lint` and `npm run build` (no dead references).
  4. **Sync docs:** if frontend behavior or the WebSocket event protocol diverges, update `docs/websocket-protocol.md`, `docs/architecture.md`, or add a doc note; keep `implementation-plan/README.md` architecture flow accurate.
- Keep frontend code **independent of backend code** — canonical frontend path is `frontend/frontend/` (nested per `phase1.md` P1-DEV-001).

## Code Quality

- Keep components and hooks focused; avoid premature abstraction.
- Use `VITE_API_BASE_URL` / `VITE_WS_URL` from `frontend/frontend/.env.example` (copy to local `.env`, never commit it) for backend/WS URLs.
- Handle errors explicitly; display connection, microphone-permission, and translation states clearly to the user.

## Testing

Cover important application behavior with frontend tests alongside implementation. Do not mark frontend tasks `[x]` until `npm run lint` and `npm run build` (and any phase-specified `npm test` / Vitest) pass.

## Git (Frontend)

Keep commits small and logical. Do not use `git reset --hard` unless instructed.

### Commit Authorization

No auto-commits. Do not run `git commit`/`commit --amend`/`push` or create PRs without explicit user confirmation — `git add` only to prepare a diff.

### Commit Format

```
<prefix>: <descriptive and precise change description>
```

Allowed: `feat`, `fix`, `enhancement`, `refactor`, `chore`, `docs`, `test`, `perf`. Use imperative mood, include phase/task scope, one change per commit. Examples:

- `feat(phase3): add language selector and transcript/translation shell with Vite env handling`
- `feat(phase5): add browser AudioWorklet pipeline with PCM S16LE mono 16kHz chunking and binary streaming`
- `refactor(frontend): remove unused audio playback stub after TTS provider swap`
- `docs(phase3): update UI shell docs after frontend foundation`

Every phase-advancing commit MUST include its `implementation-plan/phaseN.md` checklist/progress update.

## Dependencies

Do not add a frontend dependency because it is popular. Prefer the existing React/Vite/WebSocket API before introducing a new package; keep new deps isolated.
