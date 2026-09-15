# Architecture

## Phase 1 Scope

Phase 1 implements only the core real-time audio translation system.

Included:

- React frontend
- FastAPI backend
- WebSocket communication
- microphone capture
- audio streaming
- speech-to-text
- translation
- text-to-speech
- translated audio playback
- transcript display
- translation display

Excluded:

- authentication
- registration
- database
- user profiles
- authorization
- billing
- persistent user sessions

## System

Browser
    |
    | WebSocket
    v
FastAPI
    |
    v
Audio Processing
    |
    v
Speech-to-Text
    |
    v
Translation
    |
    v
Text-to-Speech
    |
    v
FastAPI
    |
    | WebSocket
    v
Browser