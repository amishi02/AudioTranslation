# Phase 4: WebSocket Foundation & Session Lifecycle

## Progress

| Status | Count |
|---|---:|
| Completed | 0 |
| Partially Completed | 0 |
| Remaining | 29 |
| Blocked | 0 |
| Total | 29 |

Progress: 0%

Status: Not Started

Last Updated: 2026-09-14

Related documentation: `docs/websocket-protocol.md`, `docs/srs.md` §4-6, §13-19 (session, event protocol), `docs/trd.md` §6.3-6.4, §36-38, `docs/prd.md` §16-17 (translation session, states), `AGENTS.md` (WebSockets are the primary mechanism)

---

## 1. Objective

Implement the documented WebSocket foundation at `/ws/v1/translate` with full session lifecycle (`start → ready → stop → ended`), keep the API layer thin, and isolate session-specific state so every connection owns independent buffers and pipeline handles. This phase introduces bidirectional JSON+binary framing, bounded queues/backpressure, disconnect cleanup, and normalized server→client events — but no real audio processing or model logic.

## 2. Prerequisites

- Phases 1–3 complete (modular FastAPI app, HTTP health/capabilities, React shell with backend health gating)
- `backend/app/{services,providers,schemas}` directories exist (even if stubbed)
- Browser supports WebSocket; `uvicorn --ws websockets` (already in `requirements.txt`)

## 3. Expected Starting State

- Frontend has `services/websocket.js` and `hooks/useWebSocket.js` stubs with no real socket
- Backend has empty `backend/app/api/websocket.py` and no session service
- HTTP endpoints from Phase 2 work; no WebSocket route registered
- Frontend Start/Stop buttons are gated by language validation + backend health but don't open a socket

## 4. Target State

- WebSocket endpoint `GET /ws/v1/translate` accepts `session.start` → validates config → creates `TranslationSession` → emits `session.ready` (and optionally `session.started` alias)
- Server supports: JSON control frames (`session.start`, `session.stop`, `ping`), binary audio frames, and malformed-message handling with `error` events
- Each session owns a bounded `asyncio.Queue(maxsize=64)` for incoming audio, independent `receive`/`process`/`send` tasks, and a unique `session_id` (uuid4)
- Client `services/websocket.js` implements `connect(wsUrl, {onEvent, onBinary})`, `sendJson()`, `sendAudio(ArrayBuffer)`, `disconnect()` with reconnect helper and connection state machine (`disconnected|connecting|connected|failed`)
- Hook `useWebSocket` drives the session lifecycle: `session.start` on Start, `session.stop` on Stop, handles all server events into `useSessionState`
- Unexpected disconnect (client or server) triggers deterministic cleanup (cancel pipeline tasks, drop audio queue, remove session from manager)
- All behavior covered by backend WebSocket integration tests using mock model (no real STT yet) and is load-test safe for ~10 concurrent sessions at this mock level

## 5. Task Checklist

### WebSocket / Backend

- [ ] P4-WS-001 Create `backend/app/api/websocket.py` router with `GET /ws/v1/translate` handler (thin: validate, delegate to session service, loop)
- [ ] P4-WS-002 Accept and validate JSON control frames: `type: "start"` with `source_language`, `target_language` (reject invalid JSON)
- [ ] P4-WS-003 Generate `session_id` (uuid4 hex short/long) and create `TranslationSession` via `SessionService`
- [ ] P4-WS-004 Validate session config: both languages present, supported combination (stub allowlist from config), source != target unless explicitly allowed
- [ ] P4-WS-005 Emit `session.ready` (and `connected` alias if documented) after session creation succeeds
- [ ] P4-WS-006 Accept binary audio frames (bytes) and route to session's bounded audio queue (drop/signal backpressure, not crash)
- [ ] P4-WS-007 Accept JSON `type: "stop"`; trigger session finalization and emit `session.ended`
- [ ] P4-WS-008 Implement bounded `asyncio.Queue(maxsize=64)` per session with configurable size from `settings.audio_queue_maxsize`
- [ ] P4-WS-009 Create independent `receive_task`, `processor_task` (stub: consume queue, echo no-op), `send_task` pattern
- [ ] P4-WS-010 Implement backpressure handling: on queue full, drop oldest or return `error` `RATE_LIMITED` without disconnecting
- [ ] P4-WS-011 Handle malformed JSON, invalid `type`, missing fields → emit normalized `error` event with `code` & `message`, keep connection open where recoverable
- [ ] P4-WS-012 Handle `WebSocketDisconnect` and server-side exceptions — guarantee cleanup via `finally` block
- [ ] P4-WS-013 Enforce payload limits (`max_audio_frame_bytes`, `max_json_bytes`) from config; oversize → `INVALID_AUDIO_DATA`/`INVALID_MESSAGE`

