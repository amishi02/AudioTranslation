# Real-Time Audio Translation

Browser-based real-time audio translation: **microphone → WebSocket → FastAPI → STT → Translation → TTS → WebSocket → Browser**.

Phase 1 **complete (10/10 phases, 100%)** — dual pipelines (cascaded `STT→Translation→TTS` + unified `Seamless` mock), 12-code error taxonomy, `T0-T5` latency instrumentation, concurrent load harness, and `GET /metrics`. See `docs/architecture.md` and `implementation-plan/README.md`.

## Repository Structure

```
.
├── backend/            # Python FastAPI (app/{api,services,providers,models,schemas,core,utils})
├── frontend/frontend/  # React + Vite + JS/JSX (canonical nested path per phase1.md P1-DEV-001)
├── docs/               # BRD, PRD, SRS, TRD, websocket-protocol, architecture, benchmark, adr/
├── implementation-plan/ # Phased roadmap (README + phase1..phase10) — authoritative tracker
├── Makefile            # dev/lint/test shortcuts
└── AGENTS.md           # Working instructions
```

> Do not combine frontend and backend code. All phase docs reference `frontend/frontend/`.

## Prerequisites

- **Git**, **Python 3.11+**, **Node 18+** (Node 20 recommended), **npm 9+**
- Linux/macOS recommended. For STT/translation models, 4 GB free disk for weights (`~/.cache/huggingface`).
- No GPU required — `faster-whisper` `int8` + `Opus-MT` run on CPU. GPU (`STT_DEVICE=cuda`, `TRANSLATION_DEVICE=cuda`) auto-used if `torch.cuda.is_available()`.

## Clone & Setup (from GitHub)

```bash
# 1. Clone
git clone https://github.com/amishi02/AudioTranslation.git
cd AudioTranslation

# 2. Backend — venv + dependencies
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt    # pinned runtime + dev (fastapi, torch, transformers, faster-whisper, etc.)
# Alternative (pyproject): pip install -e .  # uses backend/pyproject.toml dependencies

# 3. Backend — environment
cp .env.example .env               # then edit if needed
# Key vars: HOST/PORT, CORS_ORIGINS, PIPELINE_TYPE=cascaded|unified,
# STT_PROVIDER=whisper|mock, TRANSLATION_PROVIDER=opus|nllb|mock, TTS_PROVIDER=piper|mock,
# STT_MODEL=base|tiny|small, SESSION_IDLE_TIMEOUT_MS, RATE_LIMIT_*, PERF_ENABLED
# Never commit .env

# 4. Frontend — dependencies + env
cd ../frontend/frontend
npm install                        # react@19, vite@8, vitest@3, eslint, testing-library
cp .env.example .env
# Key vars: VITE_API_BASE_URL=http://localhost:8000, VITE_WS_URL=ws://localhost:8000/ws/v1/translate
# Must match backend WS_V1_PATH

# 5. Verify installs
cd ../../backend && .venv/bin/python -m pytest -q          # 70 tests, ~45s
cd ../frontend/frontend && npm run lint && npm run build   # eslint + vite build
```

### Backend Dependencies (pinned)

Core runtime: `fastapi==0.141`, `uvicorn==0.53` (with `uvloop`, `httptools`, `watchfiles`), `starlette`, `pydantic`/`pydantic-settings`, `websockets`, `httpx`, `huggingface_hub`, `transformers` + `sentencepiece`/`tokenizers`, `faster-whisper` + `ctranslate2`, `torch` + `onnxruntime`, `numpy`, `av`, `sounddevice`, `python-dotenv`, `tqdm`, `safetensors`. Dev: `ruff`, `mypy`, `pytest`/`pytest-asyncio`. See `backend/requirements.txt` (92 pins, including CUDA wheels) and `backend/pyproject.toml` (`dependencies` mirrors the above).

Models are **downloaded on first use** (lazy per-pair for Opus-MT, lazy for Whisper) to `~/.cache/huggingface` via `huggingface_hub` (HEAD + GET logs are normal). Offline after first download: `HF_HUB_OFFLINE=1`.

### Frontend Dependencies (pinned)

Runtime: `react@19.2.8`, `react-dom@19.2.8`. Dev: `vite@8`, `vitest@3`, `jsdom@26`, `@testing-library/react@16`/`jest-dom@6`/`user-event@14`, `eslint@10` + `eslint-plugin-react-hooks/refresh`, `@vitejs/plugin-react@6`. See `frontend/frontend/package.json`.

## Models & Local Downloads

All models are **open-source / free, self-hosted** (no paid APIs per `AGENTS.md`). Weights are **downloaded once on first use**, then cached locally and used offline. No code change needed to switch models — only `.env` (`backend/app/core/config.py` → `ProviderFactory` → interface).

