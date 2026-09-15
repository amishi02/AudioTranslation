# Architecture Requirements and Design Document

# Real-Time Audio Translation System

**Document:** Architecture Requirements and Design Document
**Version:** 1.0
**Phase:** Phase 1, Core Real-Time Translation
**Status:** Initial Architecture
**Last Updated:** September 2026

---

# 1. Purpose

This document defines the technical architecture and architectural requirements for the Real-Time Audio Translation System.

The system must accept live microphone audio from a browser, process that audio continuously, and provide translated output while the speaker is still speaking.

Two AI processing approaches are supported by the architecture:

1. **Cascaded architecture**

   * Speech-to-Text
   * Translation
   * Text-to-Speech

2. **Unified/direct speech translation architecture**

   * A model or model pipeline capable of directly processing speech and producing translated output.

The architecture must allow either approach to be implemented without requiring changes to the frontend's fundamental communication model.

The actual approach should be selected based on measurable results, especially:

* End-to-end latency.
* Translation quality.
* Speech recognition quality.
* Streaming capability.
* Language coverage.
* Hardware requirements.
* Model size.
* Licensing.
* Local/self-hosted availability.
* Resource consumption.
* Stability during continuous speech.

---

# 2. Architectural Goals

The architecture must achieve the following goals.

## 2.1 Primary Goals

1. Real-time microphone audio streaming.
2. Low-latency processing.
3. Incremental speech recognition.
4. Incremental translation where possible.
5. Real-time translated output.
6. Translated audio playback where supported.
7. Stable partial and final results.
8. Model/provider independence.
9. Clean separation between frontend and backend.
10. Modular backend architecture.
11. Ability to switch between cascaded and unified models.
12. Ability to replace individual AI models.
13. Ability to operate without a database in Phase 1.
14. Ability to add authentication later without redesigning the processing pipeline.

---

# 3. Phase 1 Architectural Scope

Phase 1 includes:

```text
React Frontend
        |
        | WebSocket
        |
FastAPI Backend
        |
        +-- Audio Processing
        |
        +-- AI Processing
        |
        +-- Result Normalization
        |
        +-- WebSocket Response
```

AI processing can follow either:

```text
Approach A:

Audio
  ↓
STT
  ↓
Translation
  ↓
TTS
```

or:

```text
Approach B:

Audio
  ↓
Unified Speech Translation Model
  ↓
Translated Output
```

Phase 1 does not include:

* User registration.
* Authentication.
* Authorization.
* Database.
* Persistent user sessions.
* Translation history.
* Billing.
* Redis.
* Celery.
* Administrative features.

---

# 4. Architectural Principles

## 4.1 Separation of Concerns

Each component must have a clearly defined responsibility.

The frontend should not contain backend processing logic.

The WebSocket endpoint should not contain AI model implementation.

AI provider-specific code should not be embedded directly into the application service.

---

## 4.2 Model Agnostic Core

The core application must not depend directly on a specific AI model.

The architecture should support:

```text
Application
    |
    v
Model/Provider Interface
    |
    +-- Cascaded Pipeline
    |
    +-- Unified Speech Translation
```

This allows the system to evaluate different models without restructuring the entire application.

---

## 4.3 Real-Time First

The architecture must prioritize continuous processing.

The preferred flow is:

```text
Audio Chunk
    ↓
Process
    ↓
Partial Result
    ↓
Send Result
    ↓
Continue
```

rather than:

```text
Record Entire Sentence
    ↓
Process Entire Sentence
    ↓
Return Result
```

Batch processing may be used internally by a model if streaming is unavailable, but the application should minimize the resulting latency.

---

## 4.4 Stateless Application Design

Phase 1 should avoid persistent application state.

Each WebSocket connection represents an independent temporary translation session.

Session-specific state should exist only for the lifetime of the session.

---

## 4.5 Replaceable AI Components

The architecture must allow replacing:

```text
STT model
Translation model
TTS model
Unified speech translation model
```

without changing the frontend protocol.

---

## 4.6 Explicit Contracts

Communication between components must use explicit contracts.

Important contracts include:

```text
Frontend ↔ WebSocket API
WebSocket API ↔ Session Service
Session Service ↔ Processing Pipeline
Processing Pipeline ↔ Providers
Providers ↔ Model Runtime
```

---

# 5. High-Level Architecture

```text
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                       │
│                                                         │
│  ┌────────────┐ ┌──────────────┐ ┌──────────────────┐ │
│  │ Language   │ │ Audio        │ │ Transcript /     │ │
│  │ Selection  │ │ Capture      │ │ Translation UI   │ │
│  └────────────┘ └──────┬───────┘ └──────────────────┘ │
│                        │                                │
│                        ▼                                │
│                 WebSocket Client                        │
└────────────────────────┬────────────────────────────────┘
                         │
                         │ WebSocket
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Backend                        │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │ WebSocket API                                     │  │
│  └──────────────────────┬────────────────────────────┘  │
│                         │                               │
│                         ▼                               │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Translation Session Manager                       │  │
│  └──────────────────────┬────────────────────────────┘  │
│                         │                               │
│                         ▼                               │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Processing Pipeline                               │  │
│  │                                                   │  │
│  │  Pipeline Strategy Selection                      │  │
│  └───────────────┬───────────────────────┬───────────┘  │
│                  │                       │              │
│                  ▼                       ▼              │
│        ┌──────────────────┐    ┌────────────────────┐ │
│        │ Cascaded Pipeline│    │ Unified Translation│ │
│        │                  │    │                    │ │
│        │ STT → Translate  │    │ Speech →           │ │
│        │ → TTS            │    │ Translation        │ │
│        └────────┬─────────┘    └─────────┬──────────┘ │
│                 │                        │             │
│                 └───────────┬────────────┘             │
│                             ▼                          │
│                  Result/Event Normalizer                │
│                             │                          │
│                             ▼                          │
│                      WebSocket API                     │
└─────────────────────────────────────────────────────────┘
```

