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
  const [segments, setSegments] = useState([]); // transcript
  const [activeSegment, setActiveSegment] = useState(null);
  const [translationSegments, setTranslationSegments] = useState([]);
  const [translationActive, setTranslationActive] = useState(null);
  const [error, setError] = useState(null);

  const reset = useCallback(() => {
    setSessionId(null);
    setConnection(CONNECTION_STATES.IDLE);
    setSegments([]);
    setActiveSegment(null);
    setTranslationSegments([]);
    setTranslationActive(null);
    setError(null);
  }, []);

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

  const applyTranslationEvent = useCallback((event) => {
    const { segment_id, status, source_text, translated_text } = event;
    const id = segment_id;
    const text = translated_text || source_text || "";
    if (status === "partial") {
      setTranslationActive({ id, sourceText: source_text, translatedText: text, status });
      setTranslationSegments((prev) => {
        const exists = prev.find((s) => s.id === id);
        if (exists) return prev.map((s) => (s.id === id ? { id, sourceText: source_text, translatedText: text, status } : s));
        return [...prev, { id, sourceText: source_text, translatedText: text, status }];
      });
    } else if (status === "final") {
      setTranslationActive((cur) => (cur && cur.id === id ? null : cur));
      setTranslationSegments((prev) => {
        const exists = prev.find((s) => s.id === id);
        if (exists) return prev.map((s) => (s.id === id ? { id, sourceText: source_text, translatedText: text, status: "final" } : s));
        return [...prev, { id, sourceText: source_text, translatedText: text, status: "final" }];
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
    translationSegments,
    setTranslationSegments,
    translationActive,
    setTranslationActive,
    error,
    setError,
    reset,
    applyTranscriptEvent,
    applyTranslationEvent,
  };
}
