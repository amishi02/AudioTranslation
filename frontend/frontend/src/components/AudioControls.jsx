import React from "react"; // eslint-disable-line no-unused-vars

export default function AudioControls({ micStatus, micError }) {
  const showPermissionHelp = micStatus === "permission_denied";
  return (
    <div className="audio-controls" data-testid="audio-controls">
      {micStatus === "active" && (
        <span className="mic-indicator" data-testid="mic-active">
          ● Listening
        </span>
      )}
      {micStatus === "requesting" && <span data-testid="mic-requesting">Requesting microphone...</span>}
      {micError && (
        <p className="validation-error" role="alert" data-testid="mic-error">
          {micError}
        </p>
      )}
      {showPermissionHelp && (
        <p className="validation-error" role="alert">
          Microphone access is required to start translation. Allow in browser settings and try again.
        </p>
      )}
      {/* Start/Stop are rendered by AppShell, but also show mic status here */}
    </div>
  );
}