---

# 6. Component Architecture

# 6.1 Frontend

Technology:

```text
React
Vite
JavaScript
JSX
WebSocket API
Web Audio APIs
```

The frontend is responsible for:

* User interaction.
* Language selection.
* Microphone access.
* Audio capture.
* Audio streaming.
* WebSocket communication.
* Transcript display.
* Translation display.
* Translated audio playback.
* Connection status.
* Basic error presentation.

The frontend must not contain AI model logic.

---

# 6.2 Backend

Technology:

```text
Python
FastAPI
Uvicorn
Pydantic
```

The backend is responsible for:

* WebSocket connections.
* Session management.
* Audio processing.
* AI pipeline orchestration.
* Provider management.
* Result normalization.
* Error handling.
* Logging.
* Configuration.

---

# 6.3 WebSocket Gateway

The WebSocket gateway is responsible for communication between the frontend and backend.

Responsibilities:

* Accept WebSocket connections.
* Validate connection/session messages.
* Receive audio.
* Forward audio to the session service.
* Receive normalized events.
* Send events back to the frontend.
* Handle disconnection.
* Trigger session cleanup.

The WebSocket gateway must not contain:

* STT implementation.
* Translation implementation.
* TTS implementation.
* Model initialization.
* Complex business logic.

---

# 6.4 Translation Session

Each WebSocket connection creates a temporary translation session.

Conceptually:

```text
TranslationSession
│
├── session_id
├── source_language
├── target_language
├── processing_mode
├── audio_state
├── transcript_state
├── translation_state
└── provider_state
```

The session owns state associated with one active translation stream.

Session state must not be shared between users/connections.

---

# 7. Audio Processing Architecture

The frontend captures microphone audio.

The captured audio is divided into small chunks.

```text
Microphone
    ↓
Browser Audio API
    ↓
Audio Capture
    ↓
Audio Chunk
    ↓
WebSocket
    ↓
Backend Audio Processor
```

The backend audio processor may perform:

* Format validation.
* Decoding.
* Resampling.
* Channel conversion.
* PCM conversion.
* Buffering.
* Chunk aggregation when required by a model.

The audio processor should remain independent from the AI provider.

---

# 8. Audio Buffering

Audio buffering must balance latency and model requirements.

If the chunks are too small:

```text
Too many messages
High overhead
Potential model inefficiency
```

If chunks are too large:

```text
Higher latency
Poor real-time behavior
Delayed results
```

Therefore, the system should make chunk size configurable.

The optimal chunk size should be determined experimentally.

---

# 9. Processing Architecture

The processing layer should support a common pipeline interface.

Conceptually:

```python
class TranslationPipeline:
    async def start_session(...):
        ...

    async def process_audio(...):
        ...

    async def receive_events(...):
        ...

    async def end_session(...):
        ...
```

The exact interface may evolve during implementation.

Two implementations should be possible:

```text
CascadedTranslationPipeline
UnifiedTranslationPipeline
```

---

# 10. Approach A: Cascaded Architecture

## 10.1 Overview

The cascaded approach uses independent models or providers:

```text
Audio
  ↓
Speech-to-Text
  ↓
Source Text
  ↓
Translation
  ↓
Translated Text
  ↓
Text-to-Speech
  ↓
Translated Audio
```

Each component is independently replaceable.

---

# 11. Cascaded STT Architecture

The STT component receives audio chunks.

It produces events such as:

```text
partial transcript
final transcript
```

Example:

```json
{
  "type": "transcript",
  "segment_id": "1",
  "status": "partial",
  "text": "Hello how"
}
```

Later:

```json
{
  "type": "transcript",
  "segment_id": "1",
  "status": "partial",
  "text": "Hello how are"
}
```

Finally:

```json
{
  "type": "transcript",
  "segment_id": "1",
  "status": "final",
  "text": "Hello, how are you?"
}
```

The STT provider is responsible for communicating with the underlying model.

---

# 12. Cascaded Translation

The translation service receives recognized text.

The service should not assume that every partial transcript is independently translatable.

For example:

```text
Partial 1:
Hello

Partial 2:
Hello how

Partial 3:
Hello how are

Partial 4:
Hello how are you
```

Naively translating every partial can result in:

```text
Translation 1
Translation 2
Translation 3
Translation 4
```

which may create:

* Duplicate translations.
* Incorrect grammar.
* Constantly changing output.
* Unnecessary model calls.

Therefore, the translation layer should maintain enough state to determine when a useful translation unit can be produced.

---

# 13. Incremental Translation Strategy

The translation pipeline should distinguish between:

```text
Stable source text
+
Unstable/partial source text
```

Conceptually:

```text
Source Segment
│
├── Stable text
│
└── Current partial text
```

Translation can then operate on suitable units rather than blindly translating every STT event.

Possible strategies include:

### Strategy A: Translate partial text

Useful when the translation model handles incomplete text well.

### Strategy B: Translate stable phrases

Wait for enough context to produce a more meaningful translation.

### Strategy C: Translate finalized segments

More stable but increases latency.

### Strategy D: Hybrid

Translate stable portions immediately while keeping the current unstable portion temporary.

The implementation should benchmark these strategies.

---

# 14. Cascaded TTS

The TTS stage receives translated text.

TTS should preferably process finalized or sufficiently stable translation segments.

Sending every partial translation directly to TTS can produce:

```text
Hello
Hello how
Hello how are
Hello how are you
```

which would result in repeated audio.

Therefore, TTS should generally operate on:

```text
Stable/final translation segments
```

or use a streaming TTS model specifically designed for incremental synthesis.

---

# 15. Cascaded Architecture Advantages

Advantages:

1. Independent components.
2. Easier debugging.
3. Easier model replacement.
4. Independent STT evaluation.
5. Independent translation evaluation.
6. Independent TTS evaluation.
7. Easier support for different language combinations.
8. Components can potentially run on separate hardware.

---

# 16. Cascaded Architecture Limitations

Potential limitations:

1. Latency accumulates across multiple models.
2. STT errors can propagate into translation.
3. Translation of partial text is difficult.
4. TTS can introduce additional latency.
5. Multiple model runtimes may require significant resources.
6. Synchronization between stages is complex.
7. Partial updates may be unstable.

---

# 17. Approach B: Unified/Direct Speech Translation

## 17.1 Overview

The unified architecture uses a speech translation model or model pipeline designed specifically for direct speech translation.

Conceptually:

```text
Audio
   ↓
Unified Speech Translation Model
   ↓
Translated Text
   ↓
Optional TTS
   ↓
Translated Audio
```

If the model itself produces speech output:

```text
Audio
   ↓
Speech-to-Speech Translation Model
   ↓
Translated Speech
```

---

# 18. Unified Model Interface

The application should expose a normalized interface regardless of the underlying model.

Conceptually:

```text
UnifiedTranslationProvider

start_session()
push_audio()
receive_events()
end_session()
```

The provider may internally handle:

* Audio buffering.
* Speech recognition.
* Translation.
* Alignment.
* Partial results.
* Final results.
* Audio generation.

These details must remain hidden from the rest of the application.

---

# 19. Unified Streaming Events

A unified model may produce events such as:

```text
partial translation
final translation
translated audio
segment boundary
```

The provider adapter must normalize these events into the application's common event format.

Example:

```json
{
  "type": "translation",
  "segment_id": "1",
  "status": "partial",
  "text": "नमस्ते"
}
```

The frontend should not need to know whether this event came from:

```text
STT + Translation
```

or:

```text
Unified Speech Translation
```

---

# 20. Unified Architecture Advantages

Potential advantages:

1. Potentially lower end-to-end latency.
2. Better handling of simultaneous translation.
3. Better access to speech context.
4. Fewer application-level pipeline boundaries.
5. Potentially fewer intermediate representations.
6. Potentially more natural speech translation.

---

# 21. Unified Architecture Limitations

Potential limitations:

1. Large model requirements.
2. GPU requirements.
3. Model licensing restrictions.
4. Limited language coverage.
5. More difficult debugging.
6. Less flexibility.
7. Model-specific integration complexity.
8. Potentially difficult deployment.
9. Model availability may change.
10. Some models may not provide usable streaming APIs.

---

# 22. Common Architecture for Both Approaches

The most important architectural decision is that both approaches should expose the same application-level contract.

```text
                         ┌─────────────────────┐
                         │    React Frontend   │
                         └──────────┬──────────┘
                                    │
                                    │ WebSocket
                                    ▼
                         ┌─────────────────────┐
                         │   WebSocket API     │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Translation Session │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Pipeline Interface  │
                         └──────────┬──────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     │                             │
                     ▼                             ▼
             ┌───────────────┐            ┌────────────────┐
             │   Cascaded    │            │    Unified     │
             │   Pipeline    │            │    Pipeline    │
             └───────┬───────┘            └───────┬────────┘
                     │                             │
                     ▼                             ▼
              STT → MT → TTS             Speech Translation
                     │                             │
                     └──────────────┬──────────────┘
                                    ▼
                           Normalized Events
                                    │
                                    ▼
                              WebSocket API
```

This allows the model strategy to be changed without changing the frontend.

---

# 23. Provider Abstraction

The provider layer should isolate third-party or local model implementations.

Recommended conceptual structure:

```text
providers/
│
├── base/
│   ├── stt.py
│   ├── translation.py
│   ├── tts.py
│   └── speech_translation.py
│
├── stt/
│   └── ...
│
├── translation/
│   └── ...
│
├── tts/
│   └── ...
│
└── speech_translation/
    └── ...
```

The exact structure can remain simpler until multiple implementations exist.

Do not create dozens of empty abstraction files merely for the sake of architecture.

Introduce additional layers when they provide a concrete benefit.

---

# 24. Model Adapter

A model adapter translates the application's common interface into the interface required by a specific model.

Example:

