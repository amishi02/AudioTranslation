# Phase 3: Frontend Foundation & UI Shell

## Progress

| Status | Count |
|---|---:|
| Completed | 21 |
| Partially Completed | 0 |
| Remaining | 0 |
| Blocked | 0 |
| Total | 21 |

Progress: 100%

Status: Completed

Last Updated: 2026-09-16

Related documentation: `AGENTS.md` (frontend responsibilities), `docs/prd.md` §8-18 (product scope, UI states), `docs/srs.md` §7 (UI requirements), `docs/architecture.md` § System, `docs/trd.md` §6.1/§40

---

## 1. Objective

Establish the React/Vite frontend foundation and the application shell so users can select languages, see connection/session status, view transcript and translation areas (with placeholder content for now), and handle errors — all without WebSocket or microphone logic. The shell must keep WebSocket communication separate from UI components and use JavaScript/JSX only.

## 2. Prerequisites

- Phase 1 complete (frontend scaffold, Vite env, lint/build passing)
- Phase 2 complete (or at least `/health` and `/api/v1/capabilities` available for backend health gating)
- Node 18+, modern browser (Chrome/Edge/Firefox/Safari) for later AudioWorklet support

## 3. Expected Starting State

- `frontend/frontend/src/App.jsx` shows a minimal header shell (from Phase 1)
- `src/{components,hooks,services,config,utils}` skeleton exists but holds no real code
- No language selector, transcript, translation, status, or error components; no health check against backend; no application state separation

## 4. Target State

- Frontend boots with: header, language selectors (source + target), Start/Stop controls (disabled state until health + language validation), connection status indicator, source transcript panel, translation panel, error banner
- `GET /health` and `/api/v1/capabilities` are called on load to display backend availability and populate language options
- Components are presentational; state/hooks are isolated; WebSocket service is a stub (empty hook) ready for Phase 4
- Language validation implements PRD/SRS rules: must select source+target, reject identical pair, reject unsupported combinations
- UI states (idle, connecting, listening, processing, error, disconnected) have distinct visual rendering (PRD §18)
- Accessibility: language selectors are labeled, keyboard-accessible, with focus states and sufficient contrast

## 5. Task Checklist

### Frontend

- [x] P3-FE-001 Create `src/config/environment.js` centralizing `VITE_API_BASE_URL` and `VITE_WS_URL`
- [x] P3-FE-002 Create `src/utils/constants.js` (language codes/names, connection states, session states, error codes)
- [x] P3-FE-003 Create `src/components/LanguageSelector.jsx` (source + target dropdowns, accessible labels, validation)
- [x] P3-FE-004 Create `src/components/ConnectionStatus.jsx` (idle/connecting/listening/processing/error/ready)
- [x] P3-FE-005 Create `src/components/Transcript.jsx` (final segments list + active partial with visual distinction)
- [x] P3-FE-006 Create `src/components/Translation.jsx` (final segments list + active partial mirror of transcript)
- [x] P3-FE-007 Create `src/components/StatusBanner.jsx` (or inline error display) for backend unreachable + unsupported language errors
- [x] P3-FE-008 Create `src/components/AppShell.jsx` layout composing header, language selectors, transcript, translation, controls
- [x] P3-FE-009 Update `src/App.jsx` to mount `AppShell` and application state container
- [x] P3-FE-010 Create `src/hooks/useLanguageSelection.js` (validate pair, derive `canStart`, expose `supportedLanguages` from capabilities)
- [x] P3-FE-011 Create `src/hooks/useSessionState.js` (sessionId, sourceLanguage, targetLanguage, segments, connection, error — without WS wiring)
- [x] P3-FE-012 Create `src/services/api.js` (fetch helpers for `/health` and `/api/v1/capabilities` with typed responses and error envelope handling)
- [x] P3-FE-013 Create stub `src/services/websocket.js` (no real WS yet — exports `createWebSocketClient` returning `{connect, disconnect, status}` stubs)
- [x] P3-FE-014 Create stub `src/hooks/useWebSocket.js` (state machine `disconnected/connecting/ready/failed` with no real socket)
- [x] P3-FE-015 Apply CSS for layout, focus states, status colors, and contrast per PRD §30 (accessibility)

### Integration

- [x] P3-INT-001 Wire `useEffect` on mount to call `/health` + `/api/v1/capabilities` and update `ConnectionStatus` + language options
- [x] P3-INT-002 Gate Start button: disabled unless `canStart === true` (both languages valid, backend healthy); show inline reason text

### Testing

- [x] P3-TEST-001 Add frontend component tests for `LanguageSelector` (valid/invalid pair, identical languages blocked)
- [x] P3-TEST-002 Add frontend tests for `ConnectionStatus` rendering each state
- [x] P3-TEST-003 Add frontend test for `Transcript` segment replacement semantics (partial → partial → final)
- [x] P3-TEST-004 Verify `npm run build` still passes with new components

