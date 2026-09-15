# Phase 6: Provider Abstractions, Mocks & Event Normalization

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

Related documentation: `docs/trd.md` §23-25 (provider abstraction, model adapter, selection), `docs/srs.md` §10 (translation architectures), `docs/Translation.md` §16-18 (model adapter, event protocol), `docs/websocket-protocol.md`, `AGENTS.md` (external integrations behind provider/service interfaces)

---

## 1. Objective

Establish the stable provider/model abstraction layer and the common normalized event protocol, backed by lightweight mock providers so every WebSocket, pipeline, and UI contract can be validated without loading real model weights. By end of Phase 6, the entire system runs end-to-end on mocks: audio → mock STT → mock translation → mock TTS events → UI.

## 2. Prerequisites

- Phases 4–5 complete: WebSocket lifecycle + browser audio streaming + backend audio queue
- Phase 1 configuration (`PIPELINE_TYPE`, provider envs) placeholders exist
- Familiarity with cascading vs unified distinction (TRD §8-22, Translation.md §4/11)

## 3. Expected Starting State

- `backend/app/providers/{stt.py, translator.py, tts.py}` exist but are empty stubs
- Pipeline interface undefined; no `PipelineFactory`
- Server events are ad-hoc (`session.ready`, `error`, `session.ended`) with no `transcript`/`translation` shape
- Frontend expects eventual `transcript`/`translation` events but never receives them
- No mock providers, no event normalizer, no model configuration selection

## 4. Target State

- Base provider interfaces defined: `STTProvider`, `TranslationProvider`, `TTSProvider`, `UnifiedSpeechTranslationProvider` (per TRD §23-24) plus `BaseProvider` lifecycle (`initialize`, `is_ready`, `close`)
- Lightweight mock providers implement all interfaces with deterministic, testable behavior (e.g., feed 4 fake words per ~5 audio chunks, generate partial→final transcript, translate mock)
- Common normalized event types emitted regardless of underlying model: `transcript {session_id, segment_id, status, text}`, `translation {session_id, segment_id, status, source_text, translated_text}`, `error {code, message}`, `session.*` lifecycle events (each with `type`, `session_id`, `timestamp`)
- Pipeline abstraction defined: `TranslationPipeline` interface (`start_session`, `push_audio`, `receive_events`, `end_session`) with factory `PipelineFactory.create(pipeline_type)` selecting `CascadedPipeline` (wired to mock STT→translation provider) or `UnifiedPipeline` (mock unified provider)
- `SessionService` updated to own a `pipeline` instance per session, route `audio_queue` → `pipeline.push_audio()` → `pipeline.receive_events()` → WebSocket send
- Frontend renders mocked transcripts/translations end-to-end (partial replacement + final stability) while no real model is loaded
- Provider tests, normalizer tests, and pipeline integration tests all pass

## 5. Task Checklist

### Backend — Provider Abstractions

- [ ] P6-MODEL-001 Define `backend/app/providers/base.py`: `BaseProvider` ABC with `async initialize()`, `is_ready() -> bool`, `async close()`, `health()` + error mapping via `ModelError`
- [ ] P6-MODEL-002 Define `backend/app/providers/interfaces.py` or `base/{stt.py,translation.py,tts.py,speech_translation.py}`: `STTProvider(BaseProvider)` with `async start_session(session_id, lang)`, `async push_audio(session_id, pcm_bytes)`, `async poll_events(session_id) -> list[RawEvent]`
- [ ] P6-MODEL-003 Define `TranslationProvider` interface with `async translate(text, source_lang, target_lang) -> str` + batched/streaming variant
- [ ] P6-MODEL-004 Define `TTSProvider` interface with `async synthesize(text, lang) -> bytes` (PCM/WAV/opus marker)
- [ ] P6-MODEL-005 Define `UnifiedSpeechTranslationProvider` interface with `async push_audio` + `async poll_events` returning both transcript and translation segments
- [ ] P6-MODEL-006 Define `ModelError` hierarchy (`ModelNotReady`, `ModelInitError`, `InferenceError`) mapped to WS `error` codes

### Backend — Events & Schemas

