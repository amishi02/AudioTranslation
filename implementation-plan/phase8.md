# Phase 8: Translation Layer & Cascaded Pipeline

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

Related documentation: `docs/trd.md` §12-15 (translation, incremental strategies, cascaded advantages/limitations), `docs/Translation.md` §9-10 (translation layer, important issue with Architecture A), `docs/srs.md` §5 FR-010..013 (translation), `docs/prd.md` §13 (translation display), `docs/websocket-protocol.md` (Translation event)

---

## 1. Objective

Implement the real translation layer, address the unstable-STT partial problem explicitly, and cement the cascaded pipeline `Audio → STT → Translation → (TTS pending)` so target-language text appears incrementally while the speaker is still speaking — with quality, latency, and segment consistency verifiable in-app.

## 2. Prerequisites

- Phase 7 complete: real streaming STT producing stable `transcript` events with `segment_id`
- Mock translation from Phase 6 still wired (to be replaced); `TranslationProvider` interface + `TranslationEvent` schema already exist
- At least one free/self-hosted translation model evaluated (candidates below); CPU inference verified locally
- Frontend `Provider` and `pipeline` state enforced; WS channel supports `translation` events

## 3. Expected Starting State

- `CascadedPipeline` does `stt.poll → mock_translate(text) → TranslationEvent` via `MockTranslationProvider`
- `TranslationEvent` is `source_text` + `translated_text` per `segment_id` with `partial`/`final` but backed by placeholder strings
- No real translation model loaded; no unstable-partial decision rule; no translation buffering
- Frontend translation panel updates from mocks correctly per `segment_id` semantics

## 4. Target State

- Real translation provider (env-selected) translates STT-produced transcript segments, emitting `translation` events that share the same `segment_id` as their source `transcript` event
- Pipeline implements an incremental translation strategy (one of A–D from TRD §13), documented and parameterized, that balances latency vs stability (default: hybrid — translate stable translation immediately upon `final`, update `partial` translations below a rate limit for `partial` sources)
- Cascaded pipeline orchestrates end-to-end: accumulated PCM → STT partial/final transcripts → translation partial/final → normalized events → WS → React `Translation.jsx`
- API validation rejects unsupported `(source_language,target_language)` combinations via model capabilities lookup, emitting `UNSUPPORTED_LANGUAGE`
- Translation latency, partial-update frequency, and quality are observable for comparison before TTS and unified phases
- Mock translation remains available via env for offline/CI testing

## 5. Task Checklist

### Model Evaluation & Selection

- [ ] P8-MODEL-001 Evaluate free/self-hosted translation candidate 1: `Helsinki-NLP/opus-mt-*` (MarianMT) — per language pair — document license (Apache-2.0 for Marian, Opus-MT models CC-derived), pair coverage, model size (~300MB/pair), CPU latency, quality for en↔hi
- [ ] P8-MODEL-002 Evaluate translation candidate 2: `facebook/nllb-200-distilled-600M` (Meta NLLB) — multilingual single model, Apache-2.0, larger (~2.3GB for 600M), broader coverage (200 languages), higher latency, quality trade-off
- [ ] P8-MODEL-003 Record comparison ADR/doc and select `TRANSLATION_PROVIDER`/`TRANSLATION_MODEL` (allow `TRANSLATION_PROVIDER=mock|opus|nllb` env switch)
- [ ] P8-MODEL-004 Document supported `(source→target)` pairs for chosen model and where to add pair-model files (Opus-MT: one checkpoint per pair)

### Backend — Real Translation Provider

- [ ] P8-BE-001 Implement `backend/app/providers/translation/opus.py` (or `nllb.py`) `OpusTranslationProvider` (or `NLLBTranslationProvider`) fulfilling `TranslationProvider` interface
- [ ] P8-BE-002 Implement model loading during app startup or lazily on first `translate()` call (documented choice); load model/tokenizer per language pair on demand where Opus-MT per-pair
- [ ] P8-BE-003 Implement `async def translate(self, text: str, source_lang: str, target_lang: str) -> str` calling `model.generate(tokenized_input)` behind executor if synchronous
- [ ] P8-BE-004 Implement batching/cache helper so identical `(source_lang,target_lang,text)` repeated partials do not re-invoke inference unnecessarily
- [ ] P8-BE-005 Map unsupported pair → `UNSUPPORTED_LANGUAGE` error; invalid language code normalization (`en`→`en`, `hi`→`hi`) with `INVALID_SESSION_CONFIG` if neither pair nor code is supported
- [ ] P8-BE-006 Add provider-specific config fields: `translation_device`, `translation_compute_type`, `translation_max_length`, `translation_num_beams` (document defaults)

