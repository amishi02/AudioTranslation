import React from "react"; // eslint-disable-line no-unused-vars
import LanguageSelector from "./LanguageSelector.jsx";
import ConnectionStatus from "./ConnectionStatus.jsx";
import Transcript from "./Transcript.jsx";
import Translation from "./Translation.jsx";
import StatusBanner from "./StatusBanner.jsx";

/**
 * Layout per PRD §8 — no business logic, props only.
 */
export default function AppShell({
  sourceLanguage,
  targetLanguage,
  onSourceChange,
  onTargetChange,
  supportedLanguages = [],
  connectionStatus = "idle",
  modelLoading = false,
  connectionError = null,
  bannerMessage = null,
  onRetry,
  onDismiss,
  // transcript / translation
  transcriptSegments = [],
  transcriptActive = null,
  translationSegments = [],
  translationActive = null,
  // controls
  canStart = false,
  validationError = null,
  backendHealthy = true,
  onStart,
  onStop,
  isActive = false,
  micStatus = "idle",
  playbackStatus = "idle",
  playbackMuted = false,
  onToggleMute,
}) {
  const startDisabled = !canStart || !backendHealthy;
  let startReason = "";
  if (!backendHealthy) startReason = "Backend unreachable";
  else if (validationError) startReason = validationError;
  else if (!sourceLanguage || !targetLanguage) startReason = "Select source and target";

  return (
    <div className="app-shell" data-testid="app-shell">
      <header className="app-header">
        <h1>Real-Time Audio Translation</h1>
        <p className="app-subtitle">Speak and see live transcript + translation</p>
      </header>

      {bannerMessage && <StatusBanner message={bannerMessage} onRetry={onRetry} onDismiss={onDismiss} />}

      <section className="controls-section">
        <LanguageSelector
          sourceLanguage={sourceLanguage}
          targetLanguage={targetLanguage}
          onSourceChange={onSourceChange}
          onTargetChange={onTargetChange}
          supportedLanguages={supportedLanguages}
        />
        <ConnectionStatus status={connectionStatus} error={connectionError} micStatus={micStatus} modelLoading={modelLoading} />
        <div className="controls-row">
          {!isActive ? (
            <button
              type="button"
              data-testid="start-button"
              disabled={startDisabled}
              onClick={onStart}
              className="btn btn-primary"
            >
              Start Translation
            </button>
          ) : (
            <button
              type="button"
              data-testid="stop-button"
              onClick={onStop}
              className="btn btn-danger"
            >
              Stop Translation
            </button>
          )}
        </div>
        <div className="playback-controls" data-testid="playback-controls">
          <span className="playback-status" data-testid="playback-status" data-status={playbackStatus}>
            {playbackStatus === "playing" ? "🔊 Playing translation" : playbackMuted ? "🔇 Muted" : "🔈 Ready"}
          </span>
          <button
            type="button"
            className="btn btn-secondary"
            data-testid="mute-toggle"
            onClick={onToggleMute}
            aria-label={playbackMuted ? "Unmute" : "Mute"}
          >
            {playbackMuted ? "Unmute" : "Mute"}
          </button>
        </div>
        {startReason && !isActive && (
          <p className="start-reason" data-testid="start-reason">
            {startReason}
          </p>
        )}
      </section>

      <section className="panels" aria-label="Translation panels">
        <div className="panel">
          <Transcript segments={transcriptSegments} activeSegment={transcriptActive} />
        </div>
        <div className="panel">
          <Translation segments={translationSegments} activeSegment={translationActive} />
        </div>
      </section>

      <footer className="app-footer">
        <small>Real-Time Translation • Phase 5 • Low-latency streaming</small>
      </footer>
    </div>
  );
}
