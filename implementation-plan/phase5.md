# Phase 5: Browser Audio Pipeline & Real-time Streaming

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

Related documentation: `docs/srs.md` §9 (audio requirements), §4.1 (high-level arch: AudioWorklet→PCM→WS), `docs/trd.md` §7-8 (audio processing & buffering), `docs/Translation.md` §6 (browser audio capture), `docs/prd.md` §23 (audio requirements), `docs/architecture.md` (WebSocket→Audio Processing)

---

## 1. Objective

Implement the end-to-end browser audio pipeline: microphone permission → AudioContext/AudioWorklet → PCM S16LE mono 16 kHz → small chunk framing → binary WebSocket streaming → backend audio validation and bounded queuing. By the end of Phase 5, speaking into the mic produces verifiable binary traffic that reaches `TranslationSession.audio_queue` at <100 ms chunk granularity — still without requiring a real model.

## 2. Prerequisites

- Phase 4 complete: `/ws/v1/translate` live with session lifecycle and per-session bounded queue
- Phase 3 complete: React shell with language selector and WS hook stubs
- Target browsers support `navigator.mediaDevices.getUserMedia`, `AudioContext`, `AudioWorklet`, `WebSocket` (Chrome/Edge/Firefox/Safari current versions)
- Dev servers: FastAPI on `localhost:8000`, Vite on `localhost:5173`

## 3. Expected Starting State

- `src/services/websocket.js` can send `session.start`/`stop` and accept binary `sendAudio()` calls, but no audio is actually captured
- No `getUserMedia` call, no `AudioWorklet`, no audio utils, no frontend mic controls
- Backend `processor_loop` drains queue but does not inspect audio format
- Transcript/translation panels still show placeholder state

## 4. Target State

- User can click Start → browser requests mic permission (with clear rationale), captures mic audio continuously, and streams `Int16` PCM chunks as binary WS frames until Stop or error
- Frontend exposes distinct mic statuses (idle, requesting, active, error, permission-denied) and cleanup on Stop or disconnect
- Audio path is: `getUserMedia → MediaStream → AudioContext(16 kHz or resampled) → AudioWorkletProcessor → Float32→Int16 → mono conversion → ~20–100 ms PCM S16LE chunks → WebSocket binary frames`
- Backend validates frames (binary, size limits, PCM sanity) with normalized `INVALID_AUDIO_DATA` errors and backpressure handling from Phase 4
- All of the above is tested with mocked `AudioWorklet` + integration streaming tests; measured chunk duration and frame sizes are documented for later model alignment

## 5. Task Checklist

### Frontend — Microphone & AudioWorklet

- [ ] P5-AUDIO-001 Create `src/services/audio.js` helpers: `requestMicrophone()`, `createAudioContext(targetSampleRate)`, `attachWorklet(audioContext)` with error handling for permission denied/unavailable
- [ ] P5-AUDIO-002 Create `public/audio-processor.js` or `src/worklets/audioProcessor.worklet.js` (AudioWorkletProcessor) capturing input channel 0, buffering to `Float32Array`, posting messages with `port.postMessage`
- [ ] P5-AUDIO-003 Register AudioWorklet via `audioContext.audioWorklet.addModule(url)` with fallback error handling for unsupported browsers
- [ ] P5-AUDIO-004 Implement mono conversion (mix or channel-0) — document chosen strategy — for stereo mic input
- [ ] P5-AUDIO-005 Implement 16-bit PCM S16LE conversion: `float32 [-1,1] → int16 [-32768,32767]` clamping helper
- [ ] P5-AUDIO-006 Implement client-side sample-rate handling: detect `audioContext.sampleRate`, resample to 16 kHz if hardware rate differs (simple ratio or `OfflineAudioContext`/worklet resampling; document algorithm and trade-off)
- [ ] P5-AUDIO-007 Implement browser-side chunking: configurable `CHUNK_MS` (default 60 ms) and `CHUNK_SAMPLES = 16000 * CHUNK_MS / 1000`; buffer partial input blocks until full chunk, then emit `ArrayBuffer`
- [ ] P5-AUDIO-008 Expose `getAudioConfig()` returning actual `sampleRate`, `channelCount`, `chunkMs`, `chunkBytes` for backend negotiation/debug
- [ ] P5-AUDIO-009 Implement microphone lifecycle: `startCapture(onChunk)`, `stopCapture()` releasing `MediaStreamTrack.stop()`, `AudioContext.close()`, awaiting `processor.port` close

