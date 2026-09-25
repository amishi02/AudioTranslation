import React from "react"; // eslint-disable-line no-unused-vars
import { CONNECTION_STATES } from "../utils/constants.js";

const STATUS_TEXT = {
  [CONNECTION_STATES.IDLE]: "Select languages to start",
  [CONNECTION_STATES.CONNECTING]: "Connecting...",
  [CONNECTION_STATES.READY]: "Ready",
  [CONNECTION_STATES.LISTENING]: "Listening...",
  [CONNECTION_STATES.PROCESSING]: "Translating...",
  [CONNECTION_STATES.ERROR]: "Error",
  [CONNECTION_STATES.DISCONNECTED]: "Disconnected",
};

const STATUS_CLASS = {
  [CONNECTION_STATES.IDLE]: "status-idle",
  [CONNECTION_STATES.CONNECTING]: "status-connecting",
  [CONNECTION_STATES.READY]: "status-ready",
  [CONNECTION_STATES.LISTENING]: "status-listening",
  [CONNECTION_STATES.PROCESSING]: "status-processing",
  [CONNECTION_STATES.ERROR]: "status-error",
  [CONNECTION_STATES.DISCONNECTED]: "status-disconnected",
};

export default function ConnectionStatus({ status, error, micStatus, modelLoading = false }) {
  const text = modelLoading ? "Preparing language models..." : STATUS_TEXT[status] || status;
  const cls = STATUS_CLASS[status] || "status-idle";
  return (
    <div
      className={`connection-status ${cls}`}
      aria-live="polite"
      data-testid="connection-status"
      data-status={status}
    >
      <span className="status-text">{text}</span>
      {micStatus === "active" && <span className="mic-subline" data-testid="mic-status"> — Mic active</span>}
      {micStatus === "requesting" && <span className="mic-subline"> — Requesting mic…</span>}
      {error && <span className="status-error-text"> — {error}</span>}
    </div>
  );
}