### Pipeline — Incremental Translation Strategy

- [ ] P8-PIPE-001 Select and document incremental strategy per TRD §13:
  - Strategy A (translate every `partial` as-is)
  - Strategy B (only stable phrases)
  - Strategy C (only `final` segments — most stable, higher latency)
  - Strategy D (hybrid: stable immediate + rate-limited partial updates) — recommended default
- [ ] P8-PIPE-002 Extend `CascadedPipeline` to track `SegmentState {segment_id, transcript_text, status, last_translation_text, last_translated_at}` so decision uses transcript `status`
- [ ] P8-PIPE-003 Wire cascaded loop: `stt_events = await stt.poll_events()` → for each `transcript` event, apply strategy → call `translation_provider.translate()` when appropriate → emit `TranslationEvent` sharing `segment_id`
- [ ] P8-PIPE-004 Add de-duplication: if `translated_text == last_translation_text` skip emitting the event (avoid WS churn)
- [ ] P8-PIPE-005 Add rate limit for partial translations (e.g., at most 1 translation per 250 ms per segment id) to avoid flicker
- [ ] P8-PIPE-006 Ensure `final` transcript always triggers a `final` translation emit (even if last partial was already sent) with identical `segment_id`

### Events & Session

- [ ] P8-BE-007 Ensure `TranslationEvent` normalized shape `{type:"translation", session_id, segment_id, status, source_text, translated_text, timestamp}` is produced by `EventNormalizer` for real provider
- [ ] P8-BE-008 Update `SessionService` pipeline orchestration to `gather` STT poll + translation dispatch without blocking `receive_task`

### Frontend

- [ ] P8-FE-001 Update `src/services/websocket.js` + `src/hooks/useSessionState.js` to handle `translation` events sharing `segment_id` with `transcript` events
- [ ] P8-FE-002 Ensure `Translation.jsx` mirrors `Transcript.jsx` replacement semantics (partial replace, final commit) and shows `source_text` tooltip or small muted source line when useful
- [ ] P8-FE-003 Display translation lag indicator (optional enhancement) when `partial` hasn't updated for `>500ms` — document if deferred

### Configuration

- [ ] P8-CFG-001 Env: `TRANSLATION_PROVIDER`, `TRANSLATION_MODEL`, `TRANSLATION_DEVICE`, `TRANSLATION_PAIR_MAP` (for Opus multi-pair) with validation
- [ ] P8-CFG-002 Readiness: readiness reflects `translation_ready` (no-op if translation is pure CPU/no-weight download already complete)

### Testing

- [ ] P8-TEST-001 Unit: translation provider loads selected model (mocked HF download when missing) and translates `"Hello my name is John"` fixture deterministically
- [ ] P8-TEST-002 Unit: `CascadedPipeline` incremental strategy — real STT events + mock translation, verify strategy D sends text-translation pairs respecting `status` and `segment_id`
- [ ] P8-TEST-003 Unit: de-duplication and rate-limit: identical successive partials don't emit, subtly-changed source re-emits, `final` always emits
- [ ] P8-TEST-004 Integration: WS with real STT + real translation (fixture PCM) → ordered `transcript` then `translation` events with matching `segment_id` per pair
- [ ] P8-TEST-005 Frontend unit: `translation` event reducer (same semantics as `transcript`) — partial replace, final commit, no dup line
- [ ] P8-TEST-006 Error path: unsupported pair `(en→xx_unknown)` yields `UNSUPPORTED_LANGUAGE` error instead of crashing

---

## 6. Detailed Task Instructions

