import React from "react"; // eslint-disable-line no-unused-vars
export default function StatusBanner({ message, type = "error", onRetry, retryLabel = "Try Again", onDismiss }) {
  if (!message) return null;
  const cls = type === "error" ? "banner banner-error" : "banner banner-info";
  return (
    <div className={cls} role="alert" data-testid="status-banner">
      <span className="banner-icon" aria-hidden="true">
        {type === "error" ? "⚠" : "ℹ"}
      </span>
      <span className="banner-message">{message}</span>
      <div className="banner-actions">
        {onRetry && (
          <button type="button" className="banner-retry" onClick={onRetry}>
            {retryLabel}
          </button>
        )}
        {onDismiss && (
          <button type="button" className="banner-dismiss" onClick={onDismiss} aria-label="Dismiss error">
            ×
          </button>
        )}
      </div>
    </div>
  );
}
