/**
 * useAudioRecorder — mic lifecycle + chunking → PCM S16LE → onChunk(ArrayBuffer)
 * State: idle | requesting | active | error | permission_denied
 */
import { useCallback, useRef, useState } from "react";
import {
  AUDIO_TARGET_SAMPLE_RATE,
  CHUNK_SAMPLES,
  MicPermissionDenied,
  MicNotFound,
  attachWorklet,
  createAudioContext,
  floatTo16BitPCM,
  getAudioConfig,
  requestMicrophone,
  resampleLinear,
} from "../services/audio.js";

export function useAudioRecorder() {
  const [micStatus, setMicStatus] = useState("idle");
  const [error, setError] = useState(null);

  const streamRef = useRef(null);
  const ctxRef = useRef(null);
  const workletRef = useRef(null);
  const sourceRef = useRef(null);
  const accumulatorRef = useRef([]);
  const accumulatorLenRef = useRef(0);

  const resetAccumulator = useCallback(() => {
    accumulatorRef.current = [];
    accumulatorLenRef.current = 0;
  }, []);

  const stopRecording = useCallback(async () => {
    if (micStatus === "idle") return;
    const stream = streamRef.current;
    const ctx = ctxRef.current;
    const node = workletRef.current;

    try {
      if (node && node.port) node.port.close();
      if (node) node.disconnect();
    } catch {
      void 0;
    }
    try {
      if (sourceRef.current) sourceRef.current.disconnect();
    } catch {
      void 0;
    }

    if (stream) {
      stream.getTracks().forEach((t) => {
        try {
          t.stop();
        } catch {
          void 0;
        }
      });
    }
    if (ctx) {
      try {
        await ctx.close();
      } catch {
        void 0;
      }
    }
    streamRef.current = null;
    ctxRef.current = null;
    workletRef.current = null;
    sourceRef.current = null;
    resetAccumulator();
    setMicStatus("idle");
    setError(null);
  }, [micStatus, resetAccumulator]);

  const startRecording = useCallback(
    async (onChunk, { wsStatusRef } = {}) => {
      if (micStatus === "active" || micStatus === "requesting") return;
      setMicStatus("requesting");
      setError(null);
      resetAccumulator();

      let stream;
      try {
        stream = await requestMicrophone();
      } catch (e) {
        if (e instanceof MicPermissionDenied) {
          setMicStatus("permission_denied");
          setError("Microphone access is required to start translation. Allow in browser settings and try again.");
        } else if (e instanceof MicNotFound) {
          setMicStatus("error");
          setError("Microphone not found. Connect a microphone and try again.");
        } else {
          setMicStatus("error");
          setError(e.message || "Failed to access microphone");
        }
        return;
      }

      let ctx;
      let node;
      try {
        ctx = createAudioContext(AUDIO_TARGET_SAMPLE_RATE);
        await attachWorklet(ctx);
        node = new AudioWorkletNode(ctx, "audio-processor");
      } catch (e) {
        stream.getTracks().forEach((t) => t.stop());
        setMicStatus("error");
        setError(e.message || "Audio not supported in this browser");
        return;
      }

      streamRef.current = stream;
      ctxRef.current = ctx;
      workletRef.current = node;

      const source = ctx.createMediaStreamSource(stream);
      sourceRef.current = source;
      source.connect(node);

      const cfg = getAudioConfig(ctx);
      console.log(`[audio] actualRate=${cfg.actualSampleRate} target=${cfg.targetSampleRate} chunk=${cfg.chunkSamples}@${cfg.chunkMs}ms`);

      node.port.onmessage = (event) => {
        const float32 = event.data;
        if (!(float32 instanceof Float32Array)) return;

        if (wsStatusRef && wsStatusRef.current && wsStatusRef.current !== "connected" && wsStatusRef.current !== "listening") {
          console.debug("[audio] dropped_chunk_backpressure ws=", wsStatusRef.current);
          return;
        }

        let chunk = float32;
        if (cfg.needsResample) {
          chunk = resampleLinear(float32, cfg.actualSampleRate, cfg.targetSampleRate);
        }

        const acc = accumulatorRef.current;
        acc.push(chunk);
        accumulatorLenRef.current += chunk.length;

        let totalLen = accumulatorLenRef.current;
        while (totalLen >= CHUNK_SAMPLES) {
          const out = new Float32Array(CHUNK_SAMPLES);
          let offset = 0;
          let remaining = CHUNK_SAMPLES;
          while (remaining > 0) {
            const first = acc[0];
            if (!first) break;
            if (first.length <= remaining) {
              out.set(first, offset);
              offset += first.length;
              remaining -= first.length;
              acc.shift();
            } else {
              out.set(first.subarray(0, remaining), offset);
              acc[0] = first.subarray(remaining);
              offset += remaining;
              remaining = 0;
            }
          }
          accumulatorLenRef.current = totalLen - CHUNK_SAMPLES;
          totalLen = accumulatorLenRef.current;

          const pcm16 = floatTo16BitPCM(out);
          const buf = pcm16.buffer;
          if (onChunk) onChunk(buf);
        }
      };

      stream.getTracks().forEach((track) => {
        track.onended = () => {
          console.log("[audio] track ended");
        };
      });

      setMicStatus("active");
    },
    [micStatus, resetAccumulator]
  );

  return {
    micStatus,
    error,
    startRecording,
    stopRecording,
    getAudioConfig: () => (ctxRef.current ? getAudioConfig(ctxRef.current) : getAudioConfig(null)),
  };
}