### Backend / Session Service

- [ ] P4-BE-001 Create `backend/app/services/session_service.py` (`SessionService` class, not globals) with `create_session`, `get_session`, `end_session`, `cleanup_on_disconnect`
- [ ] P4-BE-002 Define `backend/app/schemas/websocket.py` Pydantic models for `SessionStart`, `SessionStop`, `ServerEvent` union (session.started/ready, transcript, translation, audio markers, error, session.ended)
- [ ] P4-BE-003 Define `backend/app/models/session.py` (or `domain/session.py`) `TranslationSession` dataclass with `session_id`, `source_language`, `target_language`, `state`, `audio_queue`, `created_at`, `segment_counter`
- [ ] P4-BE-004 Integrate `SessionService` with FastAPI dependency injection (singleton `session_service` instance or per-app state `app.state.sessions`)
- [ ] P4-BE-005 Add session lifecycle state machine: `connecting → ready → listening → processing → ending → ended/failed` (PRD §17)
- [ ] P4-BE-006 Add structured logging for `session_created`, `websocket_connected`, `session_ended`, `websocket_disconnected` with `session_id`

### Frontend

- [ ] P4-FE-001 Implement `src/services/websocket.js` — real WebSocket client: `connect()`, `sendSessionStart()`, `sendAudio(buffer)`, `sendStop()`, `disconnect()`, `on('event', cb)`, reconnect stub
- [ ] P4-FE-002 Implement `src/hooks/useWebSocket.js` — state machine `disconnected|connecting|connected|active|ending|error` + `sessionId`; exposes `startSession(langs)`, `stopSession()`, `sendAudio()`
- [ ] P4-FE-003 Wire `src/hooks/useSessionState.js` to receive server events (`session.ready`, `error`, `session.ended`) from the WS hook
- [ ] P4-FE-004 Update `src/components/ConnectionStatus.jsx` to reflect live WS status (not just HTTP health)
- [ ] P4-FE-005 Implement WS error display via `src/components/StatusBanner.jsx` mapping `error.code` → user-friendly messages

### Testing

- [ ] P4-TEST-001 WebSocket test: client connects and receives `session.ready` after valid `session.start`
- [ ] P4-TEST-002 WebSocket test: invalid `session.start` (missing language, identical languages) → `error` `INVALID_SESSION_CONFIG`/`UNSUPPORTED_LANGUAGE`
- [ ] P4-TEST-003 WebSocket test: binary audio frames accepted and queued (no crash)
- [ ] P4-TEST-004 WebSocket test: `session.stop` → `session.ended`; subsequent audio after stop is rejected
- [ ] P4-TEST-005 WebSocket test: malformed JSON and oversize frame handling (no server crash, correct `error` codes)
- [ ] P4-TEST-006 WebSocket test: disconnect triggers cleanup (session removed, tasks cancelled)

---

## 6. Detailed Task Instructions

