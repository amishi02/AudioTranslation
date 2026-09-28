"""P10-TEST-004: perf instrumentation + frontend edge cases."""

import time

from app.services.event_normalizer import normalize_transcript, normalize_translation
from app.services.metrics import get_metrics, reset_metrics, record_latency


def test_normalize_transcript_has_timestamp():
    raw = {"segment_id": 1, "text": "hello", "is_final": False, "session_id": "abc"}
    ev = normalize_transcript(raw, "abc")
    assert ev.timestamp > 0
    assert ev.status == "partial"


def test_normalize_translation_has_timestamp():
    raw = {"segment_id": 2, "source_text": "hi", "translated_text": "नमस्ते", "is_final": True}
    ev = normalize_translation(raw, "abc")
    assert ev.timestamp > 0
    assert ev.status == "final"


def test_metrics_latency_record():
    reset_metrics()
    record_latency(stt_ms=100, translation_ms=20, total_ms=120)
    snap = get_metrics().snapshot()
    assert snap["avg_stt_latency_ms"] == 100
    assert snap["avg_total_latency_ms"] == 120


def test_no_audio_leak_in_logs():
    """P10-SEC-004: ensure providers don't log raw PCM hex."""
    import pathlib

    root = pathlib.Path(__file__).parent.parent
    for p in (root / "app/providers").rglob("*.py"):
        text = p.read_text()
        assert "frame_bytes.hex()" not in text
        assert ".hex()" not in text or "etag" in text  # allow only etag hex
