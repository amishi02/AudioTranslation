import React from "react"; // eslint-disable-line no-unused-vars
import { useEffect, useRef, useState } from "react";
import AppShell from "./components/AppShell.jsx";
import AudioControls from "./components/AudioControls.jsx";
import { useLanguageSelection } from "./hooks/useLanguageSelection.js";
import { useSessionState } from "./hooks/useSessionState.js";
import { useWebSocket } from "./hooks/useWebSocket.js";
import { useAudioRecorder } from "./hooks/useAudioRecorder.js";
import { useAudioPlayback } from "./hooks/useAudioPlayback.js";
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
  const [modelLoading, setModelLoading] = useState(false);
  const audio = useAudioRecorder();
  const playback = useAudioPlayback();
  const sessionReadyRef = useRef(false);
  const pendingAudioRef = useRef([]);

  const ws = useWebSocket({
    onSessionReady: (event) => {
      setModelLoading(false);
      sessionReadyRef.current = true;
      for (const buffer of pendingAudioRef.current) ws.sendAudio(buffer);
      pendingAudioRef.current = [];
      session.setSessionId(event.session_id);
      session.setConnection(CONNECTION_STATES.LISTENING);
      setWsError(null);
    },
    onSessionEnded: () => {
      setModelLoading(false);
      sessionReadyRef.current = false;
      pendingAudioRef.current = [];
      session.setSessionId(null);
      session.setConnection(CONNECTION_STATES.IDLE);
      playback.handleSessionEnd();
    },
    onErrorEvent: (event) => {
      setModelLoading(false);
      sessionReadyRef.current = false;
      pendingAudioRef.current = [];
      setWsError(event.message || event.code);
      if (event.code === "UNSUPPORTED_PIPELINE") playback.handleSessionEnd();
    },
    onTranscript: (event) => {
      session.applyTranscriptEvent(event);
    },
    onTranslation: (event) => {
      session.applyTranslationEvent(event);
    },
    onAudioStart: (event) => playback.handleStart(event),
    onAudioEnd: () => playback.handleEnd(),
    onBinary: (buf) => playback.handleBinary(buf),
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
    audio.clearError();
    // Clear old session content — new session should start fresh (fixed length, latest at bottom)
    session.reset();
    setModelLoading(true);
    sessionReadyRef.current = false;
    pendingAudioRef.current = [];
    session.setConnection(CONNECTION_STATES.CONNECTING);
    ws.startSession({ sourceLanguage, targetLanguage });
    const ok = await audio.startRecording(
      (buffer) => {
        if (sessionReadyRef.current) {
          ws.sendAudio(buffer);
        } else if (pendingAudioRef.current.length < 32) {
          pendingAudioRef.current.push(buffer);
        }
      },
      { wsStatusRef }
    );
    if (ok) {
      session.setConnection(CONNECTION_STATES.LISTENING);
    } else {
      // Permission denied or mic error — keep banner, stop WS session to avoid hanging
      ws.stopSession();
      session.setConnection(CONNECTION_STATES.IDLE);
    }
  };

  const handleStop = async () => {
    await audio.stopRecording();
    setModelLoading(false);
    sessionReadyRef.current = false;
    pendingAudioRef.current = [];
    playback.handleSessionEnd();
    ws.stopSession();
    session.setConnection(CONNECTION_STATES.IDLE);
  };

  // If WS disconnects mid-speech, stop mic and playback
  useEffect(() => {
    if (
      ws.status === CONNECTION_STATES.DISCONNECTED ||
      ws.status === CONNECTION_STATES.ERROR ||
      ws.status === CONNECTION_STATES.IDLE
    ) {
      if (audio.micStatus === "active") {
        audio.stopRecording();
      }
      playback.handleSessionEnd();
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

  const handleDismissBanner = () => {
    setWsError(null);
    setHealthError(null);
    audio.clearError();
    setBackendHealthy(true);
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

  const transcriptSegments = session.segments;
  const translationSegments = session.translationSegments;

  return (
    <>
      <AudioControls micStatus={audio.micStatus} />
      <AppShell
        sourceLanguage={sourceLanguage}
        targetLanguage={targetLanguage}
        onSourceChange={setSource}
        onTargetChange={setTarget}
        supportedLanguages={supportedLanguages}
        connectionStatus={connectionStatus}
        modelLoading={modelLoading}
        connectionError={wsError || healthError || audio.error}
        bannerMessage={bannerMessage}
        onRetry={handleRetryHealth}
        onDismiss={handleDismissBanner}
        transcriptSegments={transcriptSegments}
        transcriptActive={session.activeSegment}
        translationSegments={translationSegments}
        translationActive={session.translationActive}
        canStart={effectiveCanStart}
        validationError={validationError}
        backendHealthy={backendHealthy}
        onStart={handleStart}
        onStop={handleStop}
        isActive={isActive}
        micStatus={audio.micStatus}
        playbackStatus={playback.status}
        playbackMuted={playback.muted}
        onToggleMute={playback.toggleMute}
      />
    </>
  );
}

export default App;