### Frontend — Streaming Integration

- [ ] P5-AUDIO-010 Create `src/hooks/useAudioRecorder.js`: state `micStatus` (idle|requesting|active|error|permission_denied), exposes `startRecording()`, `stopRecording()`, `onChunk` callback; respects `session.status === 'active'`
- [ ] P5-AUDIO-011 Wire `useAudioRecorder` → `useWebSocket.sendAudio(buffer)` until `session.stop`; batch send without extra JSON header (raw PCM bytes per frame)
- [ ] P5-AUDIO-012 Handle mic permission-denied flow: show actionable message ("Microphone access is required… Allow in browser settings") and prevent session from staying 'active' without audio
- [ ] P5-AUDIO-013 Implement mute/silence detection: do not send all-zero chunks in rapid succession if model feeding should be paused (optional optimization; document if skipped)
- [ ] P5-AUDIO-014 Add backpressure cooperation: if `ws.readyState !== OPEN`, pause worklet posting or drop chunk locally and log `dropped_chunk_backpressure`
- [ ] P5-AUDIO-015 Document why each transformation is required (PCM, mono, 16 kHz, chunking) in `src/services/audio.js` header comments

### Backend — Audio Reception & Validation

- [ ] P5-BE-001 Add audio validation inside WS receive path: frame must be binary, `min_bytes <= len <= max_bytes`, even byte length (S16LE), non-empty; else → `error` `INVALID_AUDIO_DATA`
- [ ] P5-BE-002 Add session audio stats: `frames_received`, `bytes_received`, `dropped_frames`, `last_frame_at` for observability
- [ ] P5-BE-003 Make audio queue depth observable (log at `DEBUG` every N frames or on backpressure event)
- [ ] P5-BE-004 Add config docs: `AUDIO_TARGET_SAMPLE_RATE=16000`, `AUDIO_CHANNELS=1`, `AUDIO_CHUNK_MS=60`, `AUDIO_FORMAT=pcm_s16le`, `MAX_AUDIO_FRAME_BYTES`

### Components / UX

- [ ] P5-FE-001 Create/update `src/components/AudioControls.jsx` (mic status indicator, Start/Stop button wiring, permission error rendering)
- [ ] P5-FE-002 Update `src/components/ConnectionStatus.jsx` to include mic status subline (e.g., "Listening…" when mic is active)
- [ ] P5-FE-003 Add loading/permission prompt overlay or inline banner before first `getUserMedia` call

### Integration

- [ ] P5-INT-001 End-to-end: Start → mic permission → audio flowing → backend queue depth increases (verified by log or WS metrics event)
- [ ] P5-INT-002 Stop → `MediaStreamTrack.stop` + `AudioContext.close` + WS `session.stop`; confirm no leaked tracks/contexts
- [ ] P5-INT-003 Disconnect mid-speech → mic stops and session cleans up; revisiting Start cleanly re-requests mic if needed

### Testing

- [ ] P5-TEST-001 Frontend unit: `audio.js` PCM conversion correctness (known Float32 inputs → expected Int16 bytes)
- [ ] P5-TEST-002 Frontend unit: chunking helper (arbitrary input lengths → exact `CHUNK_SAMPLES`-sized outputs + leftover handling)
- [ ] P5-TEST-003 Frontend unit: mono conversion (stereo mock input → channel-0 or mixed output path)
- [ ] P5-TEST-004 Frontend integration (JS mock): `useAudioRecorder` start/stop lifecycle with mocked `AudioWorklet` + `getUserMedia`
- [ ] P5-TEST-005 Backend integration: spam binary frames and verify bounded queue + stats + backpressure signal path

---

## 6. Detailed Task Instructions

