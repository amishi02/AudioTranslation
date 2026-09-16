import React from "react"; // eslint-disable-line no-unused-vars
import { useEffect, useState } from "react";
import AppShell from "./components/AppShell.jsx";
import { useLanguageSelection } from "./hooks/useLanguageSelection.js";
import { useSessionState } from "./hooks/useSessionState.js";
import { fetchCapabilities, fetchHealth } from "./services/api.js";
import { CONNECTION_STATES } from "./utils/constants.js";
import "./App.css";

function App() {
  const [supportedLanguages, setSupportedLanguages] = useState([]);
  const [backendHealthy, setBackendHealthy] = useState(true);
  const [healthError, setHealthError] = useState(null);
  const [isActive, setIsActive] = useState(false);

  const {
    sourceLanguage,
    targetLanguage,
    setSource,
    setTarget,
    validationError,
    canStart: langCanStart,
  } = useLanguageSelection(supportedLanguages);

  const session = useSessionState();

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

  const handleStart = () => {
    if (!effectiveCanStart) return;
    setIsActive(true);
    session.setConnection(CONNECTION_STATES.LISTENING);
  };

  const handleStop = () => {
    setIsActive(false);
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

  const bannerMessage = !backendHealthy ? healthError || "Unable to connect to translation service" : null;

  const connectionStatus = !backendHealthy
    ? CONNECTION_STATES.ERROR
    : isActive
      ? CONNECTION_STATES.LISTENING
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
      connectionError={healthError}
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
