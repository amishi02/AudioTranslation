import React from "react"; // eslint-disable-line no-unused-vars
import { SEGMENT_STATUS } from "../utils/constants.js";

/**
 * Mirrors Transcript semantics for translated segments.
 * Each segment: { id, sourceText, translatedText, status }
 */
export default function Translation({ segments = [], activeSegment = null }) {
  const hasActiveInList = activeSegment && segments.some((s) => s.id === activeSegment.id);
  const display =
    activeSegment && !hasActiveInList ? [...segments, { ...activeSegment }] : segments;

  if (display.length === 0) {
    return (
      <div className="translation" data-testid="translation">
        <p className="placeholder">No translation yet</p>
      </div>
    );
  }

  return (
    <div className="translation" data-testid="translation">
      {display.map((seg) => (
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
      ))}
    </div>
  );
}
