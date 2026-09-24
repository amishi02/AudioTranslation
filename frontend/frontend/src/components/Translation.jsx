import React, { useEffect, useRef, useState } from "react"; // eslint-disable-line no-unused-vars
import { SEGMENT_STATUS } from "../utils/constants.js";

/**
 * Mirrors Transcript semantics for translated segments.
 * Each segment: { id, sourceText, translatedText, status }
 * Auto-scrolls + themed scrollbar + copy.
 */
export default function Translation({ segments = [], activeSegment = null }) {
  const hasActiveInList = activeSegment && segments.some((s) => s.id === activeSegment.id);
  const display =
    activeSegment && !hasActiveInList ? [...segments, { ...activeSegment }] : segments;

  const containerRef = useRef(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const el = containerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [segments, activeSegment]);

  const handleCopy = async () => {
    const text = display.map((s) => s.translatedText || s.text || "").join("\n");
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1400);
  };

  const hasContent = display.length > 0;

  return (
    <div className="translation-wrapper" data-testid="translation-wrapper">
      <div className="panel-header">
        <h2 id="translation-heading" className="panel-title">Translation</h2>
        <button
          type="button"
          className="copy-btn"
          data-testid="copy-translation"
          aria-label="Copy translation"
          title={copied ? "Copied!" : "Copy translation"}
          onClick={handleCopy}
          disabled={!hasContent}
        >
          {copied ? (
            <span className="copy-label">Copied!</span>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <rect x="9" y="9" width="13" height="13" rx="2" />
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v3" />
            </svg>
          )}
        </button>
      </div>
      <div className="translation" data-testid="translation" ref={containerRef}>
        {display.length === 0 ? (
          <p className="placeholder">No translation yet</p>
        ) : (
          display.map((seg) => (
            <p
              key={seg.id}
              data-testid={seg.status === SEGMENT_STATUS.FINAL ? "translation-final" : "translation-active"}
              data-status={seg.status}
              data-segment-id={seg.id}
              className={seg.status === SEGMENT_STATUS.FINAL ? "segment final" : "segment partial"}
            >
              <span className="translated-text">{seg.translatedText || seg.text || ""}</span>
              {seg.sourceText && <span className="source-hint"> ({seg.sourceText})</span>}
              {seg.status === SEGMENT_STATUS.PARTIAL && <span className="partial-indicator"> …</span>}
            </p>
          ))
        )}
      </div>
    </div>
  );
}
