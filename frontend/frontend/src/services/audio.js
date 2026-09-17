/**
 * Audio helpers — microphone, AudioContext/AudioWorklet, PCM conversion, chunking.
 *
 * Why each transformation is required:
 * - PCM S16LE: models (Whisper, etc.) expect raw PCM, not Opus/WebM. S16LE is
 *   the de-facto local model input (int16 little-endian).
 * - Mono: most STT models are trained on mono; stereo doubles data and
 *   confuses the model. We take channel 0 (documented tradeoff: mixing would
 *   be more faithful for stereo mics but channel 0 is sufficient and cheapest).
 * - 16 kHz: Whisper and many STT models are trained at 16k. 48k hardware
 *   rate would waste bandwidth and require model to resample internally.
 *   We request 16k and resample on main thread if hardware ignores the hint.
 * - Chunking ~60 ms (960 samples @16k → 1920 bytes): balances latency vs
 *   WebSocket overhead. ~20 ms is too chatty (high overhead), ~100 ms+ adds
 *   noticeable lag. 60 ms is benchmark-tunable later.
 *
 * If a future model needs a different format, only floatTo16BitPCM / chunk
 * constants and AUDIO_* env need to change — WS and pipeline stay untouched.
 */

export const AUDIO_TARGET_SAMPLE_RATE = 16000;
export const AUDIO_CHANNELS = 1;
export const AUDIO_CHUNK_MS = 60;
export const AUDIO_FORMAT = "pcm_s16le";

export const CHUNK_SAMPLES = Math.floor((AUDIO_TARGET_SAMPLE_RATE * AUDIO_CHUNK_MS) / 1000); // 960
export const CHUNK_BYTES = CHUNK_SAMPLES * 2; // S16LE 2 bytes per sample

export class MicPermissionDenied extends Error {
  constructor(message = "Microphone permission denied") {
    super(message);
    this.name = "MicPermissionDenied";
    this.code = "PERMISSION_DENIED";
  }
}

export class MicNotFound extends Error {
  constructor(message = "Microphone not found") {
    super(message);
    this.name = "MicNotFound";
    this.code = "NOT_FOUND";
  }
}

/**
 * Request microphone with echoCancellation + noiseSuppression.
 * See TRD §7 for why these are enabled (reduce background noise for STT).
 */
export async function requestMicrophone() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    throw new MicNotFound("getUserMedia not supported in this browser");
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: AUDIO_CHANNELS,
        sampleRate: AUDIO_TARGET_SAMPLE_RATE,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    return stream;
  } catch (e) {
    const name = e?.name || "";
    if (name === "NotAllowedError" || name === "PermissionDeniedError") {
      throw new MicPermissionDenied(e.message);
    }
    if (name === "NotFoundError" || name === "DevicesNotFoundError") {
      throw new MicNotFound(e.message);
    }
    throw e;
  }
}

export function createAudioContext(targetRate = AUDIO_TARGET_SAMPLE_RATE) {
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) throw new Error("AudioContext not supported");
  // Some browsers ignore sampleRate hint — we detect actual rate after creation
  try {
    return new Ctx({ sampleRate: targetRate });
  } catch {
    return new Ctx();
  }
}

export async function attachWorklet(audioContext) {
  // public/audio-processor.js is served statically; Vite does not bundle it
  const url = "/audio-processor.js";
  try {
    await audioContext.audioWorklet.addModule(url);
  } catch (e) {
    // Fallback error for unsupported browsers
    throw new Error(`AudioWorklet not supported: ${e.message}`, { cause: e });
  }
}

/**
 * Float32 [-1,1] → Int16 [-32768,32767] clamping.
 * Returns Int16Array (view) — caller should use .buffer for ArrayBuffer.
 */
export function floatTo16BitPCM(float32) {
  const len = float32.length;
  const out = new Int16Array(len);
  for (let i = 0; i < len; i++) {
    let s = float32[i];
    // Clamp
    if (s > 1) s = 1;
    else if (s < -1) s = -1;
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
}

/**
 * Simple linear resampler for 48k → 16k etc.
 * For Phase 5, linear is sufficient; heavy polyphase is deferred until
 * benchmark shows quality loss. Document tradeoff: linear is cheap but
 * introduces mild aliasing vs proper low-pass.
 *
 * @param {Float32Array} input - at inputRate
 * @param {number} inputRate - e.g., 48000
 * @param {number} targetRate - e.g., 16000
 * @returns {Float32Array} resampled
 */
export function resampleLinear(input, inputRate, targetRate) {
  if (inputRate === targetRate) return input;
  const ratio = inputRate / targetRate;
  const outputLength = Math.floor(input.length / ratio);
  const output = new Float32Array(outputLength);
  for (let i = 0; i < outputLength; i++) {
    const srcIndex = i * ratio;
    const left = Math.floor(srcIndex);
    const right = Math.min(left + 1, input.length - 1);
    const frac = srcIndex - left;
    output[i] = input[left] * (1 - frac) + input[right] * frac;
  }
  return output;
}

/**
 * Mono conversion — channel 0 only (see header comment).
 * If stereo input is [left, right] interleaved or as two arrays, we take left.
 */
export function toMono(channelData) {
  // channelData is Float32Array of channel 0 already from worklet
  return channelData;
}

export function getAudioConfig(audioContext) {
  const actualRate = audioContext ? audioContext.sampleRate : AUDIO_TARGET_SAMPLE_RATE;
  return {
    targetSampleRate: AUDIO_TARGET_SAMPLE_RATE,
    actualSampleRate: actualRate,
    channelCount: AUDIO_CHANNELS,
    chunkMs: AUDIO_CHUNK_MS,
    chunkSamples: CHUNK_SAMPLES,
    chunkBytes: CHUNK_BYTES,
    format: AUDIO_FORMAT,
    needsResample: actualRate !== AUDIO_TARGET_SAMPLE_RATE,
  };
}

/**
 * Chunk accumulator helper for testing — buffers Float32 slices
 * until CHUNK_SAMPLES, converts to PCM and calls onChunk.
 * See P5-AUDIO-007.
 */
export function createChunkAccumulator(onChunk) {
  let acc = [];
  let accLen = 0;

  function push(float32) {
    acc.push(float32);
    accLen += float32.length;
    let totalLen = accLen;
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
      accLen = totalLen - CHUNK_SAMPLES;
      totalLen = accLen;
      const pcm16 = floatTo16BitPCM(out);
      onChunk(pcm16.buffer);
    }
  }

  function reset() {
    acc = [];
    accLen = 0;
  }

  function getAccumulatedLength() {
    return accLen;
  }

  return { push, reset, getAccumulatedLength };
}
