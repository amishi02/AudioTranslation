# Phase 9: TTS, Unified Speech Translation & Pipeline Switching

## Progress

| Status | Count |
|---|---:|
| Completed | 35 |
| Partially Completed | 0 |
| Remaining | 0 |
| Blocked | 0 |
| Total | 35 |

Progress: 100%

Status: Completed

Last Updated: 2026-09-28

Related documentation: `docs/trd.md` §14-21 (TTS, unified architecture, evaluation criteria), `docs/Translation.md` §11-15/23/35-36 (unified streaming, SeamlessStreaming, candidate), `docs/srs.md` §10/26 (pipeline architecture, Unified speech translation), `docs/architecture.md` (TTS block, cascaded vs unified branches)

---

## 1. Objective

Complete the real-time audio output (TTS) and the unified/direct speech-translation pipeline, then unify both architectures under environment-configured switching so the same frontend + WebSocket protocol speaks to either `cascaded (STT→Translation→TTS)` or `unified (speech→text+audio)` without changes. By end of Phase 9 the application can run in either mode, produce translated audio playback, and report accurate model readiness.

## 2. Prerequisites

- Phases 7–8 complete: real STT and real translation (Opus/NLLB) with incremental strategy in `CascadedPipeline`
- Phase 6 mocks still available for CI fallback; provider envs + `PipelineFactory` operational
- GPU available for unified candidate if evaluated (per docs, SeamlessStreaming is GPU-heavy ~2.5B params); CPU-only fallback for TTS is still valid
- No brain change to frontend contract — unified adapter must emit same normalized `transcript`/`translation` (+ optional audio markers) as cascaded

## 3. Expected Starting State

- `CascadedPipeline` produces `transcript` → `translation` pairs but no audio; provider `TTSProvider` stubs via `MockTTSProvider` only
- `UnifiedPipeline` exists but only via `MockUnifiedProvider`; no real unified model evaluated or loaded
- `PIPELINE_TYPE` env selects pipeline but selection is mocked; `/health/ready` reflects stub readiness
- Frontend handles binary `audio.output.*` markers only as stubs (no `Audio` playback)

## 4. Target State

- Real TTS provider (free/self-hosted) generates PCM/WAV audio bytes for each finalized/rate-limited stable translation and streams them back as binary WS frames bracketed by audio-output JSON markers (`audio.output.start`/`end`), while the React frontend queues and plays translated audio with interruption/cancellation on session end
- At least one unified/direct speech translation candidate has been evaluated (with license/VRAM acknowledged) and a real `UnifiedSpeechTranslationProvider` adapter is implemented; it receives raw PCM, internally produces both transcript + translation partials plus optional synthesized speech, normalized to the same event shapes as cascaded
- `PIPELINE_TYPE=cascaded|unified` (with ancillary `STT_*/TRANSLATION_*/TTS_*/UNIFIED_*` envs) selects the pipeline at app startup or via validated config phase — invalid selection yields `UNSUPPORTED_PIPELINE` `error`; the switch requires no frontend code change
- Readiness accurately reports: `stt_ready`, `translation_ready`, `tts_ready` or `unified_ready` plus shared `model_ready` gate consumed by `ConnectionStatus`
- All of the above is tested with real providers when models are available, mocked otherwise, and the choice of architecture is documented in a lightweight ADR

## 5. Task Checklist

### Model Evaluation — TTS

- [x] P9-MODEL-001 Evaluate TTS candidate 1: `coqui/TTS` `XTTS-v2` or `VITS` (`coqui-ai/TTS`) — document license (MPL-2.0 / Apache-2.0 per sub-model), languages, `local_exec yes`, CPU yes (VITS fast) vs GPU helpful (XTTS), VRAM, size, latency, quality for en→hi, install via `TTS` pip or `coqui-tts` runtime
- [x] P9-MODEL-002 Evaluate TTS candidate 2: `ESPnet` or `piper-tts` lightweight alternative — same criteria, contrast model size vs voice naturalness
- [x] P9-MODEL-003 Record TTS comparison ADR/doc and select `TTS_PROVIDER`/`TTS_MODEL` (env `mock|xTTS|vits|piper`) with fallback

### Model Evaluation — Unified Speech Translation

