# Implementation Plan

## Purpose

This directory contains the phased, implementation-ready plan for the **Real-Time Audio Translation System** — a browser-based application that captures microphone audio, streams it over WebSockets to a Python FastAPI backend, performs speech-to-text, translation, and text-to-speech (plus an alternative unified speech-translation path), and displays continuously updating transcript/translation results while the speaker is still speaking.

The plan is the **authoritative task-level roadmap**. Every phase is written so that a developer or AI coding agent can receive a single instruction such as `Implement Phase 3 from implementation-plan.` and implement that phase without redesigning the architecture.

Each phase is a **living progress tracker**: task checkboxes, progress counters, acceptance criteria, and verification procedures must be updated after every implementation pass.

## Source Documentation

The plan was derived from the following authoritative docs in `docs/`:

| Document | Role |
|---|---|
| `docs/architecture.md` | Phase-1 scope, system diagram, included/excluded capabilities |
| `docs/real_time_audio_translation_brd.md` | Business need, objectives, scope, success criteria |
| `docs/prd.md` | Product behavior, user flows, partial/final semantics, UI states |
| `docs/srs.md` | Functional & non-functional software requirements, event protocol, lifecycle |
| `docs/trd.md` (ARD) | Technical architecture: cascaded vs unified, provider abstraction, pipeline interface, error/logging, testing, deployment, mock providers |
| `docs/websocket-protocol.md` | WebSocket endpoint `/ws/translate` and client↔server message shapes |
| `docs/Translation.md` | Deep dive on Architecture A (cascaded STT+translation) vs Architecture B (unified SeamlessStreaming), comparison, recommended order |
| `docs/development.md` | (empty at time of writing — reserved for development conventions) |
| `AGENTS.md` | Project layout rules, frontend/backend responsibilities, layered backend (`api/services/providers/models/schemas/core/utils`), quality/testing/dependency rules |

If docs conflict, the plan prefers — in order — most-specific/latest doc, explicit architectural decisions, documented technology constraints, and simplest production-appropriate interpretation. Important assumptions are called out in each phase's **Risks / Notes**.

## Phase Overview

| Phase | Name | Objective | Status | Progress |
|---|---|---|---:|---|
| Phase 1 | Project & Development Foundation | Repo structure, env config, logging, lint/format, testing harness, dev scripts | Completed | 100% |
| Phase 2 | Backend Foundation & HTTP API | Modular FastAPI app, config management, health/readiness/capabilities, CORS, error format,薄 API layer | Completed | 100% |
| Phase 3 | Frontend Foundation & UI Shell | React/Vite foundations, routing/shell, state management, language selector, transcript/translation areas, connection & error UI | Completed | 100% |
| Phase 4 | WebSocket Foundation & Session Lifecycle | `/ws/v1/translate` gateway, JSON control messages, binary audio framing, session service, bounded queues, backpressure, disconnect cleanup | Completed | 100% |
| Phase 5 | Browser Audio Pipeline & Real-time Streaming | getUserMedia, AudioContext/AudioWorklet, PCM S16LE mono 16 kHz, chunking, binary WS streaming, backend audio queue | Completed | 100% |
| Phase 6 | Provider Abstraction, Mocks & Event Normalization | Base provider interfaces, mock STT/translation/TTS, common normalized event protocol, pipeline interface | Completed | 100% |
| Phase 7 | Streaming STT & Transcript Stabilization | Real free/self-hosted streaming STT, partial/final handling, segment_id lifecycle, transcript stabilization, UI replacement semantics | Not Started | 0% |
| Phase 8 | Translation Layer & Cascaded Pipeline | Translation provider, partial/final translation, unstable-partial handling, cascaded STT→Translation→(TTS stub) orchestration | Not Started | 0% |
| Phase 9 | TTS & Unified Speech Translation & Pipeline Switching | TTS provider + playback, unified model evaluation & adapter, environment-configured pipeline selection, readiness gating | Not Started | 0% |
| Phase 10 | Hardening, Performance, Testing & Production Readiness | Error taxonomy hardening, performance instrumentation, full test pyramid, E2E (cascaded + unified), benchmarking & arch decision | Not Started | 0% |

## Overall Progress

