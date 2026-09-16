/**
 * P5-TEST-001..003: audio helpers — PCM, chunking, mono.
 */
import { describe, it, expect } from "vitest";
import {
  CHUNK_BYTES,
  CHUNK_SAMPLES,
  createChunkAccumulator,
  floatTo16BitPCM,
  resampleLinear,
  toMono,
} from "../services/audio.js";

describe("audio helpers", () => {
  it("P5-TEST-001: floatTo16BitPCM clamps and converts", () => {
    const input = new Float32Array([0, 1, -1, 0.5, -0.5, 2, -2]);
    const out = floatTo16BitPCM(input);
    // 0 -> 0, 1 -> 32767, -1 -> -32768, 0.5 -> 16383, -0.5 -> -16384, 2 clamped to 32767, -2 to -32768
    expect(out[0]).toBe(0);
    expect(out[1]).toBe(32767);
    expect(out[2]).toBe(-32768);
    expect(out[3]).toBe(16383);
    expect(out[4]).toBe(-16384);
    expect(out[5]).toBe(32767);
    expect(out[6]).toBe(-32768);
    // Little-endian bytes check: first sample 0 => bytes 0x00 0x00
    const bytes = new Uint8Array(out.buffer);
    expect(bytes[0]).toBe(0);
    expect(bytes[1]).toBe(0);
    // Second sample 32767 => 0xFF 0x7F little-endian
    expect(bytes[2]).toBe(0xff);
    expect(bytes[3]).toBe(0x7f);
  });

  it("P5-TEST-002: chunking helper exact CHUNK_SAMPLES", () => {
    const chunks = [];
    const acc = createChunkAccumulator((buf) => chunks.push(buf));
    // Push 3 arbitrary-sized slices that sum to 2*CHUNK_SAMPLES + remainder
    const a = new Float32Array(400);
    const b = new Float32Array(600);
    const c = new Float32Array(1000); // total 2000
    a.fill(0.1);
    b.fill(0.2);
    c.fill(0.3);
    acc.push(a);
    acc.push(b);
    acc.push(c);
    // Should have emitted floor(2000/960)=2 chunks
    expect(chunks.length).toBe(2);
    expect(chunks[0].byteLength).toBe(CHUNK_BYTES);
    expect(chunks[1].byteLength).toBe(CHUNK_BYTES);
    // Remainder 80 samples
    expect(acc.getAccumulatedLength()).toBe(2000 - 2 * CHUNK_SAMPLES);
  });

  it("P5-TEST-002: chunking with exact boundary", () => {
    const chunks = [];
    const acc = createChunkAccumulator((buf) => chunks.push(buf));
    const exact = new Float32Array(CHUNK_SAMPLES);
    acc.push(exact);
    expect(chunks.length).toBe(1);
    acc.push(new Float32Array(CHUNK_SAMPLES));
    expect(chunks.length).toBe(2);
  });

  it("P5-TEST-003: mono conversion is identity for channel 0", () => {
    const ch0 = new Float32Array([0.1, 0.2, 0.3]);
    const mono = toMono(ch0);
    expect(mono).toBe(ch0);
    expect(mono.length).toBe(3);
  });

  it("resampleLinear identity when rates equal", () => {
    const input = new Float32Array([0.1, 0.2, 0.3]);
    const out = resampleLinear(input, 16000, 16000);
    expect(out).toBe(input);
  });

  it("resampleLinear 48k->16k reduces length", () => {
    const input = new Float32Array(480);
    const out = resampleLinear(input, 48000, 16000);
    expect(out.length).toBe(160);
  });
});
