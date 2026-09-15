# Phase 7: Streaming STT & Transcript Stabilization

## Progress

| Status | Count |
|---|---:|
| Completed | 0 |
| Partially Completed | 0 |
| Remaining | 31 |
| Blocked | 0 |
| Total | 31 |

Progress: 0%

Status: Not Started

Last Updated: 2026-09-14

Related documentation: `docs/trd.md` §11-13 (STT, incremental translation strategy), `docs/srs.md` §5 (FR-007..009), `docs/Translation.md` §8-10, `docs/prd.md` §11-13 (partial/final, display behavior), `docs/websocket-protocol.md` (Transcript event)

---

## 1. Objective

Replace the mock STT with a real, free/self-hosted streaming-capable speech-to-text model, implement transcript stabilization (partial → updated partial → final), and stabilize frontend rendering so the UI never shows duplicate permanent lines. This phase validates that real microphone audio can produce low-latency, incremental transcription while the speaker is still speaking.

## 2. Prerequisites

- Phase 6 complete: provider interfaces, mock pipeline, event normalization, pipeline-per-session wiring
- At least one free/self-hosted STT model evaluated (candidates below); CPU inference verified locally (GPU optional)
- Phase 5 audio pipeline (PCM S16LE mono 16 kHz, ~60 ms chunks) operational and measured
- Model weights can be downloaded or cached locally (Hugging Face / local runtime)

## 3. Expected Starting State

- `MockSTTProvider` drives the pipeline; `TranscriptEvent` + `TranslationEvent` shapes are fixed; frontend replacement semantics proven against mocks
- `CascadedPipeline` exists but uses the stub mapping `stt_raw → translation_provider.translate(mapped_text)`
- No real STT loaded; `/health/ready` reports `model_ready=True` for mocks only
- Backend `processor_loop` orchestrates `audio_queue → pipeline.push_audio → poll` on mocks; no metered latency

## 4. Target State

- A real STT provider (environment-selectable) streams partial and final transcripts from accumulating PCM while the speaker is still talking; language handling respects `source_language`
- Pipeline is still `CascadedPipeline` but now wired to real `STTProvider` implementation (+ `MockTranslationProvider` remains for this phase — translation swap deferred to Phase 8)
- Segments have stable lifecycle: `segment_id` increments monotonically per session, partial events share `segment_id` until `final`, then next utterance gets new id
- Frontend stabilizes: each `segment_id` renders one active line that is replaced on every `partial` and committed on `final`; no duplicate final lines appear under normal conditions
- `/health/ready` accurately reflects real STT readiness (`model_ready` false while weights loading, true after load)
- Model evaluation (license, language coverage, streaming support, local vs cloud, latency) is documented before selection; fallback mock remains available

## 5. Task Checklist

### Model Evaluation & Selection

- [ ] P7-MODEL-001 Evaluate free/self-hosted streaming STT candidate 1: `faster-whisper` (Systran) + `whisper-small/medium` or `distil-whisper` — document license (MIT/Apache-2.0 for code; model is MIT/Apache per variant), language coverage, size/VRAM, CPU vs GPU latency, streaming support (native chunk-based), partial-update approach
- [ ] P7-MODEL-002 Evaluate STT candidate 2: `openai/whisper.cpp` or `vosk` as lightweight alternative — same criteria
- [ ] P7-MODEL-003 Record model comparison ADR/doc section with latency, quality, resource, and licensing trade-offs
- [ ] P7-MODEL-004 Select one production STT model/provider for Phase 7 (allow `STT_PROVIDER=whisper|cpp|mock` env switch) and document chosen `STT_MODEL` name

### Backend — Real STT Provider

- [ ] P7-BE-001 Implement `backend/app/providers/stt/whisper.py` (or provider-named file) `WhisperSTTProvider` (or selected) implementing `STTProvider` interface
- [ ] P7-BE-002 Implement model loading during app startup or lazily on first `start_session` — document choice and lifespan; release resources on shutdown
- [ ] P7-BE-003 Implement `start_session(session_id, source_language)`: per-session `segments` dict, `segment_id` counter, audio buffer per session (accumulated PCM until model produces chunk boundary)
- [ ] P7-BE-004 Implement `push_audio(session_id, pcm_bytes)`: accumulate PCM in session buffer, dispatch to model inference path (streaming chunk or buffered window)
- [ ] P7-BE-005 Implement `poll_events(session_id)`: return `[TranscriptEvent]` raws for normalizer — emit `partial` on incremental hypothesis, `final` on VAD/silence or fixed segment boundary
- [ ] P7-BE-006 Handle `end_session(session_id)`: flush buffered audio → produce last `final` event if non-empty buffer, then release per-session state (not global model weights)
- [ ] P7-BE-007 Map source language codes (`en`, `hi`, etc.) correctly to model language parameter; emit `UNSUPPORTED_LANGUAGE` if `source_language` not feasible for model variant
- [ ] P7-BE-008 Add error mapping: `MODEL_NOT_READY` when inference called before init, `MODEL_ERROR` on inference failure (log inference error with `session_id`, not audio bytes)
- [ ] P7-BE-009 Persist chosen audio format alignment: confirm provider consumes PCM S16LE mono 16 kHz chunks directly; if resampling required, document path

