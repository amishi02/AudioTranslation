import React from "react"; // eslint-disable-line no-unused-vars
import { useEffect, useRef, useState } from "react";
import AppShell from "./components/AppShell.jsx";
import AudioControls from "./components/AudioControls.jsx";
import { useLanguageSelection } from "./hooks/useLanguageSelection.js";
import { useSessionState } from "./hooks/useSessionState.js";
import { useWebSocket } from "./hooks/useWebSocket.js";
import { useAudioRecorder } from "./hooks/useAudioRecorder.js";
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
  const audio = useAudioRecorder();

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

  // Track WS status for audio backpressure
  const wsStatusRef = useRef(ws.status);
  useEffect(() => {
    wsStatusRef.current = ws.status;
  }, [ws.status]);

  // Derive isActive from WS + mic status (Phase 5)
  const isActiveWs =
    ws.status === CONNECTION_STATES.LISTENING ||
    ws.status === CONNECTION_STATES.READY ||
    ws.status === CONNECTION_STATES.CONNECTING;
  const isActive = isActiveWs || audio.micStatus === "active";

  const handleStart = async () => {
    if (!effectiveCanStart) return;
    setWsError(null);
    session.setConnection(CONNECTION_STATES.CONNECTING);
    ws.startSession({ sourceLanguage, targetLanguage });
    // Start mic capture — onChunk sends raw PCM via WS
    // Respect backpressure via wsStatusRef
    await audio.startRecording(
      (buffer) => {
        // buffer is ArrayBuffer (PCM S16LE 1920 bytes)
        ws.sendAudio(buffer);
      },
      { wsStatusRef }
    );
    if (audio.micStatus === "permission_denied" || audio.micStatus === "error") {
      // Prevent hanging session without audio
      // Keep banner via audio.error
    } else if (audio.micStatus === "active") {
      session.setConnection(CONNECTION_STATES.LISTENING);
    }
  };

  const handleStop = async () => {
    await audio.stopRecording();
    ws.stopSession();
    session.setConnection(CONNECTION_STATES.IDLE);
  };

  // If WS disconnects mid-speech, stop mic
  useEffect(() => {
    if (
      ws.status === CONNECTION_STATES.DISCONNECTED ||
      ws.status === CONNECTION_STATES.ERROR ||
      ws.status === CONNECTION_STATES.IDLE
    ) {
      if (audio.micStatus === "active") {
        audio.stopRecording();
      }
    }
  }, [ws.status, audio.micStatus]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleRetryHealth = async () => {
    try {
      await fetchHealth();
      setBackendHealthy(true);
      setHealthError(null);
    } catch (e) {
      setHealthError(e.message);
    }
  };

  const audioBanner = audio.error || (audio.micStatus === "permission_denied" ? "Microphone access is required to start translation. Allow in browser settings and try again." : null);
  const bannerMessage = wsError || audioBanner || (!backendHealthy ? healthError || "Unable to connect to translation service" : null);

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
    <>
      <AudioControls micStatus={audio.micStatus} micError={audio.error} />
      <AppShell
        sourceLanguage={sourceLanguage}
        targetLanguage={targetLanguage}
        onSourceChange={setSource}
        onTargetChange={setTarget}
        supportedLanguages={supportedLanguages}
        connectionStatus={connectionStatus}
        connectionError={wsError || healthError || audio.error}
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
      micStatus={audio.micStatus}
      />
    </>
  );
}

export default App;
