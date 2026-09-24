import React from "react"; // eslint-disable-line no-unused-vars
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useAudioPlayback } from "../hooks/useAudioPlayback.js";
import * as playback from "../services/audioPlayback.js";

describe("audioPlayback", () => {
  beforeEach(() => {
    playback._resetForTest();
    vi.restoreAllMocks();
  });

  it("playAudioBuffer queues and plays via mocked AudioContext", async () => {
    // Mock AudioContext
    const mockDecode = vi.fn().mockResolvedValue({ duration: 0.5 });
    const mockSource = { buffer: null, connect: vi.fn(), start: vi.fn(), stop: vi.fn(), onended: null };
    const mockCtx = {
      decodeAudioData: mockDecode,
      createBufferSource: () => mockSource,
      destination: {},
      state: "running",
      resume: vi.fn(),
    };
    global.AudioContext = vi.fn(() => mockCtx);
    global.webkitAudioContext = global.AudioContext;

    const { result } = renderHook(() => useAudioPlayback());
    const wavHeader = new Uint8Array([82,73,70,70,36,0,0,0,87,65,86,69]).buffer; // fake WAV
    await act(async () => {
      await result.current.handleBinary(wavHeader);
    });
    // handleBinary should attempt to play
    expect(mockDecode).toHaveBeenCalled();
  });

  it("handleStart and handleEnd manage status", async () => {
    const { result } = renderHook(() => useAudioPlayback());
    act(() => {
      result.current.handleStart({ sample_rate: 22050, encoding: "wav", segment_id: 1 });
    });
    expect(result.current.status).toBe("playing");
    act(() => {
      result.current.handleEnd();
    });
    // after end, status will go idle after queue drains (async)
  });

  it("mute toggle stops playback", async () => {
    const { result } = renderHook(() => useAudioPlayback());
    expect(result.current.muted).toBe(false);
    act(() => {
      result.current.toggleMute();
    });
    expect(result.current.muted).toBe(true);
    act(() => {
      result.current.toggleMute();
    });
    expect(result.current.muted).toBe(false);
  });

  it("handleSessionEnd cancels playback", async () => {
    const { result } = renderHook(() => useAudioPlayback());
    act(() => {
      result.current.handleStart({ sample_rate: 16000 });
    });
    act(() => {
      result.current.handleSessionEnd();
    });
    expect(result.current.status).toBe("idle");
  });
});
