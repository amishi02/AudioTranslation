"""P6-TEST-001: EventNormalizer."""

from app.services.event_normalizer import normalize_transcript, normalize_translation, normalize_unified


def test_normalize_transcript_partial():
    raw = {"segment_id": 1, "text": "Hello", "is_final": False, "session_id": "s1"}
    ev = normalize_transcript(raw, "s1")
    assert ev.type == "transcript"
    assert ev.segment_id == 1
    assert ev.status == "partial"
    assert ev.text == "Hello"


def test_normalize_transcript_final():
    raw = {"segment_id": 2, "text": "Hello world", "is_final": True}
    ev = normalize_transcript(raw, "s2")
    assert ev.status == "final"
    assert ev.segment_id == 2


def test_normalize_translation():
    raw = {"segment_id": 1, "source_text": "Hello", "translated_text": "[hi] Hello", "is_final": False}
    ev = normalize_translation(raw, "s1")
    assert ev.type == "translation"
    assert ev.source_text == "Hello"
    assert ev.translated_text == "[hi] Hello"
    assert ev.status == "partial"


def test_normalize_unified():
    raw = {"segment_id": 1, "source_text": "Hello", "translated_text": "[hi] Hello", "is_final": True}
    tr, tl = normalize_unified(raw, "s1")
    assert tr.type == "transcript"
    assert tl.type == "translation"
    assert tr.status == "final"
    assert tl.status == "final"