### P5-AUDIO-001 services/audio.js
- Where: `src/services/audio.js`. Export `async function requestMicrophone()` wrapping `navigator.mediaDevices.getUserMedia({audio:{channelCount:1, sampleRate:16000, echoCancellation:true, noiseSuppression:true}})`. Handle `NotAllowedError` → throw `MicPermissionDenied`, `NotFoundError` → `MicNotFound`. Export `function createAudioContext(targetRate=16000)` doing `new (window.AudioContext||webkitAudioContext)({sampleRate: targetRate})` with fallback (some browsers ignore `sampleRate`, must handle mismatch in P5-AUDIO-006). Document each echo/noise option and why.
- Verify: In Chrome, `await requestMicrophone()` triggers permission bar; deny → error mapped.

### P5-AUDIO-002 AudioWorklet processor
- Where: `public/audio-processor.js` (served statically) or `src/worklets/audioProcessor.worklet.js` bundled by Vite's `?worker` import. Processor class:
  ```js
  class AudioProcessor extends AudioWorkletProcessor {
    constructor(){ super(); this.buf=[]; }
    process(inputs){ const ch0=inputs[0][0]; if(ch0){ this.port.postMessage(ch0.slice(0)); } return true; }
  }
  registerProcessor('audio-processor', AudioProcessor);
  ```
  This minimal version forwards `Float32Array` slices; chunking + S16 conversion happen on main thread (P5-AUDIO-005/007). Alternative is in-worklet conversion — either is acceptable if documented and measured.
- Verify: With `audioContext.audioWorklet.addModule('/audio-processor.js')` and `new AudioWorkletNode(ctx,'audio-processor')`, `port.onmessage` fires when mic is active.

### P5-AUDIO-005 PCM conversion
- Where: In `services/audio.js` or `worklets` helper `floatTo16BitPCM(float32)`. Loop with `s = Math.max(-1, Math.min(1, float32[i])); out[i] = s < 0 ? s*0x8000 : s*0x7FFF;`. Emit `Int16Array`→`ArrayBuffer`. Document that downstream models expect PCM S16LE mono 16 kHz (per TRD §7, Translation.md §6); if a future model needs different format, only this helper + config changes, not WS or pipeline.
- Verify: `floatTo16BitPCM(new Float32Array([0,1,-1,0.5]))` produces known little-endian bytes.

### P5-AUDIO-006 Sample-rate handling
- Where: After `AudioContext` creation, check `audioContext.sampleRate` vs `AUDIO_TARGET=16000`. If mismatch (e.g., 48000 on many devices), document chosen resampler: (a) simplest: `OfflineAudioContext` resample per chunk; (b) efficient: worklet ratio accumulation; (c) acceptable to defer heavy resampling to backend if both sides documented (but explain extra latency/CPU). Default: do worklet-based ratio if minimal helper exists, else do main-thread linear interpolation and note limitation in `P6` model alignment.
- Verify: Log resolved `actualSampleRate` and `targetSampleRate`; `chunkBytes === chunk_samples * 2` holds.

### P5-AUDIO-007 Chunking
- Where: Main thread accumulator in `services/audio.js` (or inside processor). Default `CHUNK_MS=60` (within 20–100 ms window) → `960` samples at 16 kHz → `1920` bytes S16LE. Buffer incoming `Float32Array` slices until `accumulated.length >= CHUNK_SAMPLES`, slice full chunk, convert, call `onChunk(pcmBuffer)`, retain remainder. Avoid unbounded buffer — reset on `stopCapture`.
- Latency trade-off: smaller chunks → more WS messages/overhead but lower first-result latency; larger → fewer messages but delayed. Document value as benchmark-tunable later (Phase 10).
- Verify: Feeding 3 arbitrary-sized input arrays yields `floor(totalSamples/960)` chunks and correct remainder.

