/**
 * P5-TEST-004: useAudioRecorder lifecycle with mocked AudioWorklet + getUserMedia
 */
import React from "react"; // eslint-disable-line no-unused-vars
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useAudioRecorder } from "../hooks/useAudioRecorder.js";

// Mock AudioWorkletNode and AudioContext globally for test
class MockAudioWorkletNode {
  // eslint-disable-next-line no-unused-vars
  constructor(ctx, _name) {
    this.port = { postMessage: () => {}, onmessage: null, close: vi.fn() };
    this.connect = vi.fn();
    this.disconnect = vi.fn();
    this.context = ctx;
  }
}
class MockMediaStreamTrack {
  constructor() {
    this.readyState = "live";
    this.stop = vi.fn(() => {
      this.readyState = "ended";
    });
  }
}
class MockMediaStream {
  constructor() {
    this.track = new MockMediaStreamTrack();
  }
  getTracks() {
    return [this.track];
  }
}

describe("useAudioRecorder", () => {
  let originalMediaDevices;
  let originalAudioContext;
  let originalAudioWorkletNode;

  beforeEach(() => {
    originalMediaDevices = navigator.mediaDevices;
    originalAudioContext = window.AudioContext;
    originalAudioWorkletNode = window.AudioWorkletNode;

    // Mock getUserMedia
    Object.defineProperty(navigator, "mediaDevices", {
      value: {
        getUserMedia: vi.fn(async () => new MockMediaStream()),
      },
      configurable: true,
    });

    // Mock AudioContext
    window.AudioContext = vi.fn(() => {
      return {
        sampleRate: 16000,
        state: "running",
        destination: {},
        audioWorklet: { addModule: vi.fn(async () => {}) },
        createMediaStreamSource: vi.fn(() => ({ connect: vi.fn(), disconnect: vi.fn() })),
        createGain: vi.fn(() => ({ gain: { value: 1 }, connect: vi.fn(), disconnect: vi.fn() })),
        close: vi.fn(async () => {}),
      };
    });
    window.AudioWorkletNode = MockAudioWorkletNode;
    window.webkitAudioContext = window.AudioContext;
  });

  afterEach(() => {
    Object.defineProperty(navigator, "mediaDevices", {
      value: originalMediaDevices,
      configurable: true,
    });
    window.AudioContext = originalAudioContext;
    window.AudioWorkletNode = originalAudioWorkletNode;
  });

  it("starts and stops recording", async () => {
    const { result } = renderHook(() => useAudioRecorder());
    expect(result.current.micStatus).toBe("idle");

    await act(async () => {
      await result.current.startRecording(() => {});
    });

    expect(result.current.micStatus).toBe("active");

    await act(async () => {
      await result.current.stopRecording();
    });

    expect(result.current.micStatus).toBe("idle");
  });

  it("handles permission denied", async () => {
    navigator.mediaDevices.getUserMedia = vi.fn(async () => {
      const err = new Error("Permission denied");
      err.name = "NotAllowedError";
      throw err;
    });

    const { result } = renderHook(() => useAudioRecorder());
    await act(async () => {
      await result.current.startRecording(() => {});
    });

    expect(result.current.micStatus).toBe("permission_denied");
    expect(result.current.error).toMatch(/Microphone access is required/);
  });

  it("double start is no-op", async () => {
    const { result } = renderHook(() => useAudioRecorder());
    await act(async () => {
      await result.current.startRecording(() => {});
    });
    const firstStatus = result.current.micStatus;
    await act(async () => {
      await result.current.startRecording(() => {});
    });
    expect(result.current.micStatus).toBe(firstStatus);
  });
});