```text
Application
     |
     v
STTProvider
     |
     v
Specific STT Adapter
     |
     v
STT Model
```

The adapter may handle:

* Model-specific input format.
* Model-specific output format.
* Streaming protocol.
* Model initialization.
* Device selection.
* Model errors.
* Event normalization.

The rest of the application should not depend on these details.

---

# 25. Model Selection

Model selection should not be hardcoded into business logic.

Configuration should determine the active processing approach.

Conceptually:

```text
PROCESSING_MODE=cascaded
```

or:

```text
PROCESSING_MODE=unified
```

For cascaded:

```text
STT_MODEL=...
TRANSLATION_MODEL=...
TTS_MODEL=...
```

For unified:

```text
SPEECH_TRANSLATION_MODEL=...
```

The exact configuration mechanism may change during implementation.

---

# 26. Model Runtime

The model runtime is responsible for executing models.

Depending on the selected implementation, models may run:

* Locally on CPU.
* Locally on GPU.
* Through a local model server.
* Through a self-hosted inference service.
* Through an external provider if explicitly permitted.

The application architecture should not assume that inference happens inside the FastAPI process forever.

---

# 27. Model Lifecycle

Large models should not normally be loaded for every WebSocket connection.

Preferred lifecycle:

```text
Application Startup
       ↓
Load Model
       ↓
Model Ready
       ↓
Multiple Sessions
       ↓
Application Shutdown
       ↓
Release Model
```

Session-specific state should remain separate from shared model state.

---

# 28. GPU Support

The architecture should support GPU inference where required.

The application should not hardcode GPU-specific logic into the API layer.

Conceptually:

```text
FastAPI
   |
   v
Provider
   |
   v
Model Runtime
   |
   +-- CPU
   |
   +-- CUDA GPU
```

Hardware configuration should be isolated from business logic.

---

# 29. Event Normalization

Different providers may produce different event structures.

For example:

Provider A:

```json
{
  "partial_text": "Hello"
}
```

Provider B:

```json
{
  "event": "interim_result",
  "value": "Hello"
}
```

The backend should normalize both into a common application event.

Example:

```json
{
  "type": "transcript",
  "segment_id": "1",
  "status": "partial",
  "text": "Hello"
}
```

This is essential for keeping the frontend provider-independent.

---

# 30. Common Event Model

The application should define a normalized event model.

Possible event types:

```text
session_started
session_ready
transcript
translation
audio
segment_started
segment_updated
segment_final
error
session_ended
```

Not all events are required initially.

The protocol should evolve based on actual model behavior.

---

# 31. Transcript Event

Example:

```json
{
  "type": "transcript",
  "segment_id": "segment-001",
  "status": "partial",
  "text": "Hello how"
}
```

Final:

```json
{
  "type": "transcript",
  "segment_id": "segment-001",
  "status": "final",
  "text": "Hello, how are you?"
}
```

---

# 32. Translation Event

Example:

```json
{
  "type": "translation",
  "segment_id": "segment-001",
  "status": "partial",
  "source_text": "Hello how",
  "translated_text": "नमस्ते कैसे"
}
```

Final:

```json
{
  "type": "translation",
  "segment_id": "segment-001",
  "status": "final",
  "source_text": "Hello, how are you?",
  "translated_text": "नमस्ते, आप कैसे हैं?"
}
```

---

# 33. Audio Event

Translated audio can be returned as binary WebSocket messages.

Control metadata may identify the audio segment.

Conceptually:

```text
JSON:
{
    "type": "audio_start",
    "segment_id": "segment-001"
}

Binary:
<audio bytes>

JSON:
{
    "type": "audio_end",
    "segment_id": "segment-001"
}
```

The exact framing should be finalized after selecting the TTS/model implementation.

---

# 34. Frontend State Model

The frontend should conceptually maintain:

```text
Connection State
Language Configuration
Session State
Transcript Segments
Translation Segments
Audio Playback State
Error State
```

Transcript state should support:

```text
Final segments
+
Current partial segment
```

Translation state should follow the same pattern.

---

# 35. Partial and Final State Handling

The frontend should not treat every incoming event as a new message.

Example:

```text
segment-001 partial
    ↓
"Hello"

segment-001 partial
    ↓
"Hello how"

segment-001 partial
    ↓
"Hello how are"

segment-001 final
    ↓
"Hello, how are you?"
```

The UI should result in one finalized segment:

```text
Hello, how are you?
```

rather than four separate segments.

---

# 36. Session Lifecycle

The session lifecycle is:

```text
                 Client
                   |
                   | Connect
                   ▼
             WebSocket Open
                   |
                   ▼
           Session Initialization
                   |
                   ▼
              Session Ready
                   |
                   ▼
             Audio Streaming
                   |
                   ▼
             AI Processing
                   |
                   ▼
            Result Streaming
                   |
                   ▼
              Audio Stop
                   |
                   ▼
           Session Finalization
                   |
                   ▼
            Resource Cleanup
                   |
                   ▼
           WebSocket Closed
```

---

# 37. Session Isolation

Each session must have independent:

* Audio buffers.
* Pipeline state.
* Segment state.
* Provider session state.
* Language configuration.

No session should be able to access another session's temporary state.

---

# 38. Concurrency

FastAPI's asynchronous architecture should be used for:

* WebSocket communication.
* Network I/O.
* Provider communication.
* Audio streaming.

CPU/GPU-heavy inference must be handled appropriately so that model execution does not unnecessarily block unrelated WebSocket connections.

The exact inference strategy depends on the selected model runtime.

---

# 39. Backend Directory Architecture

The recommended initial backend structure is:

```text
backend/
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── health.py
│   │   └── websocket.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── session_service.py
│   │   ├── audio_service.py
│   │   └── translation_service.py
│   │
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base/
│   │   ├── stt/
│   │   ├── translation/
│   │   ├── tts/
│   │   └── speech_translation/
│   │
│   ├── models/
│   │   └── ...
│   │
│   ├── schemas/
│   │   ├── websocket.py
│   │   ├── transcript.py
│   │   └── translation.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   └── logging.py
│   │
│   └── utils/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── requirements.txt
├── .env.example
└── README.md
```

This structure can be simplified if some directories do not yet contain multiple implementations.

---

# 40. Frontend Directory Architecture

Recommended initial structure:

```text
frontend/
│
├── public/
│
├── src/
│   ├── main.jsx
│   ├── App.jsx
│   │
│   ├── components/
│   │   ├── AudioControls.jsx
│   │   ├── LanguageSelector.jsx
│   │   ├── ConnectionStatus.jsx
│   │   ├── Transcript.jsx
│   │   └── Translation.jsx
│   │
│   ├── hooks/
│   │   ├── useWebSocket.js
│   │   └── useAudioRecorder.js
│   │
│   ├── services/
│   │   ├── websocket.js
│   │   └── audio.js
│   │
│   ├── config/
│   │   └── environment.js
│   │
│   └── utils/
│
├── package.json
└── vite.config.js
```

The actual structure should evolve based on application complexity.

---

# 41. Dependency Direction

Dependencies should flow toward lower-level implementation details.

Preferred:

```text
API
 ↓
Services
 ↓
Provider Interfaces
 ↓
Provider Implementations
 ↓
Model Runtime
```

Not:

```text
Provider
 ↓
WebSocket API
 ↓
UI
```

The provider layer must not know about React or WebSocket-specific details.

---

# 42. API Layer Rules

The API layer should:

* Validate input.
* Establish connections.
* Invoke services.
* Send normalized events.
* Handle connection lifecycle.

The API layer should not:

* Perform model inference directly.
* Implement translation algorithms.
* Manage complex transcript stabilization.
* Contain provider-specific logic.

---

# 43. Service Layer Rules

The service layer should:

* Coordinate application behavior.
* Manage session state.
* Coordinate pipeline components.
* Handle business rules.
* Normalize processing flow.

The service layer should not contain provider-specific communication details.

---

# 44. Provider Layer Rules

The provider layer should:

* Communicate with the selected AI/model runtime.
* Convert model-specific inputs.
* Convert model-specific outputs.
* Handle model-specific errors.
* Normalize model events.

Providers must not contain frontend logic.

---

# 45. Configuration Architecture

Configuration should be centralized.

Conceptually:

```text
Environment
     ↓
Configuration
     ↓
Application
     ↓
Provider Factory
     ↓
Selected Provider
```

Example:

```text
PROCESSING_MODE=cascaded
STT_PROVIDER=...
TRANSLATION_PROVIDER=...
TTS_PROVIDER=...
```

or:

```text
PROCESSING_MODE=unified
SPEECH_TRANSLATION_PROVIDER=...
```

---

# 46. Provider Factory

A provider factory may be introduced once multiple providers exist.

Conceptually:

```text
Configuration
      ↓
Provider Factory
      ↓
Selected Provider
```

For example:

```python
pipeline = PipelineFactory.create(
    mode=settings.processing_mode
)
```

The factory should not contain model-processing logic.

It should only select and construct the appropriate implementation.

---

# 47. Error Architecture

Errors should be handled at the appropriate layer.

```text
Model Error
    ↓
Provider
    ↓
Normalized Provider Error
    ↓
Service
    ↓
Application Event
    ↓
WebSocket
    ↓
Frontend
```

The frontend should receive safe, user-understandable errors.

Internal implementation details should remain server-side.

---

# 48. Logging Architecture

Logging should exist primarily at:

```text
API
Services
Providers
```

Useful fields may include:

```text
timestamp
level
session_id
component
event
duration
error_code
```

Raw audio should not be logged.

Sensitive provider credentials must never be logged.

---

# 49. Testing Architecture

Testing should occur at multiple levels.

## Unit Tests

Test:

* Services.
* Event normalization.
* Transcript state management.
* Translation state management.
* Provider adapters.

## Integration Tests

Test:

```text
WebSocket
    ↓
Session
    ↓
Pipeline
    ↓
Mock Provider
    ↓
Events
```

## Model Tests

Actual model behavior should be tested separately because model execution can be:

* Expensive.
* Hardware-dependent.
* Non-deterministic.
* Slow.

Mock providers should therefore be used for most automated application tests.

---

# 50. Mock Provider Architecture

A mock provider should be available for development and testing.

Example:

```text
MockSTTProvider
MockTranslationProvider
MockTTSProvider
```

This allows testing the complete application without loading large models.

Example:

```text
Browser
   ↓
WebSocket
   ↓
FastAPI
   ↓
Session
   ↓
Mock STT
   ↓
Mock Translation
   ↓
Mock TTS
   ↓
WebSocket
   ↓
Browser
```

