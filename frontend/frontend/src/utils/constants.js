/**
 * Shared constants — languages, connection states, segment status.
 * Used across components/hooks; keep JS/JSX only.
 */

export const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "Hindi" },
  { code: "es", label: "Spanish" },
  { code: "fr", label: "French" },
  { code: "de", label: "German" },
];

export const CONNECTION_STATES = {
  IDLE: "idle",
  CONNECTING: "connecting",
  READY: "ready",
  LISTENING: "listening",
  PROCESSING: "processing",
  ERROR: "error",
  DISCONNECTED: "disconnected",
};

export const SESSION_STATES = {
  IDLE: "idle",
  ACTIVE: "active",
  ENDING: "ending",
  ENDED: "ended",
};

export const SEGMENT_STATUS = {
  PARTIAL: "partial",
  FINAL: "final",
};

export const ERROR_CODES = {
  INVALID_MESSAGE: "INVALID_MESSAGE",
  INVALID_SESSION_CONFIG: "INVALID_SESSION_CONFIG",
  UNSUPPORTED_LANGUAGE: "UNSUPPORTED_LANGUAGE",
  UNSUPPORTED_PIPELINE: "UNSUPPORTED_PIPELINE",
  UNSUPPORTED_AUDIO_FORMAT: "UNSUPPORTED_AUDIO_FORMAT",
  INVALID_AUDIO_DATA: "INVALID_AUDIO_DATA",
  MODEL_NOT_READY: "MODEL_NOT_READY",
  MODEL_ERROR: "MODEL_ERROR",
  SESSION_ERROR: "SESSION_ERROR",
  SESSION_TIMEOUT: "SESSION_TIMEOUT",
  RATE_LIMITED: "RATE_LIMITED",
  INTERNAL_ERROR: "INTERNAL_ERROR",
};