### P8-MODEL-001 Opus-MT evaluation template
- Document: model name `Helsinki-NLP/opus-mt-en-hi` (and `hi-en` separately), provider Helsinki-NLP (MarianMT), license Apache-2.0 for Marian, model weights under CC-BY or similar (verify per pair), supports en↔hi among many pairs but requires one checkpoint per direction, STT no / translation yes / TTS no, streaming via per-request `generate` (no true streaming), local exec yes, CPU fast (~80–300 ms/sentence) GPU helpful for batched, VRAM minimal (~500 MB per loaded pair), size ~300 MB/pair, quality strong for hi/en per Opus benchmarks, install via `transformers` + `sentencepiece`; note tradeoff: many models to preload if supporting 5+ pairs.

### P8-MODEL-002 NLLB-200 evaluation template
- Document: `facebook/nllb-200-distilled-600M` per Meta, Apache-2.0, single model covering 200 languages, translation yes (no STT/TTS), no streaming translation (per-call), local yes (HF `transformers`), CPU slower (~400–800 ms/sentence on CPU) GPU preferred, VRAM ~4–6 GB, size ~2.3 GB (600M) / 3.3 GB (1.3B) — recommend 600M for Phase 8, quality broader coverage but slightly lower per-pair vs Opus for hi/en, single weight set for all pairs (operationally simpler than Opus per-pair).

### P8-BE-001 Translation provider skeleton
- Where: `backend/app/providers/translation/opus.py`. Maintains `models: dict[(src,tgt), MarianModel|Pipeline]` loaded into memory lazily: `def _get_model(src,tgt)` loads `Helsinki-NLP/opus-mt-{src}-{tgt}` via `AutoModelForSeq2SeqLM` + `AutoTokenizer` at first use, sets device, stores. Use `asyncio.to_thread` for `model.generate` if it is CPU-bound blocking (do not block `uvicorn` event loop). Keep `is_ready() -> bool` true once at least default pair is loaded or in mock mode.
- Why per-pair lazy: loading 10 pairs at startup would allocate ~3 GB immediately; lazy loading keeps cold start fast.

### P8-BE-004 Cache helper
- Where: Inside provider `LRUCache` of size ~64 keyed by `(src,tgt,text)` → `translated`. Invalidate when provider re-initialized. This prevents re-translation of identical `partial` hypotheses emitted repeatedly while speaker pauses (e.g., "Hello my" → "Hello my" duplicated on next poll).
- Verify: Call `translate("Hello", "en","hi")` twice → second call returns from cache (`log: cache_hit:true`).

### P8-PIPE-001 Incremental strategy D details
- Where: `backend/app/services/pipeline/cascaded.py` docstring at top.
  - Default is **Strategy D (hybrid)**:
    - On `transcript.status=="final"` → always translate (flush) → emit `translation final`.
    - On `transcript.status=="partial"` → translate **only if** `now - last_translated_at > RATE_LIMIT_MS(=250)` **and** source length change ≥ 2 chars or word boundary crossed (`last_word_count < current_word_count`). Emit `translation partial` with same `segment_id`.
    - Else: skip translation for this partial (buffer), next partial will decide.
  - Add constructor params `translate_partials: bool=True`, `partial_rate_limit_ms: int=250`, `min_char_delta: int=2` so strategy is tunable via `config.translation_partial_rate_limit_ms`.
- Documentation note: explicitly state that ordinary NMT (Opus/NLLB) are not simultaneous-translation models — this is best-effort incremental feeding; quality for very short prefixes may be lower; `final` is canonical quality.

### P8-PIPE-004 De-duplication
- Where: Before `await translation_provider.translate(...)`, compare emitted `last_translation_text` for that `segment_id`. If equal, return without emitting. Prevents WS flood when STT oscillates between same hypothesis (e.g., "Hello my" ⇄ "Hello my" due to window decode).
- Verify: Two successive identical `partial` transcripts produce 1 translation event, not 2.