### P4-WS-001 WebSocket endpoint skeleton
- Where: `backend/app/api/websocket.py`:
  ```python
  from fastapi import APIRouter, WebSocket, WebSocketDisconnect
  router = APIRouter()
  @router.websocket("/ws/v1/translate")
  async def translate_ws(websocket: WebSocket): ...
  ```
  Mount via `app.include_router(ws_router)` or direct `app.add_websocket_route` inside `create_app()`.
- Thin rule: handler only does: `await websocket.accept()`, enters `try` with `receive_task` loop, delegates `start/stop/audio` to `session_service`. No direct provider/model calls here.
- Verify: `wscat -c ws://localhost:8000/ws/v1/translate` connects (expect WS upgrade 101).

### P4-WS-002 JSON control validation
- Where: inside `receive_task` loop: `msg = await websocket.receive()` — if `msg['type']=='websocket.receive'` with `text`, parse JSON; validate `type in ('start','stop','ping')`. Use `SessionStart.model_validate_json(text)` for typed parsing. On `JSONDecodeError` → `await websocket.send_json({type:"error", code:"INVALID_MESSAGE", message:"Invalid JSON frame"})` and continue.
- Verify: Sending `{"type":"start"}` with missing fields produces `error` not exception.

### P4-WS-003 Session creation
- Where: `session_id = uuid.uuid4().hex[:12]` (or full). `session = await session_service.create_session(session_id, source_language, target_language, websocket)` then `await websocket.send_json({type:"session.ready", session_id, source_language, target_language})` (also send `session.started` alias if frontend expects both). Log `session_created`.
- Verify: Client receives `session.ready` with matching `session_id` and echo of languages.

### P4-WS-006 Binary audio queuing
- Where: When `bytes` key in received message, do `try: session.audio_queue.put_nowait(frame_bytes) except asyncio.QueueFull: await websocket.send_json({type:"error", code:"RATE_LIMITED", message:"Audio queue full, dropping chunk"})`. Record dropped count on session; optionally drop oldest chunk and enqueue new one (document policy).
- Verify: Flooding 64+ frames does not crash process; error or drop observed.

### P4-WS-009 Receive/process/send pattern
- Where: Inside handler create three tasks:
  - `recv_loop`: `while True: msg = await websocket.receive()` dispatching to queue/control.
  - `processor_loop`: `while True: frame = await session.audio_queue.get()` — for Phase 4 this just discards or counts bytes (real processing deferred to Phase 6 pipeline). Must be cancelled on disconnect.
  - Lifecycle `await asyncio.gather(recv_loop, processor_loop)` with `try/except` → cleanup.
- Why: Prevents `receive()` blocking from halting processing; allows backpressure.
- Verify: Session remains responsive to `session.stop` while flooding audio.

### P4-BE-001 SessionService
- Where: `backend/app/services/session_service.py`. Class holds `self._sessions: dict[str, TranslationSession]` behind `asyncio.Lock`. Methods:
  - `create_session(id, src, tgt, ws)` validates, creates `TranslationSession`, registers, returns it.
  - `get_session(id)` → session or None.
  - `end_session(id)` → cancel processor task, drain queue, set state `ENDED`, delete entry.
  - `cleanup_on_disconnect(ws)` → find session bound to ws, call `end_session`.
- Verify: Importable; used via DI singleton `session_service = SessionService()` passed to handler.

### P4-BE-002 Schemas
- Where: `backend/app/schemas/websocket.py`. Define `SessionStart(BaseModel): type: Literal["start"]; source_language: str; target_language: str` with field validators normalizing `lower().strip()`. Define `ServerEvent` as `Annotated[Union[...], Field(discriminator="type")]` with `ErrorEvent`, `SessionReadyEvent({type:"session.ready", session_id})`, `SessionEndedEvent`. Align field names with `docs/websocket-protocol.md` (Phase 4 keeps both `session.ended` style and `type`-discriminated style). Export `translate_lang_pair_is_supported()` helper using `settings.supported_languages` stub.
- Verify: `SessionStart.model_validate({'type':'start','source_language':'en','target_language':'hi'})` succeeds.