| Role | Provider (`*_PROVIDER`) | Model (`*_MODEL`) | Env Example | Size | Local Path | Download Trigger |
|---|---|---|---|---|---|---|
| STT | `whisper` (via `faster-whisper` + `ctranslate2`) | `tiny` (39M), `base` (74M), `small` (244M) — `openai/whisper-*` | `STT_MODEL=tiny` `STT_DEVICE=cpu` `STT_COMPUTE_TYPE=int8` | tiny ~150 MB, base ~300 MB | `~/.cache/huggingface/hub/` + `~/.cache/huggingface/hub/models--Systran--faster-whisper-*` or `ctranslate2` cache | `WhisperModel(STT_MODEL, device, compute_type)` on first `startSession` (`backend/app/providers/stt/whisper.py:171`) |
| Translation | `opus` (Helsinki-NLP Marian) | `Helsinki-NLP/opus-mt-{src}-{tgt}` per pair (e.g., `opus-mt-en-hi`, `opus-mt-es-en`)  | `TRANSLATION_MODEL=Helsinki-NLP/opus-mt-{src}-{tgt}` `TRANSLATION_DEVICE=cpu` | ~300 MB per pair | `~/.cache/huggingface/hub/models--Helsinki-NLP--opus-mt-*` | `AutoTokenizer/ AutoModelForSeq2SeqLM.from_pretrained(name)` on first `translate(src→tgt)` per pair (`backend/app/providers/translation/opus.py:132`), pivot via `en` for `hi↔es/fr/de` (20 pairs, 8 direct + 12 pivoted) |
| Alternative Translation | `nllb` | `facebook/nllb-200-distilled-600M` | `TRANSLATION_PROVIDER=nllb` | ~2.4 GB | `~/.cache/huggingface/hub/models--facebook--nllb-*` | same `from_pretrained` path |
| TTS | `piper` (ONNX, MIT, CPU real-time) | `piper:en_US-lessac-medium` etc. per voice, `VOICE_MAP` in `app/providers/tts/piper.py:16` | `TTS_MODEL=piper:en_US-lessac-medium` `TTS_DEVICE=cpu` | <50 MB per voice | `~/.cache/piper` or `models/` ONNX | `piper` ONNX load on first `synthesize` |
| Unified (opt-in) | `seamless` (`facebook/seamless-streaming`, CC-BY-NC-4.0 ⚠️) | `facebook/seamless-streaming` (~2.5B) | `PIPELINE_TYPE=unified` `UNIFIED_MODEL=facebook/seamless-streaming` | ~9 GB | `~/.cache/huggingface/hub/models--facebook--seamless-*` | `AutoModel.from_pretrained` in `speech_translation/seamless.py` (mock fallback if `UNIFIED_PROVIDER=mock`) |

**Default env (ships in `backend/.env.example` → `backend/.env`):**

```
PIPELINE_TYPE=cascaded
STT_PROVIDER=whisper  STT_MODEL=tiny  STT_DEVICE=cpu  STT_COMPUTE_TYPE=int8
TRANSLATION_PROVIDER=opus  TRANSLATION_MODEL=Helsinki-NLP/opus-mt-{src}-{tgt}
TTS_PROVIDER=mock     TTS_MODEL=piper:en_US-lessac-medium
UNIFIED_PROVIDER=mock UNIFIED_MODEL=facebook/seamless-streaming
```

Switch by editing only `.env`: e.g., `STT_MODEL=base` (better multilingual, +150 MB), `TRANSLATION_PROVIDER=nllb`, `TTS_PROVIDER=piper`, `PIPELINE_TYPE=unified` — no code edits.

#### Pre-download locally (recommended before first session)

```bash
source backend/.venv/bin/activate
# 1. STT — tiny (default) or base
python -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu', compute_type='int8')"
# or base: python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"

# 2. Translation — each pair you need (example en->hi, es->en)
python -c "from transformers import AutoTokenizer, AutoModelForSeq2SeqLM; n='Helsinki-NLP/opus-mt-en-hi'; AutoTokenizer.from_pretrained(n); AutoModelForSeq2SeqLM.from_pretrained(n)"
python -c "from transformers import AutoTokenizer, AutoModelForSeq2SeqLM; n='Helsinki-NLP/opus-mt-es-en'; AutoTokenizer.from_pretrained(n); AutoModelForSeq2SeqLM.from_pretrained(n)"
# Alternative: huggingface-cli (if installed): huggingface-cli download Helsinki-NLP/opus-mt-en-hi

# 3. TTS Piper voice (if TTS_PROVIDER=piper)
# piper binary must be installed separately; mock TTS needs no download

# 4. (Opt-in) Unified — large, GPU recommended
# python -c "from transformers import AutoModel; AutoModel.from_pretrained('facebook/seamless-streaming', trust_remote_code=True)"
```

#### Verify cache

