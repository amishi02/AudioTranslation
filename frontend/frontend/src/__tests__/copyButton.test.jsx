import React from "react"; // eslint-disable-line no-unused-vars
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import Transcript from "../components/Transcript.jsx";
import Translation from "../components/Translation.jsx";
import { SEGMENT_STATUS } from "../utils/constants.js";

describe("copy buttons", () => {
  it("transcript copy copies all segments", async () => {
    const write = vi.fn().mockResolvedValue();
    Object.assign(navigator, { clipboard: { writeText: write } });
    render(<Transcript segments={[{id:1, text:"Hello world", status:SEGMENT_STATUS.FINAL},{id:2, text:"Second", status:SEGMENT_STATUS.FINAL}]} />);
    const btn = screen.getByTestId("copy-transcript");
    expect(btn).not.toBeDisabled();
    await fireEvent.click(btn);
    expect(write).toHaveBeenCalledWith("Hello world\nSecond");
  });
  it("translation copy copies translated", async () => {
    const write = vi.fn().mockResolvedValue();
    Object.assign(navigator, { clipboard: { writeText: write } });
    render(<Translation segments={[{id:1, translatedText:"नमस्ते", sourceText:"Hello", status:SEGMENT_STATUS.FINAL}]} />);
    const btn = screen.getByTestId("copy-translation");
    await fireEvent.click(btn);
    expect(write).toHaveBeenCalledWith("नमस्ते");
  });
  it("copy disabled when empty", () => {
    render(<Transcript segments={[]} />);
    expect(screen.getByTestId("copy-transcript")).toBeDisabled();
  });
  it("auto-scroll container exists", () => {
    render(<Transcript segments={[{id:1, text:"a", status:SEGMENT_STATUS.FINAL}]} />);
    expect(screen.getByTestId("transcript")).toBeInTheDocument();
    expect(screen.getByTestId("transcript-wrapper")).toBeInTheDocument();
  });
});
