# Real-Time Audio Translation

Browser-based real-time audio translation: microphone → WebSocket → FastAPI → STT → Translation → TTS → WebSocket → Browser.

## Prerequisites

- Git, Python 3.11+, Node 18+ (Node 20 recommended)
- 4 GB free disk for model weights (`~/.cache/huggingface`)

## Setup

### 1. Clone

```bash
git clone https://github.com/amishi02/AudioTranslation.git
cd AudioTranslation
```

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` if needed (`PIPELINE_TYPE`, `STT_MODEL`, `TRANSLATION_PROVIDER`, `PORT`, `CORS_ORIGINS`).

### 3. Frontend

```bash
cd ../frontend/frontend
npm install
cp .env.example .env
```

### 4. Download Models Locally

Models are open-source and cached to `~/.cache/huggingface/hub` on first use. Pre-download to avoid first-request delay:

```bash
source ../../backend/.venv/bin/activate
# STT — whisper tiny (default, ~150 MB) or base (~300 MB)
python -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu', compute_type='int8')"
# Translation — per pair (~300 MB each)
python -c "from transformers import AutoTokenizer, AutoModelForSeq2SeqLM; n='Helsinki-NLP/opus-mt-en-hi'; AutoTokenizer.from_pretrained(n); AutoModelForSeq2SeqLM.from_pretrained(n)"
python -c "from transformers import AutoTokenizer, AutoModelForSeq2SeqLM; n='Helsinki-NLP/opus-mt-es-en'; AutoTokenizer.from_pretrained(n); AutoModelForSeq2SeqLM.from_pretrained(n)"
```

Models used: `faster-whisper` `tiny`/`base` (ctranslate2), `Helsinki-NLP/opus-mt-{src}-{tgt}` (transformers/Marian), `piper` voices (if `TTS_PROVIDER=piper`), `facebook/seamless-streaming` (opt-in unified, ~9 GB). All env-configurable in `backend/.env` (`STT_MODEL`, `TRANSLATION_MODEL`, `TTS_MODEL`).

Verify:
```bash
ls ~/.cache/huggingface/hub/ | grep -E "faster-whisper|opus-mt"
```

Run offline after first download:
```bash
HF_HUB_OFFLINE=1 make dev-backend
```

### 5. Run Backend

```bash
# from repo root
make dev-backend
# or: cd backend && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# health: http://localhost:8000/health  ready: http://localhost:8000/health/ready  docs: http://localhost:8000/docs
```

### 6. Run Frontend

```bash
# new terminal, from repo root
make dev-frontend
# or: cd frontend/frontend && npm run dev -- --host
# -> http://localhost:5173
```

Open `http://localhost:5173` → select `en → hi` → Start Translation → speak.

## Verify

```bash
cd backend && .venv/bin/python -m pytest -q
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
```
