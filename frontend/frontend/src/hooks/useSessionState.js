/**
 * useSessionState — frontend session + segment state (no WS yet).
 * Holds sessionId, connection, segments, activeSegment, error.
 * Phase 3: pure state; Phases 7-8 will drive transcript/translation reducers.
 */
import { useCallback, useState } from "react";
import { CONNECTION_STATES } from "../utils/constants.js";

export function useSessionState() {
  const [sessionId, setSessionId] = useState(null);
  const [connection, setConnection] = useState(CONNECTION_STATES.IDLE);
  const [segments, setSegments] = useState([]); // final + active via {id, text, status}
  const [activeSegment, setActiveSegment] = useState(null);
  const [error, setError] = useState(null);

  const reset = useCallback(() => {
    setSessionId(null);
    setConnection(CONNECTION_STATES.IDLE);
    setSegments([]);
    setActiveSegment(null);
    setError(null);
  }, []);

  /**
   * Apply transcript event {segment_id, status, text} — partial replaces, final commits.
   * Used in Phase 3 tests and Phase 7-8 real flow.
   */
  const applyTranscriptEvent = useCallback((event) => {
    const { segment_id, status, text } = event;
    const id = segment_id;
    if (status === "partial") {
      setActiveSegment({ id, text, status });
      setSegments((prev) => {
        const exists = prev.find((s) => s.id === id);
        if (exists) return prev.map((s) => (s.id === id ? { id, text, status } : s));
        return [...prev, { id, text, status }];
      });
    } else if (status === "final") {
      setActiveSegment((cur) => (cur && cur.id === id ? null : cur));
      setSegments((prev) => {
        const exists = prev.find((s) => s.id === id);
        if (exists) return prev.map((s) => (s.id === id ? { id, text, status: "final" } : s));
        return [...prev, { id, text, status: "final" }];
      });
    }
  }, []);

  return {
    sessionId,
    setSessionId,
    connection,
    setConnection,
    segments,
    setSegments,
    activeSegment,
    setActiveSegment,
    error,
    setError,
    reset,
    applyTranscriptEvent,
  };
}