- [ ] P6-BE-001 Define normalized application events in `backend/app/schemas/events.py`: `TranscriptEvent`, `TranslationEvent`, `AudioOutputEvent`, `ErrorEvent`, `SessionEvent` union with `segment_id`, `status: Literal["partial","final"]`, `timestamp`, `session_id`
- [ ] P6-BE-002 Implement `backend/app/services/event_normalizer.py` converting provider-specific `RawEvent` dicts into normalized Pydantic events (ensures frontend never depends on model output format)
- [ ] P6-BE-003 Update `backend/app/schemas/websocket.py` server→client union to include `transcript`, `translation`, `audio.output.*`, `error`, `session.*` typed models
- [ ] P6-BE-004 Add segment lifecycle helper `SegmentState` (`segment_id`, `stable_text`, `partial_text`, `status`) used by pipeline/normalizer

### Backend — Pipeline

- [ ] P6-PIPE-001 Define `backend/app/services/pipeline/base.py`: `TranslationPipeline` ABC with `start_session(session: TranslationSession)`, `push_audio(pcm_bytes)`, `poll_events() -> list[NormalizedEvent]`, `end_session()`, `is_ready()`
- [ ] P6-PIPE-002 Implement `backend/app/services/pipeline/cascaded.py` `CascadedPipeline` (mock-backed): STT provider → translation provider on transcript chunks; append normalized events
- [ ] P6-PIPE-003 Implement `backend/app/services/pipeline/unified.py` `UnifiedPipeline` (mock-backed): unified provider → normalized events
- [ ] P6-PIPE-004 Implement `backend/app/services/pipeline/factory.py` `PipelineFactory.create(pipeline_type, settings)` selecting cascaded vs unified, raising `UNSUPPORTED_PIPELINE` for invalid type
- [ ] P6-PIPE-005 Wire `SessionService` to create `pipeline = PipelineFactory.create(settings.pipeline_type)` per session and orchestrate `audio_queue → pipeline.push_audio → poll → send`

### Backend — Mock Providers

- [ ] P6-MODEL-007 Implement `backend/app/providers/mocks/mock_stt.py` deterministic mock: every N chunks emit partial `transcript` events with increasing text, finalize after silence/M chunks
- [ ] P6-MODEL-008 Implement `backend/app/providers/mocks/mock_translation.py` (static map or passthrough with language-code suffix for visibility)
- [ ] P6-MODEL-009 Implement `backend/app/providers/mocks/mock_tts.py` returning tiny synthetic WAV or stub bytes on `synthesize()`
- [ ] P6-MODEL-010 Implement `backend/app/providers/mocks/mock_unified.py` emitting both transcript + translation events per segment
- [ ] P6-CFG-001 Expand `backend/app/core/config.py` for provider selection: `PIPELINE_TYPE=cascaded`, `STT_PROVIDER=mock|real`, `TRANSLATION_PROVIDER`, `TTS_PROVIDER`, `UNIFIED_PROVIDER` + readiness reporting (`model_ready` reflects mock vs real)

### Frontend

- [ ] P6-FE-001 Update `src/services/websocket.js` to handle new server event types `transcript` + `translation` (+ `audio.output.*` stub)
- [ ] P6-FE-002 Update `src/hooks/useSessionState.js` (or `useTranscript.js`) to apply normalized events: `transcript {segment_id,status}` → update active segment vs commit final (no duplication)
- [ ] P6-FE-003 Verify `Transcript` + `Translation` components correctly render mock pipeline stream (replacement semantics from Phase 3)
- [ ] P6-FE-004 Add debug toggle (dev-only) displaying raw WS event log for mock validation

### Testing

- [ ] P6-TEST-001 Unit: `EventNormalizer` mapping raw→normalized for both cascaded and unified mock shapes
- [ ] P6-TEST-002 Unit: `CascadedPipeline` (mock providers) push_audio → poll produces normalized transcript + translation events
- [ ] P6-TEST-003 Unit: `UnifiedPipeline` (mock) similar
- [ ] P6-TEST-004 Integration: `SessionService` + bounded queue + `CascadedPipeline` via WS `TestClient` — binary frames → normalized transcript/translation events on WS
- [ ] P6-TEST-005 Frontend: `useSessionState` update reducer with partial→partial→final sequence for same `segment_id`

