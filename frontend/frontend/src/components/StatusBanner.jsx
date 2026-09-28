import React from "react"; // eslint-disable-line no-unused-vars
export default function StatusBanner({ message, type = "error", retryable = false, onRetry, retryLabel = "Try Again", onDismiss }) {
  if (!message) return null;
  const cls = type === "error" ? "banner banner-error" : "banner banner-info";
  // P10-ERR-005: retry button only for retryable codes; fatal-only banner otherwise
  const showRetry = retryable && !!onRetry;
  return (
    <div className={cls} role="alert" data-testid="status-banner" data-retryable={retryable ? "true" : "false"}>
      <span className="banner-icon" aria-hidden="true">
        {type === "error" ? "⚠" : "ℹ"}
      </span>
      <span className="banner-message">{message}</span>
      <div className="banner-actions">
        {showRetry && (
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
