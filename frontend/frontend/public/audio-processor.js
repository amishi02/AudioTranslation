/* global AudioWorkletProcessor, registerProcessor */
/**
 * AudioWorkletProcessor — captures mic input channel 0 and forwards Float32 slices.
 * Keep worklet minimal; PCM conversion + chunking happen on main thread.
 * See src/services/audio.js for why PCM S16LE mono 16kHz is required.
 */
class AudioProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0];
    if (input && input[0] && input[0].length > 0) {
      // Copy channel 0 slice (mono conversion: channel 0 only, see audio.js)
      const ch0 = input[0];
      // Use slice(0) to copy; transfer via postMessage (clones)
      this.port.postMessage(ch0.slice(0));
    }
    return true;
  }
}

registerProcessor("audio-processor", AudioProcessor);