---

## 6. Detailed Task Instructions

### P6-MODEL-001 BaseProvider
- Where: `backend/app/providers/base.py`:
  ```python
  class BaseProvider(ABC):
      @abstractmethod async def initialize(self) -> None: ...
      @abstractmethod def is_ready(self) -> bool: ...
      @abstractmethod async def close(self) -> None: ...
      async def health(self) -> dict: ...
  ```
  Document lifecycle expectation: heavier providers load weights in `initialize()` at app startup or lazily on first session — mocks just set `ready=True`.
- Verify: `from app.providers.base import BaseProvider; issubclass(MockSTTProvider, BaseProvider)`.

### P6-MODEL-002 STTProvider
- Where: `app/providers/interfaces.py` (or `base/stt.py`):
  ```python
  class STTProvider(BaseProvider):
      @abstractmethod async def start_session(self, session_id: str, source_language: str) -> None: ...
      @abstractmethod async def push_audio(self, session_id: str, pcm: bytes) -> None: ...
      @abstractmethod async def poll_events(self, session_id: str) -> list[dict]: ...  # raw model events
      @abstractmethod async def end_session(self, session_id: str) -> None: ...
  ```
  Document that raw events are provider-specific (e.g., `{"partial_text": "Hello"}`) and must be normalized before sending to frontend — provider never emits WebSocket-shaped JSON directly.
- ! Keep interfaces deliberately small; add only one helper `segments` dict per provider.

### P6-BE-001 Normalized events
- Where: `backend/app/schemas/events.py`:
  ```python
  class TranscriptEvent(BaseModel):
      type: Literal["transcript"]
      session_id: str
      segment_id: int
      status: Literal["partial","final"]
      text: str
      timestamp: float
  class TranslationEvent(BaseModel):
      type: Literal["translation"]
      session_id: str
      segment_id: int
      status: Literal["partial","final"]
      source_text: str
      translated_text: str
      timestamp: float
  ```
  All normalized events include `type` + `session_id` + `segment_id` where applicable. `timestamp` is `time.monotonic()` or `time.time()` at creation — document choice.
- Verify: `TranslationEvent.model_json_schema()` has expected fields.

### P6-BE-002 Event normalizer
- Where: `app/services/event_normalizer.py: def normalize(raw: dict, session_id: str) -> NormalizedEvent`. Converts mock raw shapes like `{"event":"interim_result","value":"Hello"}` or `{"partial_text":"Hello"}` into `TranscriptEvent`. Must handle both cascaded (separate stt/translation raws) and unified (combined). Log at `DEBUG` the before/after mapping for diagnostics.
- Verify: Unit test passes raw `{"partial_text":"Hello"}` → `TranscriptEvent(type="transcript",text="Hello",status="partial")`.

### P6-PIPE-002 CascadedPipeline (mock)
- Where: `app/services/pipeline/cascaded.py`. Constructor takes `stt_provider: STTProvider`, `translation_provider: TranslationProvider`. `push_audio` forwards to `stt_provider.push_audio`. `poll_events` calls `raws = await stt_provider.poll_events(session_id)` then for each raw transcript, calls `translated = await translation_provider.translate(text, src, tgt)` (mock, synchronous). Normalized events are pairs (`transcript` then `translation`). Keep `TTS` integration as no-op for this phase — TTS slot is filled in Phase 9. Document in class doc why unstable STT partial handling is deferred.
- Verify: `CascadedPipeline(mock_stt, mock_trans).push_audio(b"\\x00"*1920); poll → transcript+translation events`.

### P6-MODEL-007 Mock STT specifics
- Where: `app/providers/mocks/mock_stt.py`:
  ```python
  class MockSTTProvider(STTProvider):
      def __init__(self): self.counters: dict[str,int] = {}
      async def poll_events(self, session_id):
          c = self.counters.get(session_id,0)
          texts = ["Hello","Hello my","Hello my name","Hello my name is","Hello my name is John"]
          # emit partial per every 2 chunks, final on 5th
  ```
  Must be deterministic and fast (no sleep) so tests don't flake. Guarantee `segment_id` increments and `final` is emitted periodically so frontend can show stability.