### Pipeline & Normalization

- [ ] P7-PIPE-001 Update `CascadedPipeline` to forward `audio → real STT → poll → normalize` while translation remains mock for this phase
- [ ] P7-PIPE-002 Extend `EventNormalizer` to map real STT provider raw events (e.g., `{"text":"Hello my","is_final":false}`) into normalized `TranscriptEvent` with correct `segment_id`+`status`
- [ ] P7-PIPE-003 Define segment boundary policy: silence threshold, chunk-window count, or model-provided `is_final` — document policy + parameter names
- [ ] P7-PIPE-004 Add per-segment state `SegmentState {id, partial_text, stable_text, status}` managed inside STTProvider or pipeline so `poll`/`normalize` emits consistent `segment_id` progression

### Frontend — Transcript Stabilization

- [ ] P7-FE-001 Update `src/hooks/useTranscript.js` or `useSessionState.js` reducer to enforce: `partial` for existing `id` → replace, `final` for existing `id` → commit & start new active slot
- [ ] P7-FE-002 Ensure `Transcript.jsx` renders finalized list separate from active partial (visual class `partial` vs `final`, e.g., italic/lighter vs solid)
- [ ] P7-FE-003 Ensure translation panel does not regress (it still uses mock translation in this phase; its STT-driven trigger remains wired)

### Configuration

- [ ] P7-CFG-001 Environment: `STT_PROVIDER=whisper`, `STT_MODEL=openai/whisper-small` (or `distil-whisper-small`), `STT_DEVICE=cpu|cuda`, `STT_COMPUTE_TYPE=float16|int8` — with invalid-value validation and `MODEL_NOT_READY` readiness
- [ ] P7-CFG-002 Readiness: `GET /health/ready` returns `{stt_ready, stt_model, pipeline}` based on real provider `is_ready()`

### Testing

- [ ] P7-TEST-001 Unit: `WhisperSTTProvider` loads or fakes load in test mode; validates session lifecycle (`start/push/poll/end`)
- [ ] P7-TEST-002 Unit: `EventNormalizer` mapping for real STT raws (partial vs final) preserves `segment_id`
- [ ] P7-TEST-003 Integration: WS with real STT provider — send 10 binary chunks (pre-recorded fixture WAV/PCM bytes) → expect ordered partials sharing `segment_id` then `final` for same `segment_id`
- [ ] P7-TEST-004 Frontend unit: `useTranscript` reducer with real-shaped events — verify no duplicate final line for same `segment_id`
- [ ] P7-TEST-005 End-to-end smoke: live mic for ~5 s produces incremental transcript in UI (manual or recorded fixture); `time_to_first_transcript` observed and logged
- [ ] P7-TEST-006 Model smoke: validate language mapping and error path for unsupported language code

---

## 6. Detailed Task Instructions

### P7-MODEL-001 faster-whisper evaluation (example candidate)
- Document per template (also required for Phase 8 unified): model name, provider (Systran), license (MIT for runtime; OpenAI Whisper weights are MIT-licensed), supported languages (~99 as per Whisper small), STT=yes/translation=no(speech→en only in variants)/TTS=no, streaming support via `faster-whisper` chunked decoding (no true frame-streaming but windowed), partial support via buffered incremental decoding, local execution yes (Python, CTranslate2), CPU yes / GPU yes (+CUDA), VRAM ~1–2 GB for `whisper-small`, size ~500 MB–1.5 GB depending on variant, latency ~200–600 ms per 1 s window on CPU, quality good for English/Hindi with small variant, install via `pip install faster-whisper` plus weight download. Mark explicitly if true per-frame streaming is unavailable and document workaround buffering strategy.
- If a different STT candidate is chosen, preserve same documentation fields.

### P7-BE-001 WhisperSTTProvider skeleton
- Where: `backend/app/providers/stt/whisper.py` or repo-structured path. Class stores: `model: WhisperModel|None`, `sessions: dict[session_id, SessionSTTState]` where `SessionSTTState {audio_buffer: bytearray, segment_id: int, last_text: str}`. Initialize model in `async def initialize()` (global, not per-request). Inherit `is_ready() -> bool`. Map `MODEL_NOT_READY` if called before init.
- Thin provider: no WS logic here — only audio→text.