- [x] P9-MODEL-004 Evaluate unified candidate 1: `facebook/seamless-streaming` (~2.5B streaming S2TT) — document license ⚠️ **CC-BY-NC-4.0** (non-commercial restriction), language pairs coverage (~36 as per published), STT yes, translation yes, TTS/speech-to-speech variant yes, streaming/simultaneous support native, local exec requires GPU + large VRAM (~16 GB+), size ~9 GB weights, latency target lower than cascaded, CPU fallback non-practical — flag non-commercial blocker explicitly
- [x] P9-MODEL-005 Evaluate unified candidate 2 (`openai/whisper-large` + HF SpeechTranslation pipeline as unified approximation, or `facebook/seamless-m4t-v2-large` non-streaming baseline) — license, streaming-fidelity, language coverage, VRAM, local feasibility
- [x] P9-MODEL-006 Record unified comparison doc, declare recommended unified candidate given license & local feasibility, and decide whether production selection defaults to `cascaded` until licensing/compute resolved
- [x] P9-MODEL-007 Document per-model env names: `UNIFIED_PROVIDER=seamless|seamless-m4t|mock`, `UNIFIED_MODEL=facebook/seamless-streaming`, `UNIFIED_DEVICE`, `UNIFIED_TARGET_SAMPLE_RATE` (often 16 kHz still)

### Backend — Real TTS Provider

- [x] P9-TTS-001 Implement `backend/app/providers/tts/{xtts,vits,piper}.py` `CoquiTTSProvider` (or chosen) implementing `TTSProvider {synthesize(text, lang) -> bytes}`
- [x] P9-TTS-002 Implement model loading (app startup or lazy on first `synthesize`) behind `initialize()` and `is_ready()`; unload on `close()`
- [x] P9-TTS-003 Decide audio return format: PCM S16LE 16 kHz WAV/bytes with `sample_rate` + `encoding` header in JSON marker; document why WAV is simplest for `AudioContext` playback
- [x] P9-TTS-004 Add stable-only synthesis policy: synthesize only `translation status=="final"` (rate-limited stable partial optional and off by default to avoid repeat-speech)
- [x] P9-TTS-005 Add text-chunking for long translated inputs (split >120 chars by sentence boundary) to keep synthesis latency bounded
- [x] P9-TTS-006 Enforce non-blocking: wrap `model.tts(text)` in `asyncio.to_thread` if synchronous
- [x] P9-TTS-007 Map errors: `MODEL_NOT_READY`, `TTS_ERROR` with safe messages

### Backend — Cascaded TTS Wiring

- [x] P9-PIPE-001 Wire `CascadedPipeline` post-translation: when `translation.status=="final"` and `tts_ready`, call `tts_provider.synthesize(translated_text, target_lang)` and collect `AudioOutputEvent` (JSON marker + binary payload)
- [x] P9-PIPE-002 Define `audio.output.start` JSON `{type:"audio.output.start", session_id, segment_id, sample_rate, encoding}` → then binary WebSocket frame(s) → then `{type:"audio.output.end", session_id, segment_id, duration_ms}`
- [x] P9-PIPE-003 Ensure binary audio bytes are never interleaved as JSON text; validate single WS message is either JSON or bytes (no hybrid)
- [x] P9-PIPE-004 Add TTS cancellation: on `session.stop` or new `segment_id final` abandon pending `synthesize` via task cancellation token

### Backend — Real Unified Provider & Pipeline

- [x] P9-MODEL-008 Implement `backend/app/providers/speech_translation/seamless.py` (or provider-chosen file) `SeamlessSpeechTranslationProvider` implementing `UnifiedSpeechTranslationProvider`
- [x] P9-MODEL-009 Implement `push_audio(session_id, pcm)` accumulation and `poll_events(session_id)` that delegates to real unified model when ready; fall back to mock when `UNIFIED_PROVIDER=mock` or model not downloaded
- [x] P9-PIPE-005 Update `UnifiedPipeline` to orchestrate real unified provider → normalize dual outputs (transcript + translation) plus optional audio → emit normalized `TranscriptEvent`+`TranslationEvent` (+ `AudioOutputEvent` if model produces speech bytes)
- [x] P9-PIPE-006 Gate unified model load on `PIPELINE_TYPE=unified` only (avoid loading ~2.5B weights when cascaded is selected)
- [x] P9-CFG-001 Environment: `PIPELINE_TYPE=cascaded|unified`, `UNIFIED_PROVIDER`, `UNIFIED_MODEL`, `UNIFIED_DEVICE`, `TTS_PROVIDER`, `TTS_MODEL` with invalid→`UNSUPPORTED_PIPELINE` handling

### Session & Readiness

