import React from "react"; // eslint-disable-line no-unused-vars
import { useEffect, useState } from "react";
import AppShell from "./components/AppShell.jsx";
import { useLanguageSelection } from "./hooks/useLanguageSelection.js";
import { useSessionState } from "./hooks/useSessionState.js";
import { useWebSocket } from "./hooks/useWebSocket.js";
import { fetchCapabilities, fetchHealth } from "./services/api.js";
import { CONNECTION_STATES } from "./utils/constants.js";
import "./App.css";

function App() {
  const [supportedLanguages, setSupportedLanguages] = useState([]);
  const [backendHealthy, setBackendHealthy] = useState(true);
  const [healthError, setHealthError] = useState(null);

  const {
    sourceLanguage,
    targetLanguage,
    setSource,
    setTarget,
    validationError,
    canStart: langCanStart,
  } = useLanguageSelection(supportedLanguages);

  const session = useSessionState();
  const [wsError, setWsError] = useState(null);

  const ws = useWebSocket({
    onSessionReady: (event) => {
      session.setSessionId(event.session_id);
      session.setConnection(CONNECTION_STATES.LISTENING);
      setWsError(null);
    },
    onSessionEnded: () => {
      session.setSessionId(null);
      session.setConnection(CONNECTION_STATES.IDLE);
    },
    onErrorEvent: (event) => {
      setWsError(event.message || event.code);
    },
  });

  // P3-INT-001: fetch health + capabilities on mount
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        await fetchHealth();
        if (!cancelled) {
          setBackendHealthy(true);
          setHealthError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setBackendHealthy(false);
          setHealthError(e.message || "Unable to connect to translation service");
        }
      }
      try {
        const caps = await fetchCapabilities();
        if (!cancelled && caps?.supported_languages) {
          setSupportedLanguages(caps.supported_languages);
        }
      } catch {
        // capabilities failure falls back to LANGUAGES default list (constants)
        if (!cancelled) setSupportedLanguages([]);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const effectiveCanStart = langCanStart && backendHealthy;

  // Derive isActive from WS status for Phase 4
  const isActiveWs = ws.status === CONNECTION_STATES.LISTENING || ws.status === CONNECTION_STATES.READY || ws.status === CONNECTION_STATES.CONNECTING;
  const isActive = isActiveWs || false;

  const handleStart = () => {
    if (!effectiveCanStart) return;
    setWsError(null);
    session.setConnection(CONNECTION_STATES.CONNECTING);
    ws.startSession({ sourceLanguage, targetLanguage });
  };

  const handleStop = () => {
    ws.stopSession();
    session.setConnection(CONNECTION_STATES.IDLE);
  };

  const handleRetryHealth = async () => {
    try {
      await fetchHealth();
      setBackendHealthy(true);
      setHealthError(null);
    } catch (e) {
      setHealthError(e.message);
    }
  };

  const bannerMessage = wsError || (!backendHealthy ? healthError || "Unable to connect to translation service" : null);

  const wsStatus = ws.status;
  const connectionStatus = !backendHealthy
    ? CONNECTION_STATES.ERROR
    : wsStatus === CONNECTION_STATES.ERROR
      ? CONNECTION_STATES.ERROR
      : isActive
        ? CONNECTION_STATES.LISTENING
        : wsStatus === CONNECTION_STATES.CONNECTING
          ? CONNECTION_STATES.CONNECTING
          : CONNECTION_STATES.IDLE;

  // Placeholder segments for Phase 3 shell (no WS yet)
  const transcriptSegments = session.segments;
  const translationSegments = session.segments.map((s) => ({
    id: s.id,
    translatedText: s.text ? `[${s.text}]` : "",
    sourceText: s.text,
    status: s.status,
  }));

  return (
    <AppShell
      sourceLanguage={sourceLanguage}
      targetLanguage={targetLanguage}
      onSourceChange={setSource}
      onTargetChange={setTarget}
      supportedLanguages={supportedLanguages}
      connectionStatus={connectionStatus}
      connectionError={wsError || healthError}
      bannerMessage={bannerMessage}
      onRetry={handleRetryHealth}
      transcriptSegments={transcriptSegments}
      transcriptActive={session.activeSegment}
      translationSegments={translationSegments}
      translationActive={
        session.activeSegment
          ? {
              id: session.activeSegment.id,
              translatedText: `[${session.activeSegment.text}]`,
              sourceText: session.activeSegment.text,
              status: session.activeSegment.status,
            }
          : null
      }
      canStart={effectiveCanStart}
      validationError={validationError}
      backendHealthy={backendHealthy}
      onStart={handleStart}
      onStop={handleStop}
      isActive={isActive}
    />
  );
}

export default App;