```bash
ls -lh ~/.cache/huggingface/hub/ | grep -E "faster-whisper|opus-mt|nllb"
du -sh ~/.cache/huggingface/hub/models--Helsinki-NLP--opus-mt-* 2>/dev/null
du -sh ~/.cache/huggingface/hub/models--Systran--faster-whisper-* 2>/dev/null
# Or via Python
python -c "from huggingface_hub import scan_cache_dir; print(scan_cache_dir().size_on_disk_str)"
```

#### Run fully offline after first download

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 make dev-backend
# or: HF_HUB_OFFLINE=1 .venv/bin/uvicorn app.main:app --reload
```

`HEAD https://huggingface.co/... 404` / `302` / `307` logs during first download are normal probes (`safetensors` vs `pytorch_model.bin`, etag cache check) from `huggingface_hub`/`httpx` — weights cached thereafter, no re-download (see `opus.py:132` / `whisper.py:171` path).

#### Updating / Clearing

```bash
# Remove a single model to re-download
rm -rf ~/.cache/huggingface/hub/models--Helsinki-NLP--opus-mt-en-hi
# Clear all
rm -rf ~/.cache/huggingface/hub
# Custom location
HF_HOME=/data/hf_cache make dev-backend   # or export HF_HOME=/data/hf_cache
```

See `docs/models/stt-evaluation.md`, `translation-evaluation.md`, `tts-evaluation.md`, `unified-evaluation.md` for per-model latency/quality/VRAM trade-offs and `docs/adr/ADR-001-pipeline-selection.md` for cascaded default rationale.

## Running

Two terminals:

```bash
# Terminal 1 — backend (from repo root)
make dev-backend            # cd backend && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# -> http://localhost:8000  health: GET /health, ready: GET /health/ready, metrics: GET /metrics, docs: GET /docs

# Terminal 2 — frontend
make dev-frontend           # cd frontend/frontend && npm run dev -- --host
# -> http://localhost:5173

# Or manually:
# backend:  source backend/.venv/bin/activate && uvicorn app.main:app --reload --port 8000
# frontend: cd frontend/frontend && npm run dev
```

Env overrides: `PORT=8001 make dev-backend`, `VITE_WS_URL=ws://localhost:8001/ws/v1/translate` in `frontend/frontend/.env`.

### Quick Smoke

```bash
curl http://localhost:8000/health                 # {"status":"ok","version":"0.1.0"}
curl http://localhost:8000/health/ready           # {model_ready, stt_ready, translation_ready, ...}
curl http://localhost:8000/metrics                # {sessions_started, frames_received, p50_total_ms, ...}
curl http://localhost:8000/api/v1/capabilities    # {supported_languages, pipeline_types, default_pipeline}
```

Browser: open `http://localhost:5173` → select `en → hi` → **Start Translation** → speak → see `transcript` partials replaced → `final` committed → `translation` shown → (if TTS `piper`) hear audio. **Stop** ends session; `SESSION_TIMEOUT`/`RATE_LIMITED` shows `Try Again`.

## Configuration

All dynamic values are **env-configurable** (no hard-coded URLs/paths/model names):

- Backend: `backend/.env.example` → `app/core/config.py` via `pydantic-settings` (`extra="ignore"`). Includes `APP_*`, `HOST/PORT`, `CORS_ORIGINS`, `WS_V1_PATH=/ws/v1/translate`, `SUPPORTED_LANGUAGES`, `PIPELINE_TYPE`, `STT_*`, `TRANSLATION_*`, `TTS_*`, `UNIFIED_*`, `AUDIO_*`, `SESSION_IDLE_TIMEOUT_MS=15000`, `SESSION_MAX_DURATION_MS=600000`, `WS_MAX_QUEUE_DEPTH=64`, `RATE_LIMIT_FRAMES_PER_SECOND=50`, `RATE_LIMIT_BYTES_PER_SECOND=320000`, `STT_WINDOW_FINAL_EVERY_S`, `STT_PARTIAL_THROTTLE_MS`, `STT_LIVE_WINDOW_S`, `PERF_ENABLED`, `METRICS_ENABLED`.
- Frontend: `frontend/frontend/.env.example` → `import.meta.env` in `src/config/environment.js` — `VITE_API_BASE_URL`, `VITE_WS_URL`, `VITE_API_V1_PREFIX`, `VITE_HEALTH_PATH`, etc.

Switching models requires only `.env` changes (factory pattern), e.g. `STT_MODEL=small`, `TRANSLATION_PROVIDER=nllb`, `TTS_PROVIDER=piper`, `PIPELINE_TYPE=unified` — no code edits in `services/`/`api/`/`frontend/`.

## Development Commands

