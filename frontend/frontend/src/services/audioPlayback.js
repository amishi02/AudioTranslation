/**
 * audioPlayback — Phase 9 frontend audio output via AudioContext.
 * Handles WAV decode and queued playback with cancellation on session end.
 */

let audioCtx = null;
let currentSource = null;
let isMuted = false;
const queue = [];

function getContext(sampleRate) {
  if (!audioCtx || audioCtx.state === "closed") {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    audioCtx = new Ctx({ sampleRate: sampleRate || 22050 });
  }
  if (audioCtx.state === "suspended") audioCtx.resume();
  return audioCtx;
}

export function setMuted(muted) {
  isMuted = muted;
  if (muted && currentSource) {
    try {
      currentSource.stop();
    } catch (_err) {
      void _err;
    }
    currentSource = null;
    queue.length = 0;
  }
}

export function isAudioMuted() {
  return isMuted;
}

export async function playAudioBuffer(arrayBuffer, sampleRate) {
  if (isMuted) return;
  // Queue if currently playing
  if (currentSource) {
    queue.push({ arrayBuffer, sampleRate });
    return;
  }
  await _playNow(arrayBuffer, sampleRate);
}

async function _playNow(arrayBuffer, sampleRate) {
  if (isMuted) return;
  const ctx = getContext(sampleRate);
  try {
    // Clone buffer because decodeAudioData detaches
    const copy = arrayBuffer.slice(0);
    const audioBuf = await ctx.decodeAudioData(copy);
    const source = ctx.createBufferSource();
    source.buffer = audioBuf;
    source.connect(ctx.destination);
    currentSource = source;
    source.onended = () => {
      currentSource = null;
      if (queue.length > 0 && !isMuted) {
        const next = queue.shift();
        _playNow(next.arrayBuffer, next.sampleRate);
      }
    };
    source.start(0);
  } catch (_e) {
    void _e;
    // Fallback: try createBuffer manual for raw PCM if decode fails
    currentSource = null;
    if (queue.length > 0) {
      const next = queue.shift();
      _playNow(next.arrayBuffer, next.sampleRate);
    }
  }
}

export function stopPlayback() {
  if (currentSource) {
    try {
      currentSource.stop();
    } catch (_err) {
      void _err;
    }
    currentSource = null;
  }
  queue.length = 0;
  // Do not close context — reuse for next segment
  // P10-FE-003: handle audio.output.start with no bytes gracefully — if queue empty, just clear pending start
  pendingStart = null;
}

let pendingStart = null;

export function handleStartEvent(ev) {
  // P10-FE-003: if start arrives with no following bytes, timeout to avoid infinite wait
  pendingStart = ev;
  // auto-clear if no bytes in 5s
  setTimeout(() => {
    if (pendingStart === ev) pendingStart = null;
  }, 5000);
}

export function getPendingStart() {
  return pendingStart;
}

export function getQueueLength() {
  return queue.length + (currentSource ? 1 : 0);
}

export function _resetForTest() {
  stopPlayback();
  if (audioCtx) {
    try {
      audioCtx.close();
    } catch (_err) {
      void _err;
    }
    audioCtx = null;
  }
  isMuted = false;
}