- Total phases: **10**
- Completed phases: **6**
- In-progress phases: **0**
- Not-started phases: **4**
- Blocked phases: **0**
- Overall task progress: **143 / 273 tasks (52%)**

Progress is computed from the sum of every phase's checklist. Update it whenever a phase's checklist changes.

## Architecture Progression

The phases move strictly in dependency order so every increment leaves the system in a **working, verifiable state**:

```
Foundation
  → Backend HTTP API            (health, readiness, capabilities)
  → Frontend Shell              (language selection, transcript/translation placeholders)
  → WebSocket + Sessions        (control protocol, lifecycle, bounded queues)
  → Browser Audio               (mic capture, PCM conversion, chunked streaming)
  → Provider Abstractions       (interfaces, mocks, event normalization)
  → Streaming STT               (partial/final transcripts, stabilization)
  → Translation / Cascaded      (incremental translation, pipeline orchestration)
  → TTS / Unified / Switching   (audio output, unified model, env-driven selection)
  → Performance / Testing / Prod (measurements, full test coverage, hardening)
```

Core invariant preserved throughout:

```
Browser                           FastAPI
  Microphone                        WebSocket Gateway (thin)
      ↓                                  ↓
  AudioWorklet                  Translation Session Service
      ↓                                  ↓
  PCM S16LE mono 16kHz          Pipeline Interface
      ↓                            ┌─────┴─────┐
  WebSocket (binary)             Cascaded     Unified
      ↓                          STT→MT→TTS   Speech Translation
  Bounded Audio Queue                   └─────┬─────┘
      ↓                                      ↓
                                   Event Normalizer
                                             ↓
                                     WebSocket Events
                                             ↓
                                       React Live UI
```

No phase introduces database, authentication, Redis, Celery, Kafka, Kubernetes, microservices, persistent audio storage, or paid cloud AI APIs — the entire real-time path remains `Browser → WebSocket → FastAPI in-process session → audio queue → pipeline → local model → normalized events → WebSocket → Browser`.

## How to Use This Plan

1. **Start with the earliest incomplete phase** (lowest `N` whose `Progress < 100%`).
2. **Read the phase file top-to-bottom**: prerequisites, starting/target state, checklist, detailed instructions, and acceptance criteria.
3. **Execute tasks in checklist order** (they are dependency-ordered; respect any explicit `Depends on:` annotations).
4. **Update checkboxes as you go**:
   - `[ ]` Not started · `[x]` Completed (implemented **and** verified) · `[~]` Partially completed · `[!]` Blocked (add reason).
5. **Run the phase's Verification Procedure** (commands, browser checks, WS checks, log inspection).
6. **Mark acceptance criteria** `[x]`/`[ ]` and update the **Progress** table (all four counters + `Progress: XX%`, `Status`, `Last Updated`).
7. **If architecture diverged**: add/update tasks with new IDs, never silently delete unfinished tasks, and note the change in the phase's **Risks / Notes**.
8. **Proceed to the next incomplete phase** only after the current phase meets the **Phase Completion Rule** (all required tasks verified, tests passing, verification completed, no required `[ ]`).

## Conventions Used Throughout

- **Task IDs**: `P<phase>-<category>-<number>` — categories include `BE`, `FE`, `INT`, `WS`, `AUDIO`, `PIPE`, `MODEL`, `TTS`, `TEST`, `PERF`, `DOC`, `DEV`, `CFG`, `ERR`.
- **Phase progress block** appears near the top of every phase file and must be kept consistent with the checklist.
- **Detailed Task Instructions** expand every non-trivial task with file locations, expected behavior, and how to verify.
- **Related documentation** is listed per phase; if a phase creates a new architectural decision, add a `P*-DOC-*` task to update or create an ADR/doc.
- **Implementation-plan must be updated** after every implementation pass — it is the single source of truth for "what's done, what's blocked, what remains."

## References

- `docs/architecture.md`, `docs/real_time_audio_translation_brd.md`, `docs/prd.md`, `docs/srs.md`, `docs/trd.md`, `docs/Translation.md`, `docs/websocket-protocol.md`, `AGENTS.md`
- `backend/` and `frontend/frontend/` (existing scaffold at time of plan creation)