### P8-PIPE-003 Wiring
- Where: Inside `CascadedPipeline.poll_events()` or `process_once()` helper called from `SessionService` processor loop:
  ```python
  transcript_events = await self.stt.poll_events(session_id)
  normalized = []
  for t in transcript_events:
      normalized.append(normalize(t))
      action = self._decide_translation_action(t)  # per strategy D
      if action == "translate":
          tr = await self.translation_provider.translate(t.text, src, tgt)
          normalized.append(TranslationEvent(type="translation", session_id=sid, segment_id=t.segment_id, status=t.status, source_text=t.text, translated_text=tr, timestamp=time.time()))
  return normalized
  ```
  Note: `STTProvider.poll_events` already returns normalized transcripts or raw as per contract; here consume normalized `TranscriptEvent`.

### P8-FE-001 Frontend wiring
- Where: `src/hooks/useSessionState.js` receives `translation` events sharing `segment_id`: maintain separate `translationSegments: Map<id, {sourceText, translatedText, status}>` parallel to `transcriptSegments`. UI lists keyed by `segment_id` in order. On `final`, move to finalized list like transcript path.
- Verify: Sending `transcript {id:1, text:"Hello"}` then `translation {id:1, translated_text:"नमस्ते", status:"partial"}` shows entry row with source+target in order.

### P8-TEST-004 Integration
- Where: `backend/tests/test_cascaded_integration.py` — load fixture PCM like Phase 7, push 8–12 frames via WS `TestClient` `send_bytes`, collect all events filtered by `type` and assert for each `segment_id` there is a `transcript` preceding a paired `translation`, status pairing is consistent (`partial`→`partial`, final→final), and all translation `source_text` equals their transcript `text`.
- Verify: Run with `TRANSLATION_PROVIDER=opus` if model available; with `mock` on CI by default.

## 7. Architecture / Data Flow

Phase 8 completes the **real cascaded path**:

```
Browser mic PCM → WS binary → audio_queue → CascadedPipeline
                                                   ↓
                                       STTProvider (real, Phase 7)
                                                   ↓  transcript {id, status}
                                          decide incremental action (Strategy D)
                                                   ↓
                                       TranslationProvider (real, Phase 8)
                                                   ↓  source_text + translated_text {id, status}
                                          EventNormalizer → (transcript, translation) pair
                                                   ↓
                                        WS send_json(pair)
                                                   ↓
                                    React: Transcript.jsx + Translation.jsx
                                           (segment_id-coupled, partial-replace, final-commit)
```

TTS generation still pending (Phase 9) — transcript/translation are the visible outputs this phase.

## 8. Files Expected to Be Created/Modified

Backend:
- `backend/app/providers/translation/opus.py` (new) and/or `translation/nllb.py` (new)
- `backend/app/providers/translation/__init__.py` (new/update)
- `backend/app/services/pipeline/cascaded.py` (modified: incremental decision logic, real translation wiring)
- `backend/app/services/event_normalizer.py` (modified: translation normalizations)
- `backend/app/schemas/events.py` (modified: `TranslationEvent` already present, verify alignment)
- `backend/app/core/config.py` (modified: translation envs + pair map)
- `backend/tests/test_cascaded_integration.py` (new)
- `backend/tests/test_translation_provider.py` (new)
- `backend/tests/fixtures/translation_pairs.json` (new expected fixture matrix)

Frontend:
- `frontend/src/hooks/useSessionState.js` (modified: translation segment reducer)
- `frontend/src/services/websocket.js` (modified: translation handler)
- `frontend/src/components/Translation.jsx` (modified: source_text display)
- `frontend/src/__tests__/translationReducer.test.js` (new)

## 9. Testing Requirements

- Unit: translation provider loads + translates fixture pairs (Opus vs mock), batch/cache behavior, language validation, unsupported pair → error code.
- Unit: pipeline strategy D decision matrix, de-duplication, rate-limit, `final` always translates.
- Integration: WS with real STT + real translation on fixture PCM → matched `segment_id` transcript+translation pair ordering, idempotent behavior when source unchanged.
- Frontend: translation reducer (same partial-replace/final-commit as transcript) and multi-segment ordering.
- Error/validation: unsupported pair from UI returns `UNSUPPORTED_LANGUAGE` via WS `error`.