This should be implemented before relying heavily on large AI models for integration testing.

---

# 51. Real Model Integration

Once the application pipeline works with mocks:

```text
Mock Provider
      ↓
Real Provider
```

The rest of the application should remain unchanged.

This validates whether the provider abstraction is actually effective.

---

# 52. Architecture Selection Strategy

The project should not decide the final AI architecture purely theoretically.

Both approaches should be prototyped and measured.

Recommended evaluation process:

```text
Implement common interfaces
          ↓
Implement cascaded prototype
          ↓
Measure
          ↓
Implement unified prototype
          ↓
Measure
          ↓
Compare
          ↓
Select production approach
```

---

# 53. Evaluation Criteria

Each approach should be evaluated against:

| Criterion                      | Importance  |
| ------------------------------ | ----------- |
| End-to-end latency             | Critical    |
| Partial result latency         | Critical    |
| Translation quality            | Critical    |
| STT accuracy                   | High        |
| Final translation accuracy     | High        |
| Language coverage              | High        |
| Streaming support              | Critical    |
| Hardware requirements          | High        |
| Memory usage                   | High        |
| GPU requirements               | High        |
| Model size                     | Medium/High |
| Licensing                      | Critical    |
| Local/self-hosted availability | High        |
| Implementation complexity      | Medium      |
| Stability                      | Critical    |
| TTS quality                    | High        |

---

# 54. Architecture Decision Rule

The unified approach should be selected if it demonstrates a meaningful advantage in real-time translation quality or latency while remaining practical to run and legally usable.

The cascaded approach should be selected if it provides:

* Better language coverage.
* Better overall quality.
* More practical hardware requirements.
* Better licensing.
* Easier deployment.
* More controllable components.
* Sufficient real-time performance.

The architecture should be selected based on actual benchmark results rather than model popularity.

---

# 55. Performance Benchmarking

The system should eventually record:

```text
T0 = microphone capture

T1 = audio received by backend

T2 = STT partial result

T3 = translation partial result

T4 = TTS output available

T5 = audio played
```

Then calculate:

```text
Audio transport latency
= T1 - T0

STT latency
= T2 - T1

Translation latency
= T3 - T2

TTS latency
= T4 - T3

Playback latency
= T5 - T4

End-to-end latency
= T5 - T0
```

For unified translation:

```text
Audio transport latency
= T1 - T0

Translation latency
= T2 - T1

Playback latency
= T3 - T2

End-to-end latency
= T3 - T0
```

The exact instrumentation should be added after the initial pipeline is functional.

---

# 56. Resource Management

Model resources should be managed separately from session resources.

## Shared Resources

Potentially shared:

```text
Loaded Model
Model Runtime
GPU
Tokenizer
```

## Session Resources

Per connection:

```text
Audio Buffer
Session State
Segment State
Provider Session
```

This separation prevents unnecessary model loading and reduces memory consumption.

---

# 57. Cleanup Requirements

When a session ends:

```text
Stop audio capture
       ↓
Stop receiving audio
       ↓
Flush pending processing where appropriate
       ↓
Finalize results
       ↓
Close provider session
       ↓
Release session state
       ↓
Close WebSocket
```

Unexpected disconnects must trigger equivalent cleanup.

---

# 58. Security Architecture

Phase 1 has no authentication, but the architecture should still separate:

```text
Transport
Processing
Configuration
Secrets
```

Provider credentials must remain exclusively on the backend.

The browser must never receive:

* Provider API keys.
* Model credentials.
* Internal infrastructure credentials.

---

# 59. Future Authentication Integration

Authentication should eventually be inserted at the session boundary.

Future:

```text
Client
   ↓
Authentication
   ↓
WebSocket Session
   ↓
Translation Pipeline
```

The translation pipeline itself should remain independent from authentication.

This allows:

```text
Authenticated User
       ↓
Translation Session
       ↓
Pipeline
```

without modifying STT, translation, or TTS providers.

---

# 60. Future Database Integration

A database should be introduced outside the real-time inference pipeline.

Future architecture:

```text
                    FastAPI
                       |
          ┌────────────┴────────────┐
          │                         │
          ▼                         ▼
     REST/API Layer          WebSocket Layer
          │                         │
          ▼                         ▼
      Database                Translation
                                  Pipeline
```

The database should not become a dependency for every audio chunk.

Real-time audio processing should not perform a database operation for each chunk unless a future requirement explicitly justifies it.

---

# 61. Future Redis/Celery Integration

If introduced later:

```text
Real-Time WebSocket
        |
        +---- Translation Pipeline
        |
        +---- Optional Background Jobs
                    |
                    v
              Redis / Celery
```

Redis/Celery should be used for appropriate background work, not inserted between every WebSocket audio chunk and the AI model.

---

# 62. Deployment Architecture

Phase 1 local architecture:

```text
Browser
   |
   +---- localhost:5173
   |
   +---- localhost:8000
```

Potential production architecture:

```text
Internet
   |
   v
Reverse Proxy
   |
   +----------------------+
   |                      |
   v                      v
React Static App      FastAPI
                          |
                          v
                   Translation Pipeline
                          |
             +------------+------------+
             |            |            |
             v            v            v
            STT       Translation     TTS
```

