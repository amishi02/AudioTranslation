import React from "react"; // eslint-disable-line no-unused-vars
import { SEGMENT_STATUS } from "../utils/constants.js";

/**
 * Renders finalized segments + active partial.
 * Must not duplicate same segment_id — one line per id.
 */
export default function Transcript({ segments = [], activeSegment = null }) {
  // Merge: segments already contains active partial; ensure no duplicate id rendering
  const all = segments;
  // If activeSegment is provided separately and not already in segments, append it (partial)
  const hasActiveInList = activeSegment && all.some((s) => s.id === activeSegment.id);
  const display =
    activeSegment && !hasActiveInList ? [...all, { ...activeSegment }] : all;

  if (display.length === 0) {
    return (
      <div className="transcript" data-testid="transcript">
        <p className="placeholder">No transcript yet</p>
      </div>
    );
  }

  return (
    <div className="transcript" data-testid="transcript">
      {display.map((seg) => (
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
      ))}
    </div>
  );
}
