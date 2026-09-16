/**
 * P3-TEST-003: Transcript segment replacement semantics (partial → partial → final).
 * Prevents regression for Phases 7-8: same segment_id must replace, not duplicate.
 * Requires Vitest (Phase 10).
 */
import React from "react"; // eslint-disable-line no-unused-vars
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Transcript from "../components/Transcript.jsx";
import { SEGMENT_STATUS } from "../utils/constants.js";

describe("Transcript", () => {
  it("replaces partial without duplicating same id", () => {
    const { rerender } = render(
      <Transcript segments={[{ id: 1, text: "Hello my", status: SEGMENT_STATUS.PARTIAL }]} />
    );
    expect(screen.getByTestId("transcript-active")).toBeInTheDocument();
    rerender(
      <Transcript segments={[{ id: 1, text: "Hello my name", status: SEGMENT_STATUS.PARTIAL }]} />
    );
    const els = screen.getAllByTestId("transcript-active");
    expect(els).toHaveLength(1);
    expect(els[0]).toHaveTextContent("Hello my name");
  });

  it("commits final and keeps stable", () => {
    render(
      <Transcript
        segments={[
          { id: 1, text: "Hello my name is John.", status: SEGMENT_STATUS.FINAL },
          { id: 2, text: "I work as a", status: SEGMENT_STATUS.PARTIAL },
        ]}
      />
    );
    expect(screen.getByTestId("transcript-final")).toBeInTheDocument();
    expect(screen.getByTestId("transcript-active")).toHaveTextContent("I work as a");
  });
});
