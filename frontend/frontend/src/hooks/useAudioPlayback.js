/**
 * useAudioPlayback — Phase 9 hook managing audio queue states.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { playAudioBuffer, stopPlayback, setMuted, getQueueLength } from "../services/audioPlayback.js";

export function useAudioPlayback() {
  const [status, setStatus] = useState("idle"); // idle|playing|error
  const [muted, setMutedState] = useState(false);
  const pendingRef = useRef(null); // {sampleRate, encoding}

  const handleStart = useCallback((event) => {
    // audio.output.start marker
    pendingRef.current = {
      sampleRate: event.sample_rate || 22050,
      encoding: event.encoding || "wav",
      segmentId: event.segment_id,
    };
    setStatus("playing");
  }, []);

  const handleBinary = useCallback(async (buffer) => {
    const pending = pendingRef.current;
    const sr = pending?.sampleRate || 22050;
    try {
      // buffer is ArrayBuffer from websocket
      const ab = buffer instanceof ArrayBuffer ? buffer : await buffer.arrayBuffer?.() || buffer;
      await playAudioBuffer(ab, sr);
      setStatus("playing");
    } catch {
      setStatus("error");
    }
    // Keep pending for end marker; next binary will chain via queue
  }, []);

  const handleEnd = useCallback(() => {
    pendingRef.current = null;
    // status remains playing until queue drains; poll queue length
    const check = () => {
      if (getQueueLength() === 0) setStatus("idle");
      else setTimeout(check, 200);
    };
    setTimeout(check, 300);
  }, []);

  const handleSessionEnd = useCallback(() => {
    stopPlayback();
    pendingRef.current = null;
    setStatus("idle");
  }, []);

  const toggleMute = useCallback(() => {
    const next = !muted;
    setMuted(next);
    setMutedState(next);
    if (next) stopPlayback();
  }, [muted]);

  useEffect(() => {
    return () => stopPlayback();
  }, []);

  return {
    status,
    muted,
    toggleMute,
    handleStart,
    handleBinary,
    handleEnd,
    handleSessionEnd,
  };
}
