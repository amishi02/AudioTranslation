import React from "react"; // eslint-disable-line no-unused-vars

export default function AudioControls({ micStatus }) {
  return (
    <div className="audio-controls" data-testid="audio-controls">
      {micStatus === "active" && (
        <span className="mic-indicator" data-testid="mic-active">
          ● Listening — microphone active
        </span>
      )}
      {micStatus === "requesting" && <span data-testid="mic-requesting">Requesting microphone…</span>}
      {micStatus === "permission_denied" && <span data-testid="mic-permission-denied">Microphone blocked</span>}
      {micStatus === "error" && <span data-testid="mic-error-state">Microphone error</span>}
    </div>
  );
}
