#!/usr/bin/env python3
"""Concurrent WS load harness — P10-PERF-004.

Spawn N WS clients feeding same fixture at 60ms cadence,
collect per-segment latency p50/p95 and resource hints.
"""

from __future__ import annotations

import argparse
import asyncio
import pathlib
import statistics
import time

import websockets


async def _run_client(url: str, pcm_path: pathlib.Path, source: str, target: str) -> dict:
    latencies: list[float] = []
    try:
        async with websockets.connect(url) as ws:
            await ws.send(f'{{"type":"start","source_language":"{source}","target_language":"{target}"}}')
            # wait for session.ready
            try:
                await asyncio.wait_for(ws.recv(), timeout=5)
            except asyncio.TimeoutError:
                return {"error": "no session.ready"}

            data = pcm_path.read_bytes()
            chunk = 1920  # 60ms @16k S16LE
            t0 = time.monotonic()
            for i in range(0, min(len(data), chunk * 80), chunk):
                await ws.send(data[i : i + chunk])
                await asyncio.sleep(0.06)
                # try to collect translation events with short timeout
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=0.05)
                    if '"type":"translation"' in msg:
                        latencies.append((time.monotonic() - t0) * 1000)
                except asyncio.TimeoutError:
                    pass
            await ws.send('{"type":"stop"}')
            try:
                await asyncio.wait_for(ws.recv(), timeout=2)
            except asyncio.TimeoutError:
                pass
    except Exception as e:
        return {"error": str(e), "latencies": latencies}
    return {"latencies": latencies}


async def main() -> None:
    parser = argparse.ArgumentParser(description="WS load harness P10-PERF-004")
    parser.add_argument("--n", type=int, default=5, help="concurrent clients")
    parser.add_argument("--url", default="ws://localhost:8000/ws/v1/translate")
    parser.add_argument("--fixture", default="backend/tests/fixtures/hello_16k.pcm")
    parser.add_argument("--source", default="en")
    parser.add_argument("--target", default="hi")
    parser.add_argument("--pipeline", default="cascaded")
    args = parser.parse_args()

    pcm = pathlib.Path(args.fixture)
    if not pcm.exists():
        # try relative to repo root
        pcm = pathlib.Path(__file__).parent.parent / "tests/fixtures/hello_16k.pcm"
    print(f"load harness n={args.n} pipeline={args.pipeline} fixture={pcm} url={args.url}")

    start = time.monotonic()
    results = await asyncio.gather(*[_run_client(args.url, pcm, args.source, args.target) for _ in range(args.n)])
    elapsed = time.monotonic() - start
    all_lats: list[float] = []
    for r in results:
        all_lats.extend(r.get("latencies", []))
    if all_lats:
        all_lats.sort()
        p50 = statistics.median(all_lats)
        p95_idx = int(0.95 * len(all_lats))
        p95 = all_lats[min(p95_idx, len(all_lats) - 1)]
        avg = sum(all_lats) / len(all_lats)
        print(f"sessions={args.n} events={len(all_lats)} elapsed={elapsed:.2f}s")
        print(f"latency p50={p50:.1f}ms p95={p95:.1f}ms avg={avg:.1f}ms max={max(all_lats):.1f}ms")
    else:
        print("no latencies collected (mock pipeline may not emit translation without STT)")
        print(f"results={results}")
    # summary for benchmark doc
    print("harness_done")


if __name__ == "__main__":
    asyncio.run(main())