```bash
make help            # list targets
make dev-backend     # uvicorn --reload @ 8000
make dev-frontend    # vite --host @ 5173
make lint            # ruff check + mypy (backend) + eslint (frontend)
make format          # ruff format (backend)
make test            # pytest -q (backend)
make test-backend    # alias
make build-frontend  # vite build

# Direct:
cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy app && .venv/bin/python -m pytest -q
cd frontend/frontend && npm run lint && npm run build && npm run test
cd backend && python scripts/load_ws_sessions.py --n 5 --fixture tests/fixtures/hello_16k.pcm
```

## Testing

- Backend: `backend/tests/` (`pytest` + `pytest-asyncio`, `asyncio_mode=auto`) — 70 tests: health/readiness, capabilities, WebSocket lifecycle (`test_websocket.py`), audio streaming/backpressure, STT/translation/TTS/unified integration, **error taxonomy** (`test_errors.py`, 12 codes), **WS guards/timeouts/rate-limits/metrics** (`test_timeouts_rate_limits.py`), perf (`test_perf_instrumentation.py`), pipeline mocks, event normalizer.
- Frontend: Vitest (`frontend/frontend/src/__tests__/`, 34 tests + `src/__tests__/errorMessages.test.jsx` for 12-code mapping + PRD §37 edge cases: silence→no emit, very-short→final, pause→final, long-split), mocked `AudioContext` for playback.
- Load: `backend/scripts/load_ws_sessions.py --n 5` spawns concurrent WS clients feeding `hello_16k.pcm` at 60 ms cadence, reports `p50/p95` table for `docs/benchmark.md`.

No DB/Redis/Celery in real-time path (guarded by `test_no_forbidden_imports`).

## Architecture & Docs

- `docs/architecture.md` — Phase 10 diagram (dual pipelines, metrics, timeout, rate-limit, invariants).
- `docs/websocket-protocol.md` — `/ws/v1/translate` JSON (`start`/`stop`/`ping` → `session.ready`/`transcript`/`translation`/`audio.output.start|end`/`session.ended`/`pong`/`error`) + binary `PCM S16LE mono 16k` framing, 12 error codes, caps, metrics.
- `docs/trd.md` / `docs/srs.md` / `docs/prd.md` — requirements, partial/final semantics, T0-T5 benchmarking (`T0 mic → T1 WS → T2 STT → T3 translation → T4 TTS → T5 decode`).
- `docs/benchmark.md` + `docs/adr/ADR-001-pipeline-selection.md` — cascaded **default** (MIT/Apache, CPU, 20 pairs via pivot) vs unified (CC-BY-NC-4.0, GPU) decision.
- `docs/development.md` — dev workflow, error envelope (HTTP + WS `retryable`), testing, lint.
- `implementation-plan/README.md` — 10 phases, 273/273 tasks (100%). Phase 10 instruments hardening without third pipeline.

## Troubleshooting

- **Port in use**: `PORT=8001 make dev-backend` + update `frontend/frontend/.env` `VITE_WS_URL`.
- **CORS**: `CORS_ORIGINS` must include `http://localhost:5173` (dev). In `APP_ENV=production`, unknown `Origin` on WS upgrade is rejected (close 1008).
- **Mic not working**: `getUserMedia` requires HTTPS in prod or `localhost`; allow mic in browser site settings.
- **Models slow on CPU**: expected — `base` whisper int8 ~300–600 ms per 1.5 s window. Try `STT_MODEL=tiny` or `STT_DEVICE=cuda`. First load downloads weights (~150–300 MB per pair).
- **HuggingFace 404 logs**: normal probes for optional `safetensors` vs `pytorch_model.bin`; weights cached in `~/.cache/huggingface`.
- **WS `RATE_LIMITED`**: frontend event throttled; slow speaking or wait 1 s window.
- **WS `SESSION_TIMEOUT`**: idle 15 s or max 10 min → `Try Again` restarts without reload.

## Code Quality

Per `AGENTS.md`: type hints, Pydantic, single-responsibility, `api/` thin → `services/` logic → `providers/` behind interfaces (`STTProvider`/`TranslationProvider`/`TTSProvider`/`UnifiedProvider`) via `PipelineFactory`, env-only model swap, structured logging (never log raw PCM bytes).

Check before committing:

```bash
cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy app && .venv/bin/python -m pytest -q
cd frontend/frontend && npm run lint && npm run build && npm run test
```

See `AGENTS.md` Git: `git status` + `git diff --staged` + `<prefix>: <descriptive>` (`feat`/`fix`/`perf`/`refactor`/`docs`/`test`/`chore`) and `implementation-plan/` progress updates per phase.

## Implementation Plan

Authoritative roadmap in `implementation-plan/` (phases 1–10). After each change: update `phaseN.md` checklist + `## Progress` table, `implementation-plan/README.md` overview, remove dead code, update `docs/` or `docs/adr/`.

## Feedback

Report at `https://github.com/anomalyco/opencode` (mention Muse Spark).