### P5-AUDIO-010 useAudioRecorder.js
- Where: `src/hooks/useAudioRecorder.js`. Holds refs: `streamRef`, `ctxRef`, `workletNodeRef`, `accumulatorRef`. Methods `startRecording(onChunk)` and `stopRecording()` with state `micStatus`. `startRecording` calls `requestMicrophone() → createAudioContext → addModule → connect(MediaStreamSource → workletNode → (no destination))`. Must not connect to `audioContext.destination` (avoid echo). Cleanup: `stream.getTracks().forEach(t=>t.stop())`, `await ctx.close()`, `workletNode.port.close()`. Guard: `startRecording` is no-op if already `active`.
- Dependencies: Called only when `session.status==='ready'` or `'active'`.
- Verify: Opening DevTools → `audioContext.state==='running'` when active; after Stop `audioContext.state==='closed'` and `stream.getTracks().every(t=>t.readyState==='ended')`.

### P5-AUDIO-011 Wiring to WS
- Where: In `App.jsx` (or `useTranslationSession` orchestrator) `useEffect(()=>{ if(useWebSocket.status==='active' && useAudioRecorder.status==='active'){ useAudioRecorder.onChunk = (buf)=> useWebSocket.sendAudio(buf); } }, [...])`. Sends raw `ArrayBuffer` (no JSON header).
- Verify: Browser DevTools → WS frames tab shows continuous binary frames (~1.9kB each) while speaking, stopping when Stop pressed.

### P5-BE-001 Backend validation
- Where: In `app/api/websocket.py` binary branch before queue: assert `isinstance(frame, bytes)` and `len(frame)%2==0` and `MIN <= len <= MAX` (e.g., MIN=320 bytes (10 ms), MAX=19200 (600 ms)). On fail: `await websocket.send_json({type:'error', code:'INVALID_AUDIO_DATA', message:'...' })` and return (drop frame) without closing connection.
- Verify: Sending text frame as binary or 1-byte frame yields `error` event, connection remains open.

### P5-TEST-001..005
- Where: Frontend unit tests in `src/__tests__/audio.*.test.js` using Vitest (or Jest) with mocked `AudioWorklet` replaced by plain callback feeder. Backend integration test in `backend/tests/test_audio_streaming.py` opens WS, sends burst of 100 binary frames, asserts queue `qsize` via stats event or internal counter, and ensures no crash.
- Verify: `npm test` / `python -m pytest` pass with mocked audio context.

## 7. Architecture / Data Flow

Phase 5 completes the **continuous audio path**:

```
Browser
  navigator.mediaDevices.getUserMedia()
        ↓  MediaStream
  AudioContext (16 kHz target)
        ↓
  AudioWorkletProcessor (channel-0 capture)
        ↓  Float32Array slices
  Main-thread accumulator
        ↓  mono + resample + Float32→Int16 conversion
  PCM S16LE chunk (960 samples ≈ 60 ms ≈ 1920 bytes)
        ↓  Binary WebSocket frame (raw ArrayBuffer)
  FastAPI api/websocket.py  (binary validation → audio_queue)
        ↓
  TranslationSession.audio_queue (bounded, backpressure)
        ↓
  processor_loop (still stub in this phase — drain & stats)
        ↓
  logs / stats events → frontend (no transcript yet)
```

Later phases plug `Pipeline` between `audio_queue` and events without changing this path.

## 8. Files Expected to Be Created/Modified

Frontend:
- `frontend/src/services/audio.js` (new: getUserMedia, AudioContext, PCM helpers, chunking)
- `frontend/public/audio-processor.js` (new) or `frontend/src/worklets/audioProcessor.worklet.js` (new)
- `frontend/src/hooks/useAudioRecorder.js` (new)
- `frontend/src/components/AudioControls.jsx` (new/updated)
- `frontend/src/components/ConnectionStatus.jsx` (modified: mic subline)
- `frontend/src/config/environment.js` (modified: audio config constants passthrough)
- `frontend/src/App.jsx` (modified: wire useAudioRecorder ↔ useWebSocket)
- `frontend/src/utils/constants.js` (modified: audio constants)
- `frontend/src/__tests__/audio.test.js` (new)

Backend:
- `backend/app/api/websocket.py` (modified: binary validation branch)
- `backend/app/services/session_service.py` (modified: session audio stats)
- `backend/app/core/config.py` (modified: audio config fields)
- `backend/tests/test_audio_streaming.py` (new)

## 9. Testing Requirements

- Frontend unit: PCM S16LE conversion (golden bytes), chunking correctness, mono conversion path, resampler identity (if `actualRate==targetRate`, pass-through).
- Frontend integration: `useAudioRecorder` lifecycle with mocked `AudioWorklet` + `getUserMedia` grant/deny, Start→Stop cleanup, double-start guard.
- Backend integration: WS with rapid binary burst → no crash, bounded queue backpressure path covered, `INVALID_AUDIO_DATA` for 1-byte/oversize frames.
- Manual: Chrome DevTools WS frames show continuous ~1.9 kB binary messages while speaking.

## 10. Acceptance Criteria

- [ ] Mic permission is requested on Start; denial shows actionable error and does not leave session in hanging `active`.
- [ ] AudioWorklet captures microphone input continuously; `AudioContext` and `MediaStreamTrack` are closed on Stop/disconnect with no leaked tracks.
- [ ] Audio is converted to PCM S16LE mono at configured rate (default 16 kHz) and framed as ~20–100 ms chunks (default 60 ms) — documented byte size.
- [ ] Binary chunks are sent as raw WS frames without JSON wrapping; frontend pauses/drops when WS is not OPEN.
- [ ] Backend validates binary frames (type, even length, size bounds) and returns `INVALID_AUDIO_DATA` for violations without disconnecting.
- [ ] Queue depth and audio stats are observable for later performance work.
- [ ] All new frontend/backend audio tests pass; lint/build still green.

## 11. Verification Procedure

```bash
# Backend
cd backend
uvicorn app.main:app --reload --port 8000 &
python -m pytest tests/test_audio_streaming.py -v
# watch logs tail -f for dropped_chunk_backpressure if flooded

# Frontend
cd ../frontend/frontend
npm run dev -- --host
# Browser:
# 1. Select languages → Start → permission prompt → Allow → ConnectionStatus "Listening…" + mic indicator active.
# 2. Open DevTools → Network/WS → verify binary frames (~1.9kB) streaming continuously.
# 3. Press Stop → frames stop immediately; Application → MediaStreamTracks ended; console no errors.
# 4. Test Deny path: clear site permission → Start → permission_denied banner with help text.
# 5. Offline browser test: DevTools → Console → verify floatTo16BitPCM golden: f32 [0,1,-1] → int16 as expected.

# Audio math sanity
python - << 'PY'
samples_per_chunk = 16000 * 60 // 1000
print(samples_per_chunk, samples_per_chunk*2, "bytes")  # 960 1920
PY
```

## 12. Known Limitations

- No STT/translation/TTS — transcript/translation panels remain empty/placeholder; `processor_loop` still drains without producing events.
- Silence optimization is optional; if omitted, zero-filled chunks are still sent (acceptable for Phase 5).
- Resampling policy is initial; precise model-driven rate (16 kHz vs 16k/48k) is finalized in Phase 7 after model evaluation.
- No persistent audio storage (chunk discarded immediately after processing per AGENTS.md).

## 13. Risks / Notes

- **Browser sample-rate lie**: Many devices report `audioContext.sampleRate=48000` even when requested 16000. Always read back `actualRate` and log it; never assume 16k is honored.
- **Don't need full resampler now**: A simple `OfflineAudioContext` or ratio accumulator is sufficient for Phase 5; heavy polyphase resampler can be introduced only if benchmark shows quality loss.
- **Vite serving of AudioWorklet**: `public/audio-processor.js` is simplest (no bundler transformation). Alternative `import workletUrl from './worklets/audioProcessor.worklet.js?worker'` requires Vite config confirmation.
- **Mixing vs channel-0**: Phase 5 defaults to channel-0; if user has stereo headset and model expects mixed mono, verify quality impact in Phase 7 evaluation — keep decision reversible.
- **Never persist raw audio**: Heap buffer cleared after chunk emitted; `processor_loop` drops queue on end — document in code.

## 14. Phase Completion Status

- Total tasks: 31
- Completed tasks: 0
- Partially completed tasks: 0
- Remaining tasks: 31
- Blocked tasks: 0
- Overall progress: 0%
- Acceptance criteria status: 0 / 7 satisfied