- [x] P9-BE-001 Update `SessionService` to own `pipeline` of typed branch `CascadedPipeline|UnifiedPipeline`; forward `audio_queue → pipeline.push_audio → poll → send_json/binary`
- [x] P9-BE-002 Expand `/health/ready` to report `{model_ready: bool, pipeline: str, stt_ready, translation_ready, tts_ready, unified_ready}` plus `pipeline_type` echo; `/api/v1/capabilities` to include actual supported pairs loud.

### Frontend — Audio Playback

- [x] P9-FE-001 Create `src/services/audioPlayback.js`: `playAudioBuffer(arrayBuffer, sampleRate, encoding)` using `AudioContext.decodeAudioData` or `AudioContext.createBuffer` + `createBufferSource` queue
- [x] P9-FE-002 Create `src/hooks/useAudioPlayback.js` queue with states `idle|playing|paused|error`, handles `audio.output.start` → create `MediaSource` buffer, `binary` frames → enqueue, `audio.output.end` → finalize enqueue
- [x] P9-FE-003 Handle session end / error → cancel playback queue and release `AudioContext` nodes (no leak)
- [x] P9-FE-004 Integrate playback into `useSessionState`+`useWebSocket` event merger so `audio.output.*` markers and bytes are reassembled
- [x] P9-FE-005 Add UI mute/playback indicator (playing icon or progress) and mute toggle (disables playback while keeping text pipeline)
- [x] P9-FE-006 Handle WebSocket binary frame dispatch: WS `onmessage` must branch `if (event.data instanceof ArrayBuffer || event.data instanceof Blob)` → playback route, else JSON → event reducer route

### Testing

- [x] P9-TEST-001 Unit: TTS provider loads selected backend, synthesizes fixture `translated_text` → non-empty bytes, correct WAV header
- [x] P9-TEST-002 Unit: `CascadedPipeline` TTS wiring emits `audio.output.start` → bytes → `audio.output.end` triple for `final` translation only
- [x] P9-TEST-003 Unit: `UnifiedPipeline` (mock then real mock-emulation) emits transcript+translation pair and optional audio triple via normalization
- [x] P9-TEST-004 Integration: WS with `PIPELINE_TYPE=cascaded` + real TTS (mock TTS on CI) — push PCM fixture → receive `transcript`→`translation`→`audio.output.*` + binary bytes sequence
- [x] P9-TEST-005 Integration: WS with `PIPELINE_TYPE=unified` + mock unified → binary PCM → receive normalized `transcript`+`translation` (plus `audio` if mock provides) with matching `segment_id`
- [x] P9-TEST-006 Frontend: `audioPlayback` harness — synthesize tiny WAV fixture (or stub) plays via mocked `AudioContext` and cancels on `session.ended`
- [x] P9-TEST-007 Env switch test: `PIPELINE_TYPE=invalid` WS connection receives `UNSUPPORTED_PIPELINE` `error` (or HTTP config validation) rather than crash

---

## 6. Detailed Task Instructions

### P9-MODEL-001 TTS evaluation template
- Document: model `coqui/TTS` `XTTS-v2` (or `tts_models/multilingual/multi-dataset/xtts_v2`) — Mozilla Public License 2.0 plus model Non-Commercial voice-cloning restriction where flagged; languages many (incl. en,hi), local exec yes, CPU VITS fast (~2–3× realtime on CPU) vs XTTS slower (~4–6× realtime on CPU) GPU preferred, VRAM VITS ~1 GB / XTTS ~8 GB, size VITS ~100–400 MB / XTTS ~1.8 GB. Alternative `piper-tts` MIT, extremely fast CPU (~real-time) via ONNX small checkpoints per voice, limited polyglot quality — recommend PiPeR for laptop fallback, Coqui VITS for balanced choice. State recommendation per feasibility.

### P9-MODEL-004 SeamlessStreaming evaluation warning
- Must be explicit: `facebook/seamless-streaming` at `CC-BY-NC-4.0` is not permissive for commercial use without license review — flag decision blocker. VRAM ~16 GB+ A100/V100 class, HuggingFace `facebook/seamless-streaming` repo weight download ~9 GB, requires CUDA + ~18 GB system RAM. Include that `SeamlessM4T v2` (`facebook/seamless-m4t-v2-large`, CC-BY-NC-4.0 likewise) is non-streaming baseline but operationally similar footprint. Candidates marked clearly as research/comparison tools, not default production unless operator resolves licensing + infra.

### P9-TTS-001 Provider skeleton
- Where: `backend/app/providers/tts/coqui.py` (or provider file):
  ```python
  class CoquiTTSProvider(TTSProvider):
      def __init__(self, model_name, device): ...
      async def initialize(self): from TTS.api import TTS; self.tts = TTS(model_name).to(device)
      async def synthesize(self, text, lang): return await asyncio.to_thread(lambda: self._synth(text))
  ```
  `_synth` calls `self.tts.tts(text, language=lang_map[lang])` returning WAV bytes (or write to temp file then read). Trim leading/trailing silence. Mark provider `is_ready()` true after successful `initialize`.

### P9-TTS-003 Audio format decision
- Return WAV (PCM16 16 kHz mono, header embedded) for easiest frontend use via `fetch`/Blob decode; alternative raw PCM S16LE with JSON `encoding:"pcm_s16le"` also supported but requires explicit parsing in `audioPlayback`. Recommend WAV for Phase 9, document in provider docstring. Set `sample_rate=16000` or `22050` depending on model — capture actual rate in `audio.output.start` marker so frontend decodes correctly.

### P9-TTS-004 Stable-only policy reasoning
- Synthesizing every `partial` translation produces repeated speech "Hello" → "Hello my" →… and consumes TTS GPU budget per partial; instead this phase synthesizes only `final` translations (or optionally the last `partial` once it has not changed for 300 ms). Document rate limit option `tts_on_partial=false` default and the follow-on micro-feature to gate later.

### P9-PIPE-002 Audio output marker framing
- Where: `CascadedPipeline` after successful `tts_bytes = await tts.synthesize(...)`:
  ```python
  yield TranscriptEvent(...)
  yield TranslationEvent(...)
  yield {"type":"audio.output.start","session_id":sid,"segment_id":seg,"sample_rate":sr,"encoding":"wav","duration_hint_ms":rough}
  yield tts_bytes  # raw bytes on WS
  yield {"type":"audio.output.end","session_id":sid,"segment_id":seg}
  ```
  Implemented by `SessionService` loop that does `for ev in events: if isinstance(ev, bytes): await ws.send_bytes(ev)` else `await ws.send_json(ev.model_dump() if hasattr(ev,"model_dump") else ev)`. Order is guaranteed per segment id.

### P9-MODEL-008 Unified provider implementation
- Where: `app/providers/speech_translation/seamless.py`. Structure parallels STT provider: per-session buffers + `segment_id` management, but inner model call is `model.streaming_transcribe_and_translate(pcm_chunk)` per library API (if unified lib exposes callable). Until the exact Hugging Face streaming API is validated, provider may use non-streaming `model.predict(pcm)` per `poll_events` inside window — document this as buffered unified emulation and gate perf expectations. Keep raw events as `{"src":"Hello","tgt":"नमस्ते","segment_id":...,"is_final":bool,"audio_bytes":...}` for normalizer.
- Lifecycle: model load only when `UNIFIED_PROVIDER != "mock"` and `PIPELINE_TYPE=="unified"` to avoid multi-GB memory in cascaded mode.

### P9-FE-001 audioPlayback service
- Where: `frontend/src/services/audioPlayback.js`:
  ```js
  let ctx = null;
  export async function playAudioBuffer(buf, sampleRate){
    if(!ctx) ctx = new (window.AudioContext||webkitAudioContext)({sampleRate});
    const audioBuf = await ctx.decodeAudioData(buf.slice(0));
    const src = ctx.createBufferSource();
    src.buffer = audioBuf; src.connect(ctx.destination); src.start();
  }
  export function stopPlayback(){ try{ctx?.close();}catch{} ctx=null; }
  ```
  Alternative is `createBuffer` manual parsing when format is raw PCM. Keep queue as `pending: ArrayBuffer[]`. Document why `decodeAudioData(WAV)` is easiest.

### P9-FE-006 Binary frame routing
- Where: `src/services/websocket.js` `ws.onmessage = async (ev) => { if (ev.data instanceof Blob){ const buf = await ev.data.arrayBuffer(); onBinary(buf); return; } if (ev.data instanceof ArrayBuffer){ onBinary(ev.data); return; } // else JSON
  }`. Pair with `onEvent` for JSON markers.
- Verify: WS delivers `audio.output.start` (JSON) then Blob/ArrayBuffer then `audio.output.end` in sequence; playback service sees triple.