- Verify: Feeding 10 chunks yields `final` segment with id 1 and text containing "John".

### P6-CFG-001 Environment-configured models
- Where: `app/core/config.py` fields: `pipeline_type: Literal["cascaded","unified"]="cascaded"`, `stt_provider: Literal["mock","whisper","seamless"]="mock"`, `translation_provider`, `tts_provider`, `unified_provider`. Add validator that cascaded requires `stt_provider`+`translation_provider` (or still `mock`), unified requires `unified_provider`. Cap readiness to `all(p.is_ready() for p in loaded)` — in Phase 6 only mocks, so always ready unless explicitly disabled. Report `unsupported_language` if client requests language not in mock allowlist.
- Verify: Setting `PIPELINE_TYPE=unified` switches `PipelineFactory` selection and `GET /health/ready` reflects `pipeline_type`.

### P6-FE-002 Frontend segment replacement
- Where: `src/hooks/useSessionState.js` or dedicated reducer. Maintain `segments: Map<id, {text,status}>` + `activeSegment`. On `transcript partial` for existing `id` → replace text; on `final` → move to finalized list and clear `activeSegment` for that id (next segment id increments). Same logic for `translation`. Document in reducer comment the non-goal: never append duplicate lines for same id.
- Verify: Dispatching `[{id:1, text:"Hello my", status:"partial"}, {id:1, text:"Hello my name", status:"partial"}, {id:1, text:"Hello my name is John.", status:"final"}]` results in one final line.

## 7. Architecture / Data Flow

Phase 6 introduces the **mock-driven pipeline**:

```
Browser PCM chunks (Phase 5)
      ↓  binary WS frame
FastAPI api/websocket.py → SessionService.audio_queue
                              ↓
                       PipelineFactory.create()
                    ┌──────────┴──────────┐
                    ↓                     ↓
            CascadedPipeline        UnifiedPipeline
            STTProvider(m)          UnifiedProvider(m)
                    ↓                     ↓
            TranslationProvider(m)    (emit both)
                    ↓                     ↓
            EventNormalizer (normalize raw → Transcript/TranslationEvent)
                              ↓
                       websocket.send_json(normalized)
                              ↓
                       React useSessionState → Transcript/Translation
```

No real model weights are loaded; the entire path is testable on laptop without GPU.

## 8. Files Expected to Be Created/Modified

Backend:
- `backend/app/providers/base.py` (new)
- `backend/app/providers/interfaces.py` (new) or `providers/base/{stt,translation,tts,speech_translation}.py`
- `backend/app/providers/mocks/mock_stt.py` (new)
- `backend/app/providers/mocks/mock_translation.py` (new)
- `backend/app/providers/mocks/mock_tts.py` (new)
- `backend/app/providers/mocks/mock_unified.py` (new)
- `backend/app/services/pipeline/base.py` (new)
- `backend/app/services/pipeline/cascaded.py` (new)
- `backend/app/services/pipeline/unified.py` (new)
- `backend/app/services/pipeline/factory.py` (new)
- `backend/app/services/event_normalizer.py` (new)
- `backend/app/schemas/events.py` (new)
- `backend/app/schemas/websocket.py` (modified: include transcript/translation types)
- `backend/app/services/session_service.py` (modified: own `pipeline` per session)
- `backend/app/core/config.py` (modified: provider selection, pipeline_type)
- `backend/app/main.py` (modified: initialize mock providers on startup if needed)
- `backend/tests/test_event_normalizer.py` (new)
- `backend/tests/test_pipeline_mock.py` (new)
- `backend/tests/test_mock_providers.py` (new)

Frontend:
- `frontend/src/services/websocket.js` (modified: transcript/translation handlers)
- `frontend/src/hooks/useSessionState.js` (modified: reducer for normalized events)
- `frontend/src/components/Transcript.jsx` (modified: verify against mocks)
- `frontend/src/components/Translation.jsx` (modified)
- `frontend/src/__tests__/eventHandling.test.js` (new)

