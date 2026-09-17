/**
 * useWebSocket — Phase 4 real hook with session lifecycle.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { createWebSocketClient } from "../services/websocket.js";
import { CONNECTION_STATES } from "../utils/constants.js";
import { getWsUrl } from "../config/environment.js";

export function useWebSocket({ onSessionReady, onSessionEnded, onErrorEvent, onBinary, onTranscript, onTranslation } = {}) {
  const [status, setStatus] = useState(CONNECTION_STATES.IDLE);
  const [sessionId, setSessionId] = useState(null);
  const [error, setError] = useState(null);
  const clientRef = useRef(null);

  const ensureClient = useCallback(() => {
    if (clientRef.current) return clientRef.current;
    const wsUrl = getWsUrl();
    const client = createWebSocketClient(wsUrl, {
      onEvent: (event) => {
        if (event.type === "session.ready") {
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
          if (event.code === "RATE_LIMITED") {
            // keep active
          } else if (event.code === "SESSION_ERROR") {
            setStatus(CONNECTION_STATES.IDLE);
          }
          if (onErrorEvent) onErrorEvent(event);
        } else if (event.type === "transcript") {
          if (onTranscript) onTranscript(event);
          // Also set listening status when transcript flows
          setStatus(CONNECTION_STATES.LISTENING);
        } else if (event.type === "translation") {
          if (onTranslation) onTranslation(event);
          setStatus(CONNECTION_STATES.LISTENING);
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
    });
    clientRef.current = client;
    return client;
  }, [onSessionReady, onSessionEnded, onErrorEvent, onBinary, onTranscript, onTranslation]);

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