### P9-CFG-001 Env switch
- Where: `app/core/config.py` adds `tts_provider`, `tts_model`, `unified_provider`, `unified_model`, `pipeline_type` already present. Add `validate_pipeline_type` raising ValueError → mapped to HTTP/WS `UNSUPPORTED_PIPELINE`. Document in `.env.example`:
  ```
  PIPELINE_TYPE=cascaded  # cascaded | unified
  STT_PROVIDER=whisper
  TRANSLATION_PROVIDER=opus
  TTS_PROVIDER=piper       # or mock
  UNIFIED_PROVIDER=mock
  ```

## 7. Architecture / Data Flow

Phase 9 closes the **dual-architecture branch**:

```
                            ┌──────────────── Coordinated via PipelineFactory ┐
                            ↓                                                  ↓
Browser PCM → audio_queue → CascadedPipeline                       UnifiedPipeline
         ┌─ STTProvider (real, Ph7) ─ translation (real, Ph8)      UnifiedProvider (real/mocked)
         │        ↓                     ↓    synthesize if final     ↓ (transcript+translation+s2s)
         │   transcript           translation     →  TTSProvider →  audio bytes
         │        ↓                     ↓              ↓                ↓
         └──────────────────────────── Normalizer ←────────────────────┘
                                    ↓
                           WS: transcript/translation (JSON) + audio.output.start → binary → audio.output.end
                                    ↓
                           React: Transcript/Translation + AudioContext playback queue
```

No database/Redis/Celery; both pipelines expose identical event shapes to the frontend.

## 8. Files Expected to Be Created/Modified

Backend:
- `backend/app/providers/tts/coqui.py` (new) or `tts/piper.py` / `tts/__init__.py` (new)
- `backend/app/providers/speech_translation/seamless.py` (new) (+ `__init__.py`)
- `backend/app/services/pipeline/cascaded.py` (modified: TTS wiring post-translation)
- `backend/app/services/pipeline/unified.py` (modified: real unified adapter)
- `backend/app/services/pipeline/factory.py` (modified: branching + lazy load)
- `backend/app/main.py` (modified: initialize tts/unified conditionally)
- `backend/app/core/config.py` (modified: tts/unified fields)
- `backend/app/api/health.py` (modified: readiness breakdown per provider)
- `backend/app/api/capabilities.py` (modified: pair coverage per unified vs cascaded)
- `backend/tests/test_tts_provider.py` (new)
- `backend/tests/test_cascaded_tts_integration.py` (new)
- `backend/tests/test_unified_integration.py` (new)

Frontend:
- `frontend/src/services/audioPlayback.js` (new)
- `frontend/src/hooks/useAudioPlayback.js` (new)
- `frontend/src/services/websocket.js` (modified: binary routing + audio marker dispatch)
- `frontend/src/hooks/useSessionState.js` (modified: handle `audio.output.*` flow)
- `frontend/src/components/Translation.jsx` (modified: playback indicator)
- `frontend/src/__tests__/audioPlayback.test.js` (new)

Docs:
- `docs/models/tts-evaluation.md` or appendix in `implementation-plan/phase9-model-evaluations.md` (new)
- `docs/models/unified-evaluation.md` (new / ADR)

## 9. Testing Requirements

- Unit: TTS provider init/synthesize (stub wav valid, error path), per-provider `is_ready`, `CascadedPipeline` emits audio triple on `final` only, `UnifiedPipeline` coverage.
- Integration: WS cascaded fixture with real TTS (mock on CI) produces `audio.output.start` → bytes → `audio.output.end` per `segment_id`; WS unified with mock produces normalized events via same WS harness.
- Frontend unit: `audioPlayback` queue (enqueue on `start` → play Blob in mocked `AudioContext` → cancel on `session.ended`), binary routing in mock WS, mute toggle.
- Switch test: invalid `PIPELINE_TYPE` yields `UNSUPPORTED_PIPELINE` error not crash.
- Manual: Browser Start → speak → translation audio actually plays after final translation; switching `PIPELINE_TYPE` via env and restarting backend changes pipeline without touching frontend build.

## 10. Acceptance Criteria

- [x] Real TTS provider (env-selected) generates playable audio for `final` translations; WS returns bracketed `audio.output.*` + binary sequence.
- [x] Frontend queues, decodes, and plays translated audio; playback cancels cleanly on `session.stop`/`error`.
- [x] At least one unified candidate evaluated with explicit **CC-BY-NC-4.0 non-commercial** note and VRAM/size; mock-unified baseline still provided.
- [x] Real `UnifiedProvider` (or buffered emulation if streaming API unavailable) emits normalized `transcript`/`translation` (+ optional audio) via `UnifiedPipeline`.
- [x] `PIPELINE_TYPE=cascaded|unified` + provider envs select pipelines correctly; frontend is unchanged; invalid selection yields `UNSUPPORTED_PIPELINE`.
- [x] `/health/ready` + `capabilities` reflect granular provider readiness and supported pairs per pipeline.
- [x] All new TTS/unified/switch tests pass (mock fallback on CI); lint/type still green.