### P7-BE-005 poll_events with partial/final cadence
- Where: `poll_events(session_id)` accumulates decoded window and decides: emit `partial` frequently (e.g., every 2nd `push_audio` or model-produced incremental result) and emit `final` when encoder-produced silence/VAD boundary or segment length limit is reached. Emit provider raw dict like `{"session_id":sid,"text":t,"is_final":is_final,"segment_id": seg_id}` for normalizer. Avoid hammering pipeline: limit to at most one partial per ~200 ms if needed (document throttle seconds).
- Why: STT models like Whisper don't natively support partial hypotheses; the provider must emulate them via windowed decoding with history — document whether this phase uses naive "last window" or more sophisticated approach (e.g., comparing successive decodes and suppressing duplicates).

### P7-BE-007 Language mapping
- Where: `WhisperSTTProvider.start_session` receives `source_language` from WS `session.start`. Map to Whisper language code (`zh` → `zh`, `hi` → `hi`, etc.). If model covers only English→English or multilingual variant, document fallback. On unsupported, provider raises `ModelError(code="UNSUPPORTED_LANGUAGE")` → `SessionService` → WS `error` `UNSUPPORTED_LANGUAGE` with user-facing message "Language not supported".

### P7-PIPE-003 Segment boundary policy
- Where: Document policy inside `CascadedPipeline` or `WhisperSTTProvider` header: default policy is `windowed_final_every_N_seconds=2.5` plus `silence_threshold_ms=700` if VAD unavailable, or `model_final_signal` if present. Keep it simple: Phase 7 requires at least deterministic `final` generation so frontend can show stability; refine in Phase 10 if needed.
- Verify: Feeding continuous PCM for ~4 s produces `partial...partial...final` with consistent `segment_id` until new id after final.

### P7-FE-001 Frontend reducer stabilization
- Where: Extend reducer handling `transcript` events:
  ```js
  onTranscript({segment_id, status, text}) {
    if(status==='partial'){
      state.segments.set(segment_id, {text, status});
      state.activeSegment = {segment_id, text};
    } else { // final
      state.segments.set(segment_id, {text, status:'final'});
      state.activeSegment = null;
    }
  }
  ```
  Guard against out-of-order delivery by ignoring `status==='final'` if `segment_id` not currently in map (log `unknown_final_id`).

### P7-TEST-003 Integration with real STT
- Where: `backend/tests/test_stt_integration.py`. Use pre-recorded fixture PCM bytes (e.g., 5 s English utterance "Hello my name is John" encoded as PCM S16LE mono 16 kHz from a `fixtures/hello_pcm.bin` or synthesized tiny WAV converted to PCM). Push those bytes in chunk-sized frames through `WhisperSTTProvider` or via WS `TestClient` with real provider loaded. Assert at least one `partial` event received quickly and that consecutive `partial` for same `segment_id` share text prefix, and final status appears within bounded time. Mark test as `pytest.mark.slow` and allow `mock` fallback when `STT_PROVIDER=real` unavailable on CI.
- Verify: Running `STT_PROVIDER=mock python -m pytest tests/test_stt_integration.py -k unit` still passes (fallback), while `STT_PROVIDER=whisper` exercises real weights when present.

## 7. Architecture / Data Flow

Phase 7 promotes `CascadedPipeline` from mock to real STT (translation still mocked):

```
Browser mic PCM chunks (Phase 5)
        ↓  binary WS
SessionService.audio_queue → CascadedPipeline.push_audio()
                              ↓
                        WhisperSTTProvider (real model)
                              ↓  poll_events →
                        raw transcript {text, is_final, segment_id}
                              ↓
                        EventNormalizer → TranscriptEvent(type:"transcript", id, status, text)
                              ↓
                        SessionService.send_json(TranscriptEvent)
                              ↓
     React hooks → Transcript.jsx (stable segments + active partial)
```

Translation path remains mock this phase so frontend translation panel shows stub rendering but correct STT-driven trigger.

## 8. Files Expected to Be Created/Modified

Backend:
- `backend/app/providers/stt/whisper.py` (new: real provider)
- `backend/app/providers/stt/__init__.py` (updated: export provider alias)
- `backend/app/core/config.py` (modified: `stt_provider`, `stt_model`, `stt_device`, `stt_compute_type`)
- `backend/app/services/pipeline/cascaded.py` (modified: wire real STT provider, translation still mock)
- `backend/app/services/event_normalizer.py` (modified: real STT raw→normalized mapping)
- `backend/app/services/session_service.py` (modified: per-session pipeline with real STT instance)
- `backend/app/schemas/events.py` (modified if real timestamps/status mapping needs new fields)
- `backend/tests/test_stt_integration.py` (new)
- `backend/tests/fixtures/hello_pcm.bin` or `hello_16k.wav` (new fixture)
- `backend/tests/test_event_normalizer_stt.py` (new/expanded)

