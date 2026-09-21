/**
 * P7-TEST-004: frontend reducer stabilization
 * Verify successive partials for same segment_id replace, final is stable and no duplicate.
 */
import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSessionState } from "../hooks/useSessionState.js";

describe("useSessionState transcript stabilization", () => {
  it("replaces partial for same segment_id without duplicating", () => {
    const { result } = renderHook(() => useSessionState());
    act(() => {
      result.current.applyTranscriptEvent({ segment_id: 1, status: "partial", text: "Hello my" });
    });
    expect(result.current.segments).toHaveLength(1);
    expect(result.current.segments[0].text).toBe("Hello my");
    expect(result.current.activeSegment.text).toBe("Hello my");

    act(() => {
      result.current.applyTranscriptEvent({ segment_id: 1, status: "partial", text: "Hello my name" });
    });
    expect(result.current.segments).toHaveLength(1);
    expect(result.current.segments[0].text).toBe("Hello my name");
    expect(result.current.activeSegment.text).toBe("Hello my name");
  });

  it("commits final and clears active, next partial increments id", () => {
    const { result } = renderHook(() => useSessionState());
    act(() => {
      result.current.applyTranscriptEvent({ segment_id: 1, status: "partial", text: "Hello" });
    });
    act(() => {
      result.current.applyTranscriptEvent({ segment_id: 1, status: "final", text: "Hello my name is John." });
    });
    expect(result.current.segments).toHaveLength(1);
    expect(result.current.segments[0].status).toBe("final");
    expect(result.current.segments[0].text).toBe("Hello my name is John.");
    expect(result.current.activeSegment).toBeNull();

    act(() => {
      result.current.applyTranscriptEvent({ segment_id: 2, status: "partial", text: "Next" });
    });
    expect(result.current.segments).toHaveLength(2);
    expect(result.current.segments[1].id).toBe(2);
    expect(result.current.segments[1].text).toBe("Next");
  });

  it("does not duplicate final for same segment_id", () => {
    const { result } = renderHook(() => useSessionState());
    act(() => {
      result.current.applyTranscriptEvent({ segment_id: 1, status: "partial", text: "Hello" });
      result.current.applyTranscriptEvent({ segment_id: 1, status: "final", text: "Hello world." });
      result.current.applyTranscriptEvent({ segment_id: 1, status: "final", text: "Hello world." });
    });
    const finals = result.current.segments.filter((s) => s.id === 1);
    expect(finals).toHaveLength(1);
    expect(finals[0].status).toBe("final");
  });

  it("translation panel remains wired (partial/final)", () => {
    const { result } = renderHook(() => useSessionState());
    act(() => {
      result.current.applyTranslationEvent({ segment_id: 1, status: "partial", source_text: "Hello", translated_text: "[hi] Hello" });
    });
    expect(result.current.translationSegments).toHaveLength(1);
    act(() => {
      result.current.applyTranslationEvent({ segment_id: 1, status: "final", source_text: "Hello world", translated_text: "[hi] Hello world" });
    });
    expect(result.current.translationSegments[0].status).toBe("final");
  });
});
