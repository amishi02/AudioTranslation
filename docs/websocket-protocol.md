# WebSocket Protocol

## Endpoint

```
WS  /ws/v1/translate   (config WS_V1_PATH)
WSS in production when APP_ENV=production
```

Query: none. Language negotiation via control JSON.

## Client -> Server

### Start Session

```json
{
  "type": "start",
  "source_language": "en",
  "target_language": "hi"
}
```

- `source_language` / `target_language`: ISO 639-1 lowercased, must differ and be in `SUPPORTED_LANGUAGES` (default en,hi,es,fr,de). Env `PIPELINE_TYPE` selects provider.
- Server validates via `SessionStart` schema. On failure emits `error` with `code=INVALID_SESSION_CONFIG` or `UNSUPPORTED_LANGUAGE`.

### Audio

Binary WebSocket frames: raw `PCM S16LE mono 16kHz` (`AUDIO_TARGET_SAMPLE_RATE=16000`, `AUDIO_CHANNELS=1`). Frontend chunks `AUDIO_CHUNK_MS=60` (~1920 bytes). Server queue `audio_queue` bounded (`AUDIO_QUEUE_MAXSIZE=128`, incoming cap `WS_MAX_QUEUE_DEPTH=64`). Empty/odd-length/oversize (`>MAX_AUDIO_FRAME_BYTES=65536`) rejected as `INVALID_AUDIO_DATA`. Flood beyond `RATE_LIMIT_FRAMES_PER_SECOND=50` / `RATE_LIMIT_BYTES_PER_SECOND=320000` yields `RATE_LIMITED` without disconnect (circular drop).

### End Session

```json
{ "type": "stop" }
```

### Ping

```json
{ "type": "ping" }
```

Server replies `{"type":"pong"}`. Used for heartbeat; idle sessions auto-close after `SESSION_IDLE_TIMEOUT_MS=15000`, hard cap `SESSION_MAX_DURATION_MS=600000` -> `SESSION_TIMEOUT` + `session.ended`.

## Server -> Client

All JSON events share `session_id` + `timestamp` (epoch float). Perf instrumentation adds `perf:{total_ms,queue_depth,stt_ms,translation_ms}` when `PERF_ENABLED=true`.

### session.ready

```json
{ "type":"session.ready","session_id":"abc123","source_language":"en","target_language":"hi" }
```

### transcript

```json
{ "type":"transcript","session_id":"abc","segment_id":1,"status":"partial|final","text":"Hello how","timestamp":1710000000.1, "perf":{"stt_ms":120} }
```

- `segment_id` monotonically increasing per session. Frontend replaces partial of same `segment_id` until `final` commits.

### translation

```json
{ "type":"translation","session_id":"abc","segment_id":1,"status":"partial|final","source_text":"Hello","translated_text":"नमस्ते","timestamp":1710000000.2 }
```

### Audio Output (TTS)

TTS only on `final` segments (stable-only `P9-TTS-004`). Framing interleaves JSON markers + binary:

```json
{ "type":"audio.output.start","session_id":"abc","segment_id":1,"sample_rate":22050,"encoding":"wav" }
```

followed by one binary `ArrayBuffer` containing WAV bytes, then:

```json
{ "type":"audio.output.end","session_id":"abc","segment_id":1,"duration_ms":840 }
```

If TTS unavailable or `audio.output.start` has no following bytes, frontend clears `pendingStart` after 5s (no infinite wait).

### session.ended

```json
{ "type":"session.ended","session_id":"abc","timestamp":1710000000.3 }
```

Also emitted on timeout (`reason=timeout`).

### pong

```json
{ "type":"pong" }
```

### error

```json
{
  "type":"error",
  "code":"RATE_LIMITED",
  "message":"Too many requests. Please slow down.",
  "retryable": true,
  "session_id":"abc",
  "timestamp": 1710000000.1
}
```

Full taxonomy (12 codes): `INVALID_MESSAGE`, `INVALID_SESSION_CONFIG`, `UNSUPPORTED_LANGUAGE`, `UNSUPPORTED_PIPELINE`, `UNSUPPORTED_AUDIO_FORMAT`, `INVALID_AUDIO_DATA`, `MODEL_NOT_READY`, `MODEL_ERROR`, `SESSION_ERROR`, `SESSION_TIMEOUT`, `RATE_LIMITED`, `INTERNAL_ERROR`. Retryable (`retryable:true`): `MODEL_NOT_READY`, `SESSION_TIMEOUT`, `RATE_LIMITED`. All errors are safe (no stack/model leakage). Unknown message types, empty JSON, oversize JSON (`>MAX_JSON_BYTES`), non-object JSON -> `INVALID_MESSAGE`. Odd/zero-length PCM -> `INVALID_AUDIO_DATA`.

### Metrics (HTTP)

```
GET /metrics  -> {sessions_started, sessions_ended, frames_received, dropped_frames, queue_depth_max, rate_limited_events, timeouts, avg_stt_latency_ms, avg_translation_latency_ms, avg_total_latency_ms, p50_total_ms, p95_total_ms}
```

## Binary vs JSON Framing

Client sends JSON control on `text` frames, PCM on `bytes` frames. Server sends JSON control on `text`, WAV on `bytes`. Frontend `services/websocket.js` distinguishes via `instanceof ArrayBuffer|Blob`.

## Security

- No audio bytes logged server-side; logs only `{bytes_len,queue_depth,session_id}`.
- CORS enforced on WS upgrade when `APP_ENV=production` (unknown `Origin` -> close `1008`).
- Caps documented in `backend/.env.example` and `app/core/config.py` (all env-configurable per AGENTS.md).