---

## 6. Detailed Task Instructions

### P3-FE-001 environment.js
- Where: `src/config/environment.js`. Export `export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'` and `WS_URL`. Provide helper `getWsUrl()` that upgrades `http://` to `ws://` when `VITE_WS_URL` not set. Document in code that production uses `wss://`.
- Verify: `import { API_BASE_URL } from './config/environment.js'` renders expected string in dev.

### P3-FE-002 constants.js
- Where: `src/utils/constants.js`. Define `LANGUAGES = [{code:'en', label:'English'}, ...]`, `CONNECTION_STATES = { IDLE:'idle', CONNECTING:'connecting', READY:'ready', LISTENING:'listening', PROCESSING:'processing', ERROR:'error', DISCONNECTED:'disconnected' }`, `SEGMENT_STATUS = {PARTIAL:'partial', FINAL:'final'}`. Later phases will reuse these.
- Verify: Importable; language list length matches capabilities stub.

### P3-FE-003 LanguageSelector.jsx
- Where: `src/components/LanguageSelector.jsx`. Props: `sourceLanguage`, `targetLanguage`, `onSourceChange`, `onTargetChange`, `supportedLanguages`, `disabled`. Renders two `<select>` with `<label>`; disables unsupported combinations if `capabilities` knows them; shows validation message when `source===target` (PRD §15). Keyboard-accessible; focus ring visible.
- Verify: Selecting identical pair shows validation error and `canStart` stays false.

### P3-FE-004 ConnectionStatus.jsx
- Where: `src/components/ConnectionStatus.jsx`. Props: `status`, `error`. Renders distinct text/icon/color for each `CONNECTION_STATES` value per PRD §18 (Idle: "Select languages" + Start button; Connecting: "Connecting..."; Listening; Processing; Error with Try Again). Use `aria-live="polite"` for status region.
- Verify: Changing `status` prop cycles through all visual states correctly.

### P3-FE-005 Transcript.jsx
- Where: `src/components/Transcript.jsx`. Props: `segments: {id, text, status}[]`, `activeSegment`. Renders finalized segments as static lines and active partial as visually distinct (e.g., lighter color + `…` suffix or underline). Internally, component must not create duplicate lines for the same `id` — it renders one line per segment id (placeholder logic that will be reused by real WebSocket handling in Phases 7–8).
- Verify: Given `[{id:1, text:"Hello my name is John.", status:"final"}, {id:2, text:"I work as a", status:"partial"}]` renders two lines with partial styled differently.

### P3-FE-006 Translation.jsx
- Where: `src/components/Translation.jsx`. Props: `segments: {id, sourceText, translatedText, status}[]`, `activeSegment`. Mirrors `Transcript.jsx` semantics. For phase 3, accepts placeholder text; will display real translations after Phase 8.
- Verify: Similar rendering to Transcript but shows translated text.

### P3-FE-008 AppShell.jsx
- Where: `src/components/AppShell.jsx`. Layout matching PRD §8 wireframe: language selectors row, status indicator, two panels (Source Transcript, Translation), Start/Stop button row. Holds no business logic; receives all state/handlers as props. Documented slot order.
- Verify: Visual order matches PRD §8 layout on desktop width.

### P3-FE-010 useLanguageSelection.js
- Where: `src/hooks/useLanguageSelection.js`. State: `sourceLanguage`, `targetLanguage`, `supportedLanguages` (from capabilities), `validationError`. Derived: `canStart = !validationError && source && target && backendHealthy`. Exposes `setSource`, `setTarget`, `loadSupportedLanguages()`. Implements PRD §15 rules (1–5).
- Verify: Hook test sets source=target → `validationError` non-null, `canStart` false.

### P3-FE-011 useSessionState.js
- Where: `src/hooks/useSessionState.js`. Holds `sessionId: null`, `connection: CONNECTION_STATES.IDLE`, `sourceLanguage`, `targetLanguage`, `segments: []`, `activeSegment: null`, `error: null`. Exposes `reset()` and `setConnection()`. No WebSocket yet — pure frontend state.
- Verify: Updating `segments` re-renders `Transcript`/`Translation` correctly.

### P3-FE-012 services/api.js
- Where: `src/services/api.js`. Functions `fetchHealth()`, `fetchCapabilities()` using `fetch(API_BASE_URL + '/health')` with proper error handling (parse `ErrorResponse` envelope if status >=400). Handles network failure with user-friendly message.
- Verify: Browser DevTools Network tab shows successful calls; handling verified when backend is down (error banner appears).

### P3-TEST-003 Transcript segment replacement
- Where: `frontend/frontend/src/__tests__/Transcript.test.jsx` (or `tests/`). Renders `Transcript` with evolving props for same `id` asserting only one active line exists and final line is stable. This test documents the contract used in Phases 7–8 to prevent regression (PRD §11-13).
- Verify: Test asserts final segment not replaced when new partial for different id arrives.

## 7. Architecture / Data Flow

Phase 3 is HTTP-only (no WS yet):

```
Frontend (React)
  AppShell
    ├── LanguageSelector  ←→ useLanguageSelection  ←→ /api/v1/capabilities (once)
    ├── ConnectionStatus  ←→ useSessionState + /health (once)
    ├── Transcript        ←→ segments state (placeholder, no WS)
    ├── Translation       ←→ segments state (placeholder)
    └── StatusBanner      ←→ error state
  services/api.js  →  FastAPI GET /health, /api/v1/capabilities
```

WebSocket/audio hooks are introduced as stubs so Phase 4 can wire them without rewriting shell.

## 8. Files Expected to Be Created/Modified

Frontend:
- `frontend/src/config/environment.js` (new/updated from Phase 1 stub)
- `frontend/src/utils/constants.js` (new)
- `frontend/src/services/api.js` (new)
- `frontend/src/services/websocket.js` (stub, new)
- `frontend/src/hooks/useLanguageSelection.js` (new)
- `frontend/src/hooks/useSessionState.js` (new)
- `frontend/src/hooks/useWebSocket.js` (stub, new)
- `frontend/src/components/LanguageSelector.jsx` (new)
- `frontend/src/components/ConnectionStatus.jsx` (new)
- `frontend/src/components/Transcript.jsx` (new)
- `frontend/src/components/Translation.jsx` (new)
- `frontend/src/components/StatusBanner.jsx` (new)
- `frontend/src/components/AppShell.jsx` (new)
- `frontend/src/App.jsx` (modified: mounts AppShell)
- `frontend/src/App.css` or `index.css` (modified: layout + a11y focus)
- `frontend/src/__tests__/LanguageSelector.test.jsx` (new)
- `frontend/src/__tests__/ConnectionStatus.test.jsx` (new)
- `frontend/src/__tests__/Transcript.test.jsx` (new)

## 9. Testing Requirements

- Component tests: LanguageSelector validation (valid pair, identical pair, unsupported language), ConnectionStatus per-state rendering, Transcript segment semantics (partial replacement, final stability).
- Integration: Frontend successfully fetches `/health` and `capabilities` and populates UI; handles backend-down gracefully.
- Build/Quality: `npm run lint` and `npm run build` still pass.

## 10. Acceptance Criteria

- [x] Language selectors render with accessible labels and validation (identical pair blocked).
- [x] Transcript and Translation panels render final + partial with distinct visuals; no duplication for same `segment_id`.
- [x] Connection status displays all states (idle, connecting, listening, processing, error, disconnected) with appropriate messaging.
- [x] `GET /health` result reflected in status banner (healthy vs backend unreachable).
- [x] Start button is disabled until languages are valid and backend is healthy, with inline reason.
- [x] No TypeScript introduced; all files are JS/JSX per `AGENTS.md`.
- [x] Component tests for language/transcript/status pass; `npm run build` passes.

## 11. Verification Procedure

```bash
# Backend must be running (Phase 2)
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/capabilities

# Frontend
cd frontend/frontend  # or frontend
npm run lint
npm run build
npm run dev -- --host
# Browser checks:
# 1. Open http://localhost:5173 — header, language selectors, transcript/translation panels visible.
# 2. Select source=English, target=Hindi — validation passes; Start becomes enabled.
# 3. Select source==target — validation error shows; Start disabled.
# 4. Stop backend → banner shows "Unable to connect to translation service" with Try Again.
# 5. Tab through UI — focus rings visible, labels announced by screen reader.
```

## 12. Known Limitations

- No WebSocket connection; Start/Stop are wired to future session logic only (buttons may appear enabled but do nothing beyond state changes).
- No microphone, AudioWorklet, or audio capture.
- No real transcripts/translations (placeholder segments only).
- No audio playback.

## 13. Risks / Notes

- **JS only**: Enforce JS/JSX throughout; do not introduce `.ts`/`.tsx`.
- **Keep WebSocket logic out of components**: Phase 3 introduces only stubs; Phase 4–5 will implement them in `services/websocket.js` + `hooks/useWebSocket.js` — guard against reintroducing WS calls inside `AppShell`.
- **Language lists**: Phase 3 uses capabilities response or a minimal hard-coded list; real model-driven language coverage arrives with provider selection in Phases 7–9 — do not over-engineer language negotiation now.

## 14. Phase Completion Status

- Total tasks: 21
- Completed tasks: 21
- Partially completed tasks: 0
- Remaining tasks: 0
- Blocked tasks: 0
- Overall progress: 100%
- Acceptance criteria status: 7 / 7 satisfied