## 10. Acceptance Criteria

- [ ] Free/self-hosted translation model evaluated and chosen; `TRANSLATION_PROVIDER=mock|opus|nllb` env switch documented and loadable.
- [ ] Real translation provider implements `TranslationProvider` with batched/cache help, language mapping, and `UNSUPPORTED_LANGUAGE` handling.
- [ ] Cascaded pipeline wires STT transcripts → translation with documented strategy D (rate-limited partial, always-translate final, de-duplicated).
- [ ] Every `transcript` and its paired `translation` share `segment_id` and their `status` values align (`partial`→`partial`, `final`→`final`).
- [ ] Identical successive partials do not re-emit translation; subtly-changed source does; `final` always emits.
- [ ] Frontend translation panel mirrors transcript stabilization (replace partial, commit final, coupled by id) with no duplicate lines.
- [ ] WS with real STT+translation on fixture PCM produces ordered transcript+translation pairs per segment id.
- [ ] Lint/type/test still green; backend readiness reflects translation provider if needed.

## 11. Verification Procedure

```bash
cd backend
# doc check: model evaluation present
cat docs/models/translation-evaluation.md 2>/dev/null || echo "verify phase doc exists"

# unit with mock (CI-safe)
TRANSLATION_PROVIDER=mock python -m pytest tests/test_translation_provider.py tests/test_cascaded_integration.py -q

# optional real model smoke (requires weights)
TRANSLATION_PROVIDER=opus STT_PROVIDER=whisper python -m pytest tests/test_cascaded_integration.py::test_real_pair -v

# WS manual with real pipeline
python - << 'PY'
from fastapi.testclient import TestClient
from app.main import app
import pathlib
pcm = pathlib.Path("tests/fixtures/hello_16k.pcm").read_bytes()
with TestClient(app).websocket_connect("/ws/v1/translate") as ws:
    ws.send_json({"type":"start","source_language":"en","target_language":"hi"})
    print("ready:", ws.receive_json())
    for off in range(0, len(pcm), 1920):
        ws.send_bytes(pcm[off:off+1920])
    for _ in range(12):
        ev = ws.receive_json(timeout=7)
        print(ev["type"], ev.get("segment_id"), ev.get("status"), ev.get("translated_text","")[:60])
    ws.send_json({"type":"stop"})
    print("ended:", ws.receive_json())
PY

cd ../frontend/frontend
npm run dev -- --host
# Browser: Start → speak → Source shows progressive STT, Translation shows incremental Hindi updating at same rhythm, both finalize together.
```

## 12. Known Limitations

- Translation models used (Opus/NLLB) are not simultaneous-translation models — very short-prefix translations may have lower quality; pair selection dict may be small (en↔hi etc.) until more `opus-mt-*` checkpoints downloaded.
- Per-pair Opus lazy loads weights on first request, so first translation for a new pair has cold-start latency; NLLB single-model alternative has higher constant memory.
- TTS generation and audio return still deferred to Phase 9; this phase's end effect is text-only.
- Unified model remains unimplemented — comparison to cascaded quality/latency happens after Phase 9.

## 13. Risks / Notes

- **Shadowing by STT quality**: Cascaded latency = STT latency + translation latency. Budgeting must compare STT window + one NMT forward pass — translation should remain <<100 ms on CPU for short sentence (Opus) but NLLB-600M may exceed; benchmark and consider beam/beam reduction.
- **Do not block event loop**: `model.generate` must run in `await asyncio.to_thread(lambda: model.generate(...))` because HF generate is CPU/GPU synchronous.
- **Cache invalidation**: Changing `(src,tgt)` must clear cache; same text under two pairs must not share cache entry.
- **Assume `hi` script**: Hindi requires Devanagari handling; sentencepiece/tokenizer must already handle unicode — smoke test with actual Hindi fixture to ensure no `encode` error.

## 14. Phase Completion Status

- Total tasks: 29
- Completed tasks: 0
- Partially completed tasks: 0
- Remaining tasks: 29
- Blocked tasks: 0
- Overall progress: 0%
- Acceptance criteria status: 0 / 8 satisfied

