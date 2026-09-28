# Architecture

## Phase 10 State (Production-Ready Phase-1)

System is a real-time audio translation app with dual pipelines, hardened per `implementation-plan/phase10.md`.

### High-Level Flow

```
Browser (React/Vite)
  Microphone (getUserMedia -> AudioWorklet @16k S16LE mono 60ms chunks)
    | binary PCM
    v
WebSocket Client (services/websocket.js, hooks/useWebSocket.js)
    |
    | WS /ws/v1/translate (wss:// in prod)
    v
FastAPI (app/main.py -> routers: health, capabilities, websocket, metrics)
    |
    +-- WebSocket Gateway (api/websocket.py) — thin, validation + backpressure
    |     |  caps: max_json_bytes/max_audio_frame_bytes, queue depth (ws_max_queue_depth),
    |     |  rate-limit (frames/bytes per second -> RATE_LIMITED), timeout watcher (idle 15s/max 10m)
    |     v
    Translation Session Service (services/session_service.py)
    |     |  TranslationSession (models/session.py): session_id, queue, framesReceived, pipeline
    |     v
    Pipeline Interface (services/pipeline/base.py)
    |     +-- Cascaded (STT -> Translation -> TTS)  [PIPELINE_TYPE=cascaded]
    |     |     STT: STTProvider (faster-whisper WhisperSTTProvider + mock) — env STT_MODEL/device/compute, VAD
    |     |     Translation: TranslationProvider (Opus-MT Helsinki + NLLB + mock) — per-pair lazy load + pivot via en
    |     |     TTS: TTSProvider (Piper ONNX + mock) — final-only synthesis, WAV framing
    |     +-- Unified (speech translation) [PIPELINE_TYPE=unified] — Seamless adapter + mock
    |     v
    Event Normalizer (services/event_normalizer.py) -> {transcript, translation, audio.output.*}
    |
    +-- Metrics (services/metrics.py) -> GET /metrics, perf T1..T5
    v
WebSocket -> Browser
    |
    +-- React: Transcript/Translation panels (segment_id replacement semantics), audioPlayback queue, StatusBanner (retryable vs fatal), ConnectionStatus
```

### Backend Layers (AGENTS.md)

```
api/            FastAPI routes/WS handlers (thin, no business logic)
services/       Business logic (session, pipeline factory, event_normalizer, metrics)
providers/      External STT/translation/TTS/unified behind base interface
  base.py       ModelError taxonomy (code)
  interfaces.py STTProvider/TranslationProvider/TTSProvider/UnifiedProvider
  stt/whisper.py, translation/opus.py|nllb.py, tts/piper.py, speech_translation/seamless.py, mocks/*
models/         Domain models (TranslationSession)
schemas/        Pydantic schemas (websocket, events, errors taxonomy, health, capabilities)
core/           Config (pydantic-settings, every dynamic value env-configurable) + logging
utils/          Small helpers
```

Model selection is env-driven only: `PIPELINE_TYPE, STT_PROVIDER, TRANSLATION_PROVIDER, TTS_PROVIDER, UNIFIED_PROVIDER, *_MODEL, *_DEVICE` in `backend/.env.example` -> `core/config.py` -> `ProviderFactory` -> interface. Swapping `STT_MODEL=base`->`small` or `TRANSLATION_PROVIDER=opus`->`nllb` requires only `.env` change.

### Frontend Layers

```
services/  websocket.js (binaryType arraybuffer), audio.js (AudioWorklet PCM), audioPlayback.js (AudioContext queue)
hooks/     useWebSocket (session lifecycle + perf T5), useAudioRecorder (capture), useSessionState (segments), useAudioPlayback
components/ AppShell, Transcript, Translation, LanguageSelector, ConnectionStatus, StatusBanner (retryable flag)
utils/     constants.js (LANGUAGES, CONNECTION_STATES, ERROR_CODES 12), errorMessages.js (code->message + retryable)
config/    environment.js (import.meta.env VITE_* -> WS/API URLs, all env-configurable)
```

### Key Invariants

- No database, no Redis/Celery in real-time path (Phase 10 verifies via grep test).
- Shared model weights across sessions; per-session buffers (audio queue, segment state) transient only.
- Cleanup on every path: Stop/timeout/disconnect/MODEL_ERROR/INTERNAL_ERROR -> queue drained, pipeline.end_session, provider buffer cleared, log `session_ended`.
- No raw audio logged; error messages safe (no stacks).
- All tunables env-configurable: model names, devices, chunk ms, queue sizes, caps, timeouts, rate limits, STT window/VAD, perf flags (see `backend/.env.example` + `app/core/config.py` + `frontend/frontend/.env.example`).

### Excluded (Phase-2+)

Auth/registration/JWT, database, billing, history, rooms — remain out-of-scope, guarded by `docs/adr/ADR-001-pipeline-selection.md`.
