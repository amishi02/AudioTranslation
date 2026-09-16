import React from "react"; // eslint-disable-line no-unused-vars
export default function StatusBanner({ message, type = "error", onRetry, retryLabel = "Try Again" }) {
  if (!message) return null;
  const cls = type === "error" ? "banner banner-error" : "banner banner-info";
  return (
    <div className={cls} role="alert" data-testid="status-banner">
      <span className="banner-message">{message}</span>
      {onRetry && (
        <button type="button" className="banner-retry" onClick={onRetry}>
          {retryLabel}
        </button>
      )}
    </div>
  );
}