## 9. Testing Requirements

- Unit: Base provider lifecycle (`initialize`/`is_ready`/`close`), mock STT deterministic behavior, mock translation map, event normalizer (cascaded vs unified shapes), `PipelineFactory` valid/invalid `pipeline_type`.
- Integration: `SessionService` + `CascadedPipeline` (mock) via `TestClient` WS — binary burst → receive normalized transcript+translation events in order; same for `UnifiedPipeline`.
- Frontend unit: `useSessionState` reducer for partial→partial→final replacement semantics (idempotent, no duplicates).
- Manual smoke: Browser audio flowing with mocks shows fake words cycling then finalizing in UI without model.

## 10. Acceptance Criteria

- [ ] Provider interfaces defined (STT, Translation, TTS, Unified) with `initialize/is_ready/close`.
- [ ] Mock STT/Translation/TTS/Unified providers implemented deterministically, no GPU/model dependency.
- [ ] Common normalized event protocol (`transcript`/`translation` with `segment_id`, `status`, `timestamp`) documented and shared between pipelines.
- [ ] `CascadedPipeline` (mock) produces transcript+translation pairs per audio chunk; `UnifiedPipeline` (mock) emits both.
- [ ] `EventNormalizer` converts each provider raw shape → normalized events (tests for both paths).
- [ ] `SessionService` owns pipeline per session; WS binary frames → pipeline → normalized events → JSON sent.
- [ ] Frontend correctly applies partial vs final events (replace active, commit final, no dup lines) against mock stream.
- [ ] `PIPELINE_TYPE` env selects pipeline; invalid value returns `UNSUPPORTED_PIPELINE` error.
- [ ] All new unit/integration tests pass; lint/type still green.

## 11. Verification Procedure

```bash
cd backend
PIPELINE_TYPE=cascaded python -m pytest tests/test_event_normalizer.py tests/test_pipeline_mock.py -v
python -m pytest tests/test_websocket.py -k ws_mock -v

# WS smoke with mocks (observe normalized events)
python - << 'PY'
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app).websocket_connect("/ws/v1/translate") as ws:
    ws.send_json({"type":"start","source_language":"en","target_language":"hi"})
    print(ws.receive_json())  # session.ready
    for i in range(5):
        ws.send_bytes(b"\x00\x01"*960)  # ~960 samples
    # expect a transcript+translation pair soon after
    print(ws.receive_json())
    print(ws.receive_json())
    ws.send_json({"type":"stop"})
    print(ws.receive_json())
PY

cd ../frontend/frontend
npm run dev -- --host
# Browser: Start → speak → mock transcript "Hello…" appears in Source panel and mock translation in Translation panel; both stabilize.
```

## 12. Known Limitations

- Real STT/translation/TTS models are not loaded — performance/resource numbers are meaningless until Phases 7–9.
- TTS slot in cascaded pipeline is stubbed (no audio generation even from mocks beyond tiny test bytes).
- Language coverage is mock allowlist, not model capabilities.
- Unified vs cascaded mocks are deliberately simple; no real simultaneous-translation behavior is simulated.

## 13. Risks / Notes

- **Do not over-abstract**: Single `BaseProvider` + 4 small interfaces is enough. Avoid a deep `providers/stt/{whisper,faster_whisper,...}` hierarchy until a real second provider exists.
- **Keep EventNormalizer authoritative**: Frontend must never branch on raw provider shapes. All mapping lives server-side so switching models requires zero frontend changes.
- **Assume mock is deterministic**: Flaky mocks make WS tests non-deterministic — seed logic and avoid `sleep`/`random`.
- **TTS bytes are stubbed**: Phase 6 mock TTS may return a fixed WAV header; real PCM/WAV detail is finalized in Phase 9 when audio playback strategy is settled.

## 14. Phase Completion Status

- Total tasks: 29
- Completed tasks: 0
- Partially completed tasks: 0
- Remaining tasks: 29
- Blocked tasks: 0
- Overall progress: 0%
- Acceptance criteria status: 0 / 9 satisfied

