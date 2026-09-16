/**
 * useWebSocket stub — Phase 3 state machine only, no real socket.
 * Real WS arrives in Phase 4 (services/websocket.js).
 */
import { useCallback, useState } from "react";
import { CONNECTION_STATES } from "../utils/constants.js";

export function useWebSocket() {
  const [status, setStatus] = useState(CONNECTION_STATES.IDLE);
  const [sessionId, setSessionId] = useState(null);
  const [error, setError] = useState(null);

  const startSession = useCallback(() => {
    setStatus(CONNECTION_STATES.CONNECTING);
    // stub: immediately move to ready/idle for Phase 3 shell
    setTimeout(() => setStatus(CONNECTION_STATES.READY), 0);
  }, []);

  const stopSession = useCallback(() => {
    setStatus(CONNECTION_STATES.IDLE);
    setSessionId(null);
  }, []);

  const sendAudio = useCallback(() => {}, []);

  return { status, sessionId, error, setError, startSession, stopSession, sendAudio, setStatus, setSessionId };
}
