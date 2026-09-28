/**
 * useWebSocket — Phase 4 real hook with session lifecycle.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { createWebSocketClient } from "../services/websocket.js";
import { CONNECTION_STATES } from "../utils/constants.js";
import { getWsUrl } from "../config/environment.js";

export function useWebSocket({ onSessionReady, onSessionEnded, onErrorEvent, onBinary, onTranscript, onTranslation, onAudioStart, onAudioEnd } = {}) {
  const [status, setStatus] = useState(CONNECTION_STATES.IDLE);
  const [sessionId, setSessionId] = useState(null);
  const [error, setError] = useState(null);
  const clientRef = useRef(null);
  const reconnectRef = useRef({ attempts: 0, timer: null });

  const ensureClient = useCallback(() => {
    if (clientRef.current) return clientRef.current;
    const wsUrl = getWsUrl();
    const client = createWebSocketClient(wsUrl, {
      onEvent: (event) => {
        // T5 capture: frontend decode done for perf (P10-PERF-001) — log when perf field present
        if (event.perf) {
          console.debug("[perf] event", event.type, event.perf);
        }
        if (event.type === "session.ready") {
          reconnectRef.current.attempts = 0;
          setSessionId(event.session_id);
          setStatus(CONNECTION_STATES.READY);
          if (onSessionReady) onSessionReady(event);
        } else if (event.type === "session.ended") {
          setStatus(CONNECTION_STATES.IDLE);
          setSessionId(null);
          if (onSessionEnded) onSessionEnded(event);
        } else if (event.type === "error") {
          const msg = event.message || event.code || "Unknown error";
          setError(msg);
          // P10-ERR-005: retryable vs fatal classification
          const retryable = event.retryable === true || ["SESSION_TIMEOUT", "RATE_LIMITED", "MODEL_NOT_READY"].includes(event.code);
          if (event.code === "RATE_LIMITED") {
            // keep active, non-fatal
          } else if (event.code === "SESSION_TIMEOUT") {
            setStatus(CONNECTION_STATES.IDLE);
          } else if (event.code === "SESSION_ERROR" || event.code === "INVALID_SESSION_CONFIG") {
            setStatus(CONNECTION_STATES.IDLE);
          } else if (!retryable && ["UNSUPPORTED_LANGUAGE", "UNSUPPORTED_PIPELINE", "INTERNAL_ERROR"].includes(event.code)) {
            setStatus(CONNECTION_STATES.ERROR);
          }
          if (onErrorEvent) onErrorEvent({ ...event, retryable });
        } else if (event.type === "transcript") {
          // P10-FE-001 edge: ignore empty transcript (no speech -> remain listening without emitting)
          if (!event.text || !event.text.trim()) return;
          // Very short speech (single word) still valid -> emit as final coherence handled by backend
          if (onTranscript) onTranscript(event);
          setStatus(CONNECTION_STATES.LISTENING);
        } else if (event.type === "translation") {
          if (!event.translated_text && !event.source_text) return;
          if (onTranslation) onTranslation(event);
          setStatus(CONNECTION_STATES.LISTENING);
        } else if (event.type === "audio.output.start") {
          if (onAudioStart) onAudioStart(event);
        } else if (event.type === "audio.output.end") {
          if (onAudioEnd) onAudioEnd(event);
        } else if (event.type === "pong") {
          // heartbeat — ignore
        } else {
          // ignore unknown
        }
      },
      onError: (err) => {
        setError(err.message);
        setStatus(CONNECTION_STATES.ERROR);
      },
      onBinary: (buf) => {
        if (onBinary) onBinary(buf);
      },
      onClose: (ev) => {
        // P10-FE-002: reconnect helper — if close was unexpected while active, surface error
        if (ev && ev.code !== 1000) {
          setError("Connection lost. Tap Try Again.");
        }
        setStatus(CONNECTION_STATES.DISCONNECTED);
      },
    });
    clientRef.current = client;
    return client;
  }, [onSessionReady, onSessionEnded, onErrorEvent, onBinary, onTranscript, onTranslation, onAudioStart, onAudioEnd]);

  const startSession = useCallback(
    ({ sourceLanguage, targetLanguage }) => {
      setError(null);
      setStatus(CONNECTION_STATES.CONNECTING);
      const client = ensureClient();
      // Ensure connection
      const ws = client.connect();
      const sendStart = () => {
        client.sendJson({
          type: "start",
          source_language: sourceLanguage,
          target_language: targetLanguage,
        });
        setStatus(CONNECTION_STATES.CONNECTING);
      };
      if (ws && ws.readyState === WebSocket.OPEN) {
        sendStart();
      } else if (ws) {
        ws.addEventListener(
          "open",
          () => {
            sendStart();
          },
          { once: true }
        );
      }
    },
    [ensureClient]
  );

  const stopSession = useCallback(() => {
    const client = clientRef.current;
    if (client) {
      client.sendJson({ type: "stop" });
      // Status will be set to IDLE on session.ended, but also set here for immediate UI
      setStatus(CONNECTION_STATES.IDLE);
    }
  }, []);

  const sendAudio = useCallback((buffer) => {
    const client = clientRef.current;
    if (client) client.sendAudio(buffer);
  }, []);

  const disconnect = useCallback(() => {
    const client = clientRef.current;
    if (client) client.disconnect();
    setStatus(CONNECTION_STATES.DISCONNECTED);
    setSessionId(null);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (clientRef.current) clientRef.current.disconnect();
    };
  }, []);

  return {
    status,
    sessionId,
    error,
    setError,
    startSession,
    stopSession,
    sendAudio,
    disconnect,
    setStatus,
    setSessionId,
  };
}