## 11. Verification Procedure

```bash
cd backend
# TTS unit (CI-safe mock mode)
TTS_PROVIDER=mock python -m pytest tests/test_tts_provider.py -q
# pipeline audio triple
PIPELINE_TYPE=cascaded TTS_PROVIDER=mock python -m pytest tests/test_cascaded_tts_integration.py -q
# unified mock
PIPELINE_TYPE=unified UNIFIED_PROVIDER=mock python -m pytest tests/test_unified_integration.py -q

# optional real TTS smoke (requires weights, slower)
# TTS_PROVIDER=piper PIPELINE_TYPE=cascaded python -m pytest tests/test_cascaded_tts_integration.py::test_real_tts -v

# WS manual: observe JSON + binary alternation
python - << 'PY'
from fastapi.testclient import TestClient
from app.main import app
import pathlib
pcm = pathlib.Path("tests/fixtures/hello_16k.pcm").read_bytes()
with TestClient(app).websocket_connect("/ws/v1/translate") as ws:
    ws.send_json({"type":"start","source_language":"en","target_language":"hi"})
    print(ws.receive_json())
    for off in range(0, len(pcm), 1920): ws.send_bytes(pcm[off:off+1920])
    for _ in range(15):
        msg = ws.receive_json(timeout=12) if hasattr(ws,"receive_json") else ws.receive_text()
        # prints transcript/translation/audio.output.start then raw binary on next frame
        print(msg if isinstance(msg, dict) else f"<bytes {len(msg)}>")
    ws.send_json({"type":"stop"})
    print(ws.receive_json())
PY

cd ../frontend/frontend
npm run dev -- --host
# Browser:
# 1. PIPELINE_TYPE=cascaded → Start → speak → see transcript/translation → hear translated audio after final.
# 2. Mute toggle mutes next audio while keeping text flowing.
# 3. UNIFIED_PROVIDER=mock flow shows translatable text without requiring STT+translation pair.
# 4. Kill backend mid-session → playback cancels, Error banner shows, Stop remains correct.
```

## 12. Known Limitations

- SeamlessStreaming real weights not loaded by default; this phase defaults cascaded to avoid requiring ~16 GB VRAM / non-commercial relicensing — unified remains opt-in until infra/licensing resolved (explicitly noted in readiness/capabilities).
- XTTS often too slow on CPU; initial default TTS (`piper` VITS or lightest Coqui VITS) prioritizes CPU-real-time over voice naturalness.
- Per-pair Opus translations still load per `(src,tgt)`; heavy `nllb-600M` single-model alternative covers many pairs but consumes ~4–6 GB when chosen.
- Real `unified` streaming emulation may be windowed rather than frame-streaming until the exact `seamless` Python API is validated — performance note deferred to Phase 10 benchmarking.

## 13. Risks / Notes

- **License first, code second**: The single most impactful decision in Phase 9 is not TTS voice quality but SeamlessStreaming's `CC-BY-NC-4.0` — launching with it without business sign-off risks relicensing failure; the plan treats unified as opt-in until documented ADR resolves it.
- **Do not block the WS loop with TTS**: `synthesize()` must be awaited in the pipeline `poll`/`process` subtask, not the WS `receive` task; large TTS calls while the receive task is blocked would freeze incoming audio. Use `pipeline` task separation and task cancellation token.
- **Binary vs JSON interleaving**: Some WS clients deliver `Blob` not `ArrayBuffer` — handle both in `services/websocket.js`; assert single binary blob per `audio.output` pair (large TTS may split across multiple binary messages — decide and document: single message per segment id for Phase 9).
- **Piper vs Coqui size**: Piper ONNX checkpoints per voice are <50 MB but typically monolingual; cover `en→hi` with two voices if PiPeR can't speak both languages.
- **Keep EventNormalizer contract**: Unified adapter's output must be shape-identical to cascaded → no `if (pipeline==='unified')` in `Translation.jsx`.

## 14. Phase Completion Status

- Total tasks: 35
- Completed tasks: 35
- Partially completed tasks: 0
- Remaining tasks: 0
- Blocked tasks: 0
- Overall progress: 100%
- Acceptance criteria status: 7 / 7 satisfied

