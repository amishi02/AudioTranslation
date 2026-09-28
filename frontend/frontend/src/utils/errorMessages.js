/**
 * Error taxonomy — P10-ERR-002 frontend mapping.
 * Mirrors backend/app/schemas/errors.py ERROR_MESSAGES + ERROR_RETRYABLE.
 */

export const ERROR_MESSAGES = {
  INVALID_MESSAGE: "Invalid message format.",
  INVALID_SESSION_CONFIG: "Invalid session configuration. Check language selection.",
  UNSUPPORTED_LANGUAGE: "Selected language pair is not supported.",
  UNSUPPORTED_PIPELINE: "Pipeline not available.",
  UNSUPPORTED_AUDIO_FORMAT: "Unsupported audio format.",
  INVALID_AUDIO_DATA: "Invalid audio data.",
  MODEL_NOT_READY: "Model is still loading. Please try again.",
  MODEL_ERROR: "Processing error. Please try again.",
  SESSION_ERROR: "Session error. Please start a new session.",
  SESSION_TIMEOUT: "Session timed out due to inactivity. Tap Try Again to restart.",
  RATE_LIMITED: "Too many requests. Please slow down.",
  INTERNAL_ERROR: "Internal server error. Please try again.",
};

export const RETRYABLE_CODES = new Set(["MODEL_NOT_READY", "SESSION_TIMEOUT", "RATE_LIMITED"]);

export function getErrorMessage(code, fallback) {
  if (!code) return fallback || "An error occurred.";
  return ERROR_MESSAGES[code] || fallback || `Error: ${code}`;
}

export function isRetryable(code) {
  return RETRYABLE_CODES.has(code);
}