### P4-FE-001 services/websocket.js
- Where: `src/services/websocket.js`. Export factory:
  ```js
  export function createWebSocketClient(wsUrl, { onEvent, onError, onBinary }) {
    let ws=null;
    return {
      connect() { ws=new WebSocket(wsUrl); ws.onopen=...; ws.onmessage=(e)=> { if (e.data instanceof Blob) onBinary(e.data); else onEvent(JSON.parse(e.data)); } },
      sendJson(o){ if(ws?.readyState===1) ws.send(JSON.stringify(o)); },
      sendAudio(buf){ if(ws?.readyState===1) ws.send(buf); },
      disconnect(){ try{ws?.close();}catch{} ws=null; }
    }
  }
  ```
  Support both JSON events and binary frames (Phase 5 binary path). Do not implement audio capture here.
- Verify: Chrome console `client.connect(); client.sendJson({type:'start',...})` receives `session.ready`.

### P4-FE-002 hooks/useWebSocket.js
- Where: `src/hooks/useWebSocket.js`. State: `status`, `sessionId`, `error`, `lastEvent`. Methods mirror `services/websocket.js` but expose typed triggers: `startSession({sourceLanguage, targetLanguage})`, `stopSession()`, `sendAudio(buffer)`. Handle `onEvent` mapping: `session.ready` → `setSessionId`, `error` → `setError`, `session.ended` → `setStatus('idle')`.
- Dependencies: Uses `useSessionState` dispatch (or passed callbacks). Keep WS logic out of `AppShell`.
- Verify: Clicking Start triggers `session.start`, status shows "Connecting..." → "Ready" then "Listening" when needed.

### P4-TEST-001..006 WebSocket tests
- Where: `backend/tests/test_websocket.py` (new). Use `from fastapi.testclient import TestClient; from app.main import app; client=TestClient(app); with client.websocket_connect("/ws/v1/translate") as ws: ...`. Cover: happy path, invalid config, malformed JSON, oversize frame, stop, disconnect cleanup. Use `pytest.mark.asyncio` if switching to `httpx.AsyncClient` — prefer `TestClient` for simplicity.
- Verify: All pass without model dependencies.

## 7. Architecture / Data Flow

Phase 4 establishes the bidirectional WebSocket skeleton:

```
Browser (services/websocket.js)
  ── JSON {type:"start", source_language, target_language} ──→  FastAPI api/websocket.py (receive_task)
                                                                    ↓
                                                            services/session_service.py
                                                                    ↓
                                                            models/session.py (audio_queue)
                                                                    ↓
                                                            processor_loop (stub, queue drain)
                                                                    ↓
  ←── JSON {type:"session.ready", session_id} ──────────────────────┘
  ←── JSON {type:"error", code, message}  (on invalid message / backpressure)
  ── binary PCM chunk ──→ audio_queue ──→ (stub drop)
  ── JSON {type:"stop"} ──→ session.ended + cleanup
```

Later phases plug `Pipeline` into `processor_loop` without changing this gateway.

## 8. Files Expected to Be Created/Modified

Backend:
- `backend/app/api/websocket.py` (new: route handler, receive/process/send tasks)
- `backend/app/services/session_service.py` (new)
- `backend/app/models/session.py` (new: `TranslationSession` dataclass)
- `backend/app/schemas/websocket.py` (new/expanded: `SessionStart/Stop`, `ServerEvent` union)
- `backend/app/core/config.py` (modified: `audio_queue_maxsize`, `max_audio_frame_bytes`, `max_json_bytes`, `ws_v1_path`)
- `backend/app/main.py` (modified: mounts WebSocket route, injects SessionService singleton)
- `backend/tests/test_websocket.py` (new)