Frontend:
- `frontend/src/hooks/useSessionState.js` or `useTranscript.js` (modified: reducer hardening)
- `frontend/src/components/Transcript.jsx` (modified: finalized vs partial styling polish)
- `frontend/src/__tests__/transcriptReducer.test.js` (new)

## 9. Testing Requirements

- Unit: provider init/is_ready/sessions, normalizer raw→normalized with real STT shape, reducer identity replacement, language map.
- Integration: WS with real STT — CHUNK-sized binary burst → ordered `partial`/`final` chain sharing `segment_id`, then new id after final.
- Manual/E2E smoke: live mic ~5 s incremental transcript in UI; `time_to_first_transcript` visible in console/log.
- Slow-model test annotated with `slow` marker, skippable on CI when `STT_PROVIDER=mock`.

## 10. Acceptance Criteria

- [ ] Free/self-hosted STT model selected and documented with license, languages, size/VRAM, CPU/GPU, streaming/partial notes — mock fallback preserved via `STT_PROVIDER=mock`.
- [ ] `WhisperSTTProvider` (or chosen) implements `STTProvider` with per-session buffers and `segment_id` lifecycle; `is_ready()` correctly reflected in `/health/ready`.
- [ ] Real continuous PCM no longer crashes; accumulating frames produce `partial` quickly (~< 1 s on laptop CPU for small variant) then `final` per policy.
- [ ] Successive `partial` events for same `segment_id` replace (not duplicate) in frontend; `final` is stable and increments `segment_id` for next utterance.
- [ ] `EventNormalizer` preserves `segment_id`/`status` correctly for real STT; mismapped shape would fail its tests.
- [ ] Unsupported `source_language` yields `UNSUPPORTED_LANGUAGE` `error` event.
- [ ] `npm run`/`pytest` tests covering provider→pipeline→WS path pass; `ruff`/`mypy` still green.

## 11. Verification Procedure

```bash
# Backend real STT (GPU optional — CPU works at ~real-time for small)
cd backend
STT_PROVIDER=whisper STT_MODEL=small python -m pytest tests/test_stt_integration.py -v
STT_PROVIDER=mock python -m pytest tests/test_event_normalizer_stt.py -q
ruff check .; ruff format --check .

# WS smoke with real STT (pipe fixture)
python - << 'PY'
from fastapi.testclient import TestClient
from app.main import app
import pathlib
pcm = pathlib.Path("tests/fixtures/hello_16k.pcm").read_bytes()
with TestClient(app).websocket_connect("/ws/v1/translate") as ws:
    ws.send_json({"type":"start","source_language":"en","target_language":"hi"})
    print(ws.receive_json())  # session.ready
    for off in range(0, len(pcm), 1920):  # ~60 ms frames
        ws.send_bytes(pcm[off:off+1920])
    # collect a few transcript events
    for _ in range(5):
        print(ws.receive_json())
    ws.send_json({"type":"stop"})
    print(ws.receive_json())
PY

# Frontend
cd ../frontend/frontend
npm run dev -- --host
# Browser: Start → speak continuously for ~5s → Source Transcript shows
# "Hello" → "Hello my" → "Hello my name is John." updating in-place,
# then committing as final; no duplicate lines.
```

## 12. Known Limitations

- Translation is still mock; target language doesn't affect transcript quality but translation quality is placeholder until Phase 8.
- Whisper's chunked incremental decoding can cause flicker; this phase tolerates mild flicker as long as final segments are stable (refine in hardening/benchmark phases).
- Silence/VAD-based segment finalization may not cleanly split long utterances; long speech may produce one long segment before `final`.
- No unified model yet; latency reported here is STT-only, not end-to-end (includes translation/TTS later).

## 13. Risks / Notes

- **Whisper is not truly streaming**: True frame-streaming ASR is rare for free local models. Phase 7's windowed approach is acceptable; document that transcript latency is ~STT window + decode time, not true 20 ms frames — benchmark and note improvement path for Phase 10.
- **Do not hard-code model name**: Always read `settings.stt_model`; hard-coded weights defeat `STT_PROVIDER=mock` CI path and force weight downloads on every test.
- **Keep per-session buffer isolated**: Global `audio_buffer` would cross-contaminate concurrent sessions — guard with `sessions: dict[session_id, buffer]` and `Lock`.
- **Language codes**: Whisper uses ISO-639-1; SRS/PRD expose language selector pairs — map `source_language` verbatim and normalize case.
- **Assume CPU baseline**: Many dev laptops lack CUDA; initial benchmark must include CPU small variant so local dev is usable even if slower.

## 14. Phase Completion Status

- Total tasks: 31
- Completed tasks: 0
- Partially completed tasks: 0
- Remaining tasks: 31
- Blocked tasks: 0
- Overall progress: 0%
- Acceptance criteria status: 0 / 7 satisfied

