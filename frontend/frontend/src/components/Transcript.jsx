import React, { useEffect, useRef, useState } from "react"; // eslint-disable-line no-unused-vars
import { SEGMENT_STATUS } from "../utils/constants.js";

/**
 * Renders finalized segments + active partial.
 * Must not duplicate same segment_id — one line per id.
 * Auto-scrolls to latest content and provides themed scrollbar + copy.
 */
export default function Transcript({ segments = [], activeSegment = null }) {
  const all = segments;
  const hasActiveInList = activeSegment && all.some((s) => s.id === activeSegment.id);
  const display =
    activeSegment && !hasActiveInList ? [...all, { ...activeSegment }] : all;

  const containerRef = useRef(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const el = containerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [segments, activeSegment]);

  const handleCopy = async () => {
    const text = display.map((s) => s.text).join("\n");
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
    <div className="transcript-wrapper" data-testid="transcript-wrapper">
      <div className="panel-header">
        <h2 id="transcript-heading" className="panel-title">Source Transcript</h2>
        <button
          type="button"
          className="copy-btn"
          data-testid="copy-transcript"
          aria-label="Copy transcript"
          title={copied ? "Copied!" : "Copy transcript"}
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
      <div className="transcript" data-testid="transcript" ref={containerRef}>
        {display.length === 0 ? (
          <p className="placeholder">No transcript yet</p>
        ) : (
          display.map((seg) => (
            <p
              key={seg.id}
              data-testid={seg.status === SEGMENT_STATUS.FINAL ? "transcript-final" : "transcript-active"}
              data-status={seg.status}
              data-segment-id={seg.id}
              className={seg.status === SEGMENT_STATUS.FINAL ? "segment final" : "segment partial"}
            >
              {seg.text}
              {seg.status === SEGMENT_STATUS.PARTIAL && <span className="partial-indicator"> …</span>}
            </p>
          ))
        )}
      </div>
    </div>
  );
}