Frontend:
- `frontend/src/services/websocket.js` (modified: real client implementation)
- `frontend/src/hooks/useWebSocket.js` (modified: state machine + lifecycle)
- `frontend/src/hooks/useSessionState.js` (modified: receives session.ready/error/ended events)
- `frontend/src/components/ConnectionStatus.jsx` (modified: maps WS statuses)
- `frontend/src/components/StatusBanner.jsx` (modified: maps WS error codes)

## 9. Testing Requirements

- Backend WS integration (6 tests listed): happy path, invalid config, binary queuing, stop, malformed/oversize handling, disconnect cleanup.
- Backend unit: `SessionService` create/get/end; schema validators (`SessionStart` normalization, invalid rejection).
- Frontend: `useWebSocket` state transitions (disconnected→connecting→connected→active→ending→idle) and error mapping — mocked WebSocket if needed.
- No model/audio tests yet; no E2E audio path in this phase.

## 10. Acceptance Criteria

- [ ] WS `GET /ws/v1/translate` accepts connections (upgrade 101).
- [ ] Valid `session.start` → `session.ready` with `session_id` echo and language validation.
- [ ] Invalid/malformed messages return normalized `error` events with stable `code` values (no server crash).
- [ ] Binary audio frames are accepted into per-session bounded queue; queue-full emits `RATE_LIMITED` (or documented drop policy), connection stays open.
- [ ] `session.stop` → `session.ended` and session is removed from manager.
- [ ] Unexpected disconnect (client close or server exception) reliably cleans up session and cancels processor task.
- [ ] Frontend `services/websocket.js` + `hooks/useWebSocket.js` correctly drive `session.start`/`stop` and reflect status in UI.
- [ ] All new WS tests pass; lint/type checks still green.

## 11. Verification Procedure

```bash
cd backend
uvicorn app.main:app --reload --port 8000 &
sleep 2
python -m pytest tests/test_websocket.py -q

# Manual WS smoke — use wscat or Python helper
pip install websocket-client  # if needed
python - << 'PY'
import websocket, json, time
ws = websocket.create_connection("ws://localhost:8000/ws/v1/translate")
ws.send(json.dumps({"type":"start","source_language":"en","target_language":"hi"}))
print(ws.recv())  # expect session.ready
ws.send(b"\x00\x01\x02" * 100)  # binary chunk
ws.send(json.dumps({"type":"stop"}))
print(ws.recv())  # expect session.ended
ws.close()
print("ws manual ok")
PY

# Frontend
cd ../frontend/frontend
npm run dev -- --host
# Browser: select languages, click Start → status Connecting→Ready; Stop → status Idle; send invalid pair → error banner.
```

## 12. Known Limitations

- No real audio processing, STT, translation, or TTS — `processor_loop` is a stub that drains/uploads count.
- Binary frames are not yet fed by real browser audio (that arrives in Phase 5).
- `session.ready` vs `session.started` naming alias may need reconciliation; document choice in code.
- Language allowlist is config stub (real allowlist from model capabilities in Phases 7–9).

## 13. Risks / Notes

- **Backpressure policy**: Must be explicit and documented (drop-oldest, drop-newest, or block with `RATE_LIMITED`). Blocking `put()` would stall the receive loop — always use `put_nowait` + explicit handling.
- **Thin API rule**: `api/websocket.py` must not contain provider/model code; if it does, later pipeline swaps require WS-layer changes — enforce via code review + `AGENTS.md`.
- **Three-task pattern** is essential for real-time: receive (network I/O), process (pipeline), send (events) must be independent asyncio tasks — single-loop would defeat concurrency under load.
- **Session isolation**: No global audio buffer; every session owns its `audio_queue` and `processor_task`.
- **Assume `ws://` local, `wss://` prod**: Document production TLS expectation; do not hard-code.

## 14. Phase Completion Status

- Total tasks: 29
- Completed tasks: 0
- Partially completed tasks: 0
- Remaining tasks: 29
- Blocked tasks: 0
- Overall progress: 0%
- Acceptance criteria status: 0 / 8 satisfied

