"""Metrics aggregation — P10-PERF-003."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class MetricsSnapshot:
    sessions_started: int = 0
    sessions_ended: int = 0
    frames_received: int = 0
    dropped_frames: int = 0
    queue_depth_max: int = 0
    rate_limited_events: int = 0
    timeouts: int = 0
    # latency samples (ms) — keep last 256 for p50/p95
    stt_latencies: deque[float] = field(default_factory=lambda: deque(maxlen=256))
    translation_latencies: deque[float] = field(
        default_factory=lambda: deque(maxlen=256)
    )
    total_latencies: deque[float] = field(default_factory=lambda: deque(maxlen=256))

    def snapshot(self) -> dict:
        def _p(lst: deque[float], q: float) -> float | None:
            if not lst:
                return None
            s = sorted(lst)
            idx = int(q * len(s))
            idx = min(idx, len(s) - 1)
            return round(s[idx], 2)

        def _avg(lst: deque[float]) -> float | None:
            if not lst:
                return None
            return round(sum(lst) / len(lst), 2)

        return {
            "sessions_started": self.sessions_started,
            "sessions_ended": self.sessions_ended,
            "frames_received": self.frames_received,
            "dropped_frames": self.dropped_frames,
            "queue_depth_max": self.queue_depth_max,
            "rate_limited_events": self.rate_limited_events,
            "timeouts": self.timeouts,
            "avg_stt_latency_ms": _avg(self.stt_latencies),
            "avg_translation_latency_ms": _avg(self.translation_latencies),
            "avg_total_latency_ms": _avg(self.total_latencies),
            "p50_total_ms": _p(self.total_latencies, 0.5),
            "p95_total_ms": _p(self.total_latencies, 0.95),
            "timestamp": time.time(),
        }


_metrics = MetricsSnapshot()


def get_metrics() -> MetricsSnapshot:
    return _metrics


def record_session_started() -> None:
    _metrics.sessions_started += 1


def record_session_ended() -> None:
    _metrics.sessions_ended += 1


def record_frames(n: int = 1) -> None:
    _metrics.frames_received += n


def record_dropped(n: int = 1) -> None:
    _metrics.dropped_frames += n


def record_rate_limited() -> None:
    _metrics.rate_limited_events += 1


def record_timeout() -> None:
    _metrics.timeouts += 1


def record_queue_depth(depth: int) -> None:
    if depth > _metrics.queue_depth_max:
        _metrics.queue_depth_max = depth


def record_latency(
    stt_ms: float | None = None,
    translation_ms: float | None = None,
    total_ms: float | None = None,
) -> None:
    if stt_ms is not None:
        _metrics.stt_latencies.append(stt_ms)
    if translation_ms is not None:
        _metrics.translation_latencies.append(translation_ms)
    if total_ms is not None:
        _metrics.total_latencies.append(total_ms)


def reset_metrics() -> None:
    global _metrics
    _metrics = MetricsSnapshot()
