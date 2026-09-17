"""Event normalizer — converts provider raw dicts to normalized events."""

from __future__ import annotations

import time

from app.schemas.events import TranscriptEvent, TranslationEvent


def normalize_transcript(raw: dict, session_id: str) -> TranscriptEvent:
    """Normalize STT raw -> TranscriptEvent."""
    # Raw shapes: {"session_id":..., "segment_id":1, "text":"Hello", "is_final":False}
    # Also supports {"partial_text":"Hello"} legacy
    text = raw.get("text") or raw.get("partial_text") or raw.get("value") or ""
    seg = int(raw.get("segment_id") or raw.get("segmentId") or 1)
    is_final = bool(raw.get("is_final") or raw.get("final") or False)
    status = "final" if is_final else "partial"
    sid = raw.get("session_id") or session_id
    return TranscriptEvent(
        session_id=sid,
        segment_id=seg,
        status=status,
        text=text,
        timestamp=time.time(),
    )


def normalize_translation(raw: dict, session_id: str) -> TranslationEvent:
    """Normalize translation raw -> TranslationEvent."""
    # Raw shapes: {"source_text":"Hello", "translated_text":"...", "segment_id":1, "is_final":...}
    src = raw.get("source_text") or raw.get("sourceText") or raw.get("text") or ""
    tgt = raw.get("translated_text") or raw.get("translatedText") or raw.get("translation") or ""
    seg = int(raw.get("segment_id") or 1)
    is_final = bool(raw.get("is_final") or False)
    status = "final" if is_final else "partial"
    sid = raw.get("session_id") or session_id
    return TranslationEvent(
        session_id=sid,
        segment_id=seg,
        status=status,
        source_text=src,
        translated_text=tgt,
        timestamp=time.time(),
    )


def normalize_unified(raw: dict, session_id: str) -> tuple[TranscriptEvent, TranslationEvent]:
    """Normalize unified raw -> (transcript, translation) pair."""
    # Unified mock returns {"source_text","translated_text","segment_id","is_final"}
    src = raw.get("source_text") or ""
    tgt = raw.get("translated_text") or ""
    seg = int(raw.get("segment_id") or 1)
    is_final = bool(raw.get("is_final") or False)
    status = "final" if is_final else "partial"
    sid = raw.get("session_id") or session_id
    ts = time.time()
    tr = TranscriptEvent(session_id=sid, segment_id=seg, status=status, text=src, timestamp=ts)
    tl = TranslationEvent(session_id=sid, segment_id=seg, status=status, source_text=src, translated_text=tgt, timestamp=ts)
    return tr, tl