The exact production infrastructure will be defined later.

---

# 63. Docker Considerations

Docker is not required to prove the initial functionality.

However, the architecture should remain compatible with containerization.

Potential future structure:

```text
docker-compose
    |
    +-- frontend
    |
    +-- backend
    |
    +-- model runtime
```

Large GPU model containers may require specialized runtime configuration.

Docker should be introduced when it provides practical value rather than adding complexity before the core pipeline works.

---

# 64. Development Phases

## Phase 1A: Repository Foundation

Implement:

* Repository.
* React application.
* FastAPI application.
* Documentation.
* AI agent instructions.
* Linting.
* Formatting.
* Testing foundation.

---

## Phase 1B: WebSocket Verification

Implement:

```text
React
   ↓
WebSocket
   ↓
FastAPI
   ↓
WebSocket
   ↓
React
```

No AI models yet.

Goal:

Verify reliable bidirectional real-time communication.

---

## Phase 1C: Audio Streaming

Implement:

```text
Microphone
   ↓
React
   ↓
Audio chunks
   ↓
WebSocket
   ↓
FastAPI
```

Goal:

Verify that real microphone audio reaches the backend correctly.

---

## Phase 1D: Streaming STT

Implement:

```text
Audio
   ↓
STT
   ↓
Partial Transcript
   ↓
WebSocket
   ↓
React
```

Goal:

Display continuously changing transcription.

---

## Phase 1E: Transcript Stabilization

Implement:

```text
Partial
   ↓
Updated Partial
   ↓
Final
```

Goal:

Prevent duplicate transcript segments.

---

## Phase 1F: Cascaded Translation

Implement:

```text
STT
 ↓
Translation
 ↓
Translated Text
```

Goal:

Measure real-time translation latency and quality.

---

## Phase 1G: TTS

Implement:

```text
Translation
 ↓
TTS
 ↓
Translated Audio
 ↓
Browser
```

Goal:

Provide translated speech.

---

## Phase 1H: Unified Model Prototype

Implement a second pipeline:

```text
Audio
 ↓
Unified Speech Translation
 ↓
Translation
```

Goal:

Compare against the cascaded implementation.

---

## Phase 1I: Benchmark

Measure:

* Latency.
* Accuracy.
* Resource consumption.
* Stability.
* Language coverage.
* Hardware requirements.

---

## Phase 1J: Select Production Pipeline

Choose:

```text
Cascaded
```

or:

```text
Unified
```

based on measured results.

---

# 65. Recommended Initial Implementation Order

The implementation should follow this order:

```text
1. Repository
      ↓
2. FastAPI foundation
      ↓
3. React foundation
      ↓
4. WebSocket
      ↓
5. Audio capture
      ↓
6. Audio streaming
      ↓
7. Mock STT
      ↓
8. Real STT
      ↓
9. Transcript stabilization
      ↓
10. Mock Translation
      ↓
11. Real Translation
      ↓
12. Mock TTS
      ↓
13. Real TTS
      ↓
14. Unified model experiment
      ↓
15. Benchmark
      ↓
16. Architecture selection
```

This order minimizes debugging complexity.

---

# 66. Why Mock Providers Should Be Used First

Without mocks, a failure could originate from:

```text
Browser
Audio API
WebSocket
FastAPI
Audio format
STT
Translation
TTS
GPU
Model runtime
```

With mocks:

```text
Browser
   ↓
WebSocket
   ↓
FastAPI
   ↓
Mock Provider
   ↓
WebSocket
   ↓
Browser
```

The application architecture can be validated before introducing model complexity.

---

# 67. Architecture Risks

## Risk 1: Excessive Latency

Multiple cascaded models may create unacceptable latency.

Mitigation:

* Streaming.
* Smaller chunks.
* Parallel processing where possible.
* GPU inference.
* Stable-segment translation.
* Benchmarking.

---

## Risk 2: Partial Translation Instability

Partial STT results may constantly change.

Mitigation:

* Segment IDs.
* Partial/final status.
* Stable/unstable state.
* Translation buffering.

---

## Risk 3: Model Resource Requirements

Large models may require significant GPU memory.

Mitigation:

* Benchmark model sizes.
* Support configurable model runtimes.
* Separate inference from API if necessary.
* Evaluate smaller models.

---

## Risk 4: Provider Lock-In

A provider-specific implementation may spread throughout the application.

Mitigation:

* Provider interfaces.
* Adapters.
* Normalized events.
* Configuration-based provider selection.

---

## Risk 5: Licensing

Some models may have licenses that restrict commercial or production usage.

Mitigation:

* Record model licenses before adoption.
* Treat licensing as an architecture-selection criterion.
* Do not assume that a freely downloadable model is unrestricted for commercial use.

---

## Risk 6: Language Coverage

A model may perform well for English but poorly for other languages.

Mitigation:

* Benchmark target language pairs.
* Maintain provider abstraction.
* Support different model combinations where practical.

---

## Risk 7: WebSocket Instability

Long-running connections may disconnect.

Mitigation:

* Connection state management.
* Cleanup.
* Heartbeats where necessary.
* Reconnection strategy.
* Session lifecycle handling.

---

## Risk 8: Audio Format Incompatibility

The browser format may not match model requirements.

Mitigation:

* Define an explicit audio contract.
* Add a dedicated audio processing layer.
* Convert audio server-side when required.

---

# 68. Architecture Decision Record Requirements

When a significant architectural decision is made, record it separately.

Examples:

```text
ADR-001: WebSocket for real-time communication
ADR-002: No database in Phase 1
ADR-003: Provider abstraction
ADR-004: Cascaded vs unified translation
ADR-005: Selected STT model
ADR-006: Selected translation model
ADR-007: Selected TTS model
```

This prevents future AI agents or developers from accidentally reversing established decisions.

---

# 69. AI-Assisted Development Requirements

Because the project will be developed using AI coding tools, the architecture documentation is part of the development system.

AI coding agents must:

1. Read `AGENTS.md`.
2. Read the relevant architecture documentation.
3. Follow established interfaces.
4. Avoid introducing infrastructure without a requirement.
5. Avoid changing architecture without documenting the change.
6. Avoid modifying unrelated code.
7. Run relevant tests after implementation.
8. Preserve frontend/backend separation.
9. Preserve provider abstraction.
10. Prefer incremental implementation.

The AI agents should not independently introduce:

```text
Database
Redis
Celery
Authentication
Additional frameworks
```

unless explicitly required by the current development phase.

---

# 70. Source of Truth Hierarchy

When making implementation decisions, the following hierarchy should be followed:

```text
Business Requirements
        ↓
Architecture Requirements
        ↓
Architecture Design
        ↓
WebSocket/API Contracts
        ↓
Implementation
        ↓
Tests
```

If implementation conflicts with the documented architecture, the discrepancy should be identified before making the change.

---

# 71. Definition of Architectural Completion

The Phase 1 architecture is considered successfully implemented when:

1. React and FastAPI operate as separate applications.
2. WebSocket communication is functional.
3. Microphone audio can be streamed continuously.
4. Audio can be processed in real time.
5. STT can produce partial/final results.
6. Translation can produce incremental/final results.
7. TTS can produce translated audio where supported.
8. The frontend is independent of the underlying AI model.
9. Provider implementations are isolated.
10. The application can support both cascaded and unified processing strategies.
11. Model implementations can be replaced without changing the frontend protocol.
12. Session state is isolated.
13. Model state is separated from session state.
14. No database is required.
15. Authentication is not required.
16. Redis and Celery are not required for the real-time pipeline.
17. The system can be benchmarked for latency and quality.
18. The final AI architecture can be selected based on measurable results.

---

# 72. Final Reference Architecture

The intended architecture is:

```text
                         ┌───────────────────────────┐
                         │       React Frontend      │
                         │                           │
                         │ Language Selection        │
                         │ Audio Capture             │
                         │ Transcript                │
                         │ Translation               │
                         │ Audio Playback            │
                         └─────────────┬─────────────┘
                                       │
                                       │ WebSocket
                                       ▼
                         ┌───────────────────────────┐
                         │      FastAPI Gateway      │
                         │                           │
                         │ WebSocket Endpoint        │
                         │ Connection Lifecycle      │
                         └─────────────┬─────────────┘
                                       │
                                       ▼
                         ┌───────────────────────────┐
                         │    Translation Session    │
                         │                           │
                         │ Session State             │
                         │ Language Configuration    │
                         │ Segment State             │
                         └─────────────┬─────────────┘
                                       │
                                       ▼
                         ┌───────────────────────────┐
                         │    Pipeline Interface     │
                         └─────────────┬─────────────┘
                                       │
                       ┌───────────────┴────────────────┐
                       │                                │
                       ▼                                ▼
            ┌─────────────────────┐          ┌─────────────────────┐
            │ Cascaded Pipeline   │          │ Unified Pipeline    │
            │                     │          │                     │
            │ Audio               │          │ Audio               │
            │   ↓                 │          │   ↓                 │
            │ STT                 │          │ Unified Speech      │
            │   ↓                 │          │ Translation Model   │
            │ Translation         │          │   ↓                 │
            │   ↓                 │          │ Translation Result  │
            │ TTS                 │          │   ↓                 │
            │   ↓                 │          │ Optional TTS         │
            │ Audio               │          │                     │
            └──────────┬──────────┘          └──────────┬──────────┘
                       │                                │
                       └───────────────┬────────────────┘
                                       │
                                       ▼
                         ┌───────────────────────────┐
                         │    Event Normalization    │
                         │                           │
                         │ Transcript Events         │
                         │ Translation Events        │
                         │ Audio Events              │
                         │ Error Events              │
                         └─────────────┬─────────────┘
                                       │
                                       │ WebSocket
                                       ▼
                         ┌───────────────────────────┐
                         │       React Frontend      │
                         │                           │
                         │ Partial Transcript       │
                         │ Final Transcript         │
                         │ Partial Translation      │
                         │ Final Translation        │
                         │ Translated Audio         │
                         └───────────────────────────┘
```

The central architectural decision is therefore:

> **The application architecture should be independent of the AI processing strategy.**

The frontend communicates with one stable real-time protocol. The FastAPI session layer communicates with one pipeline interface. Behind that interface, the system can run either a cascaded STT + translation + TTS architecture or a unified/direct speech translation architecture.

The final choice should be made after implementing and benchmarking both approaches against latency, quality, language coverage, hardware requirements, licensing, and real-time stability.
