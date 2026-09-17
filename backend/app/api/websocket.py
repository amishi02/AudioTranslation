"""WebSocket gateway — P4-WS-001..013."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.models.session import TranslationSession
from app.schemas.websocket import (
    ErrorEvent,
    SessionEndedEvent,
    SessionReadyEvent,
    SessionStart,
    SessionStop,
)
from app.services.session_service import session_service

logger = logging.getLogger(__name__)

router = APIRouter()


async def _send_error(websocket: WebSocket, code: str, message: str) -> None:
    err = ErrorEvent(code=code, message=message)
    await websocket.send_json(err.model_dump())


async def _processor_loop(session: TranslationSession, websocket: WebSocket) -> None:
    """Phase 6: audio_queue -> pipeline -> normalized events -> WS."""
    try:
        while True:
            pcm: bytes = await session.audio_queue.get()
            pipeline = session.pipeline
            if pipeline is None:
                continue
            try:
                # Whisper inference is much slower than 60 ms audio chunks on
                # CPU. Drain queued chunks before polling so one inference
                # processes the accumulated audio instead of falling behind.
                queued = [pcm]
                while True:
                    try:
                        queued.append(session.audio_queue.get_nowait())
                    except asyncio.QueueEmpty:
                        break
                for queued_pcm in queued:
                    await pipeline.push_audio(  # type: ignore[attr-defined]
                        session.session_id, queued_pcm
                    )
                events = await pipeline.poll_events(session.session_id)  # type: ignore[attr-defined]
                for ev in events:
                    try:
                        await websocket.send_json(ev)
                    except Exception:
                        # WS may be closed
                        return
            except Exception as exc:
                # Map model errors to error event
                code = getattr(exc, "code", "MODEL_ERROR")
                msg = str(exc)
                try:
                    await websocket.send_json(
                        {"type": "error", "code": code, "message": msg}
                    )
                except Exception:
                    return
    except asyncio.CancelledError:
        return


@router.websocket(settings.ws_v1_path)
async def translate_ws(websocket: WebSocket) -> None:
    """Thin gateway — validates, delegates to SessionService, manages lifecycle."""
    await websocket.accept()
    logger.info("websocket_connected path=/ws/v1/translate")
    # Per-connection session_id (None until start)
    current_session_id: str | None = None
    processor_task: asyncio.Task[None] | None = None

    try:
        while True:
            try:
                msg = await websocket.receive()
            except WebSocketDisconnect:
                break
            except RuntimeError as exc:
                # Starlette raises after disconnect — treat as normal close
                if "Cannot call" in str(exc):
                    break
                logger.exception("websocket_receive_error: %s", exc)
                break
            except Exception as exc:  # pragma: no cover
                logger.exception("websocket_receive_error: %s", exc)
                break

            # Handle text (JSON control) vs bytes (audio)
            if "text" in msg and msg["text"] is not None:
                raw_text: str = msg["text"]
                # Payload limit P4-WS-013
                if len(raw_text.encode("utf-8")) > settings.max_json_bytes:
                    await _send_error(websocket, "INVALID_MESSAGE", "Message too large")
                    continue
                # Parse JSON
                try:
                    data = json.loads(raw_text)
                except json.JSONDecodeError:
                    await _send_error(
                        websocket, "INVALID_MESSAGE", "Invalid JSON frame"
                    )
                    continue

                msg_type = data.get("type")
                if msg_type == "start":
                    # Validate via Pydantic
                    try:
                        start = SessionStart.model_validate(data)
                    except Exception as e:
                        await _send_error(
                            websocket,
                            "INVALID_SESSION_CONFIG",
                            f"Invalid session config: {e}",
                        )
                        continue
                    # Already have session?
                    if current_session_id is not None:
                        await _send_error(
                            websocket, "SESSION_ERROR", "Session already started"
                        )
                        continue
                    session_id = uuid.uuid4().hex[:12]
                    try:
                        session = await session_service.create_session(
                            session_id,
                            start.source_language,
                            start.target_language,
                            websocket,
                        )
                    except ValueError as ve:
                        msg_str = str(ve)
                        # Extract code prefix if present
                        if "UNSUPPORTED_LANGUAGE" in msg_str:
                            code = "UNSUPPORTED_LANGUAGE"
                        elif "INVALID_SESSION_CONFIG" in msg_str:
                            code = "INVALID_SESSION_CONFIG"
                        else:
                            code = "SESSION_ERROR"
                        # Clean message after colon
                        clean = (
                            msg_str.split(":", 1)[-1].strip()
                            if ":" in msg_str
                            else msg_str
                        )
                        await _send_error(websocket, code, clean)
                        continue
                    current_session_id = session_id
                    # Start processor task (Phase 6: pipeline)
                    session.processor_task = asyncio.create_task(
                        _processor_loop(session, websocket)
                    )
                    processor_task = session.processor_task
                    # Emit session.ready
                    ready = SessionReadyEvent(
                        session_id=session_id,
                        source_language=start.source_language,
                        target_language=start.target_language,
                    )
                    await websocket.send_json(ready.model_dump())
                elif msg_type == "stop":
                    try:
                        SessionStop.model_validate(data)
                    except Exception:
                        await _send_error(
                            websocket, "INVALID_MESSAGE", "Invalid stop message"
                        )
                        continue
                    if current_session_id is None:
                        await _send_error(
                            websocket, "SESSION_ERROR", "No active session"
                        )
                        continue
                    sid = current_session_id
                    await session_service.end_session(sid)
                    # Cancel processor task
                    if processor_task is not None and not processor_task.done():
                        processor_task.cancel()
                        try:
                            await processor_task
                        except asyncio.CancelledError:
                            pass
                    ended = SessionEndedEvent(session_id=sid)
                    try:
                        await websocket.send_json(ended.model_dump())
                    except Exception:
                        pass
                    current_session_id = None
                    processor_task = None
                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                else:
                    await _send_error(
                        websocket,
                        "INVALID_MESSAGE",
                        f"Unknown message type: {msg_type}",
                    )

            elif "bytes" in msg and msg["bytes"] is not None:
                frame: bytes = msg["bytes"]
                # Validation P4-WS-013 / P5-BE-001
                if current_session_id is None:
                    await _send_error(
                        websocket, "SESSION_ERROR", "No active session for audio"
                    )
                    continue
                if len(frame) == 0:
                    await _send_error(
                        websocket, "INVALID_AUDIO_DATA", "Empty audio frame"
                    )
                    continue
                if len(frame) % 2 != 0:
                    await _send_error(
                        websocket,
                        "INVALID_AUDIO_DATA",
                        "Audio frame must be even length (S16LE)",
                    )
                    continue
                if len(frame) > settings.max_audio_frame_bytes:
                    await _send_error(
                        websocket, "INVALID_AUDIO_DATA", "Audio frame too large"
                    )
                    continue
                if (
                    len(frame) < 320
                ):  # 10ms @16k S16LE ~320 bytes — treat too small as invalid? but allow
                    pass
                assert current_session_id is not None
                session_opt = await session_service.get_session(current_session_id)
                if session_opt is None:
                    await _send_error(websocket, "SESSION_ERROR", "Session not found")
                    continue
                # Enqueue with backpressure + queue depth (P4-WS-010, P5-BE-003)
                # Log every chunk (INFO) for user visibility: 60ms/960 samples/1920 bytes S16LE mono 16k
                logger.debug(
                    "ws audio chunk session_id=%s bytes=%s qsize_before=%s total_frames=%s (chunk=%s ms, %s samples, %s bytes)",
                    current_session_id[:8] if current_session_id else "unknown",
                    len(frame),
                    session_opt.audio_queue.qsize(),
                    session_opt.frames_received + 1,
                    60,
                    960,
                    1920,
                )
                try:
                    session_opt.audio_queue.put_nowait(frame)
                    session_opt.frames_received += 1
                    session_opt.bytes_received += len(frame)
                    session_opt.last_frame_at = time.time()
                    if session_opt.frames_received % 20 == 0:
                        logger.debug(
                            "audio_queue qsize=%s frames=%s bytes=%s session_id=%s",
                            session_opt.audio_queue.qsize(),
                            session_opt.frames_received,
                            session_opt.bytes_received,
                            current_session_id,
                        )
                except asyncio.QueueFull:
                    # Drop oldest to keep latency low (circular), don't spam frontend with RATE_LIMITED
                    try:
                        session_opt.audio_queue.get_nowait()
                        session_opt.dropped_frames += 1
                    except asyncio.QueueEmpty:
                        pass
                    try:
                        session_opt.audio_queue.put_nowait(frame)
                        session_opt.frames_received += 1
                        session_opt.bytes_received += len(frame)
                        session_opt.last_frame_at = time.time()
                    except asyncio.QueueFull:
                        pass
                    logger.debug(
                        "audio_queue full (circular) dropped_frames=%s qsize=%s session_id=%s",
                        session_opt.dropped_frames,
                        session_opt.audio_queue.qsize(),
                        current_session_id,
                    )
                    # Not sending RATE_LIMITED to frontend — keep UI as Listening, not error
                    continue
            else:
                # Unknown message form
                await _send_error(
                    websocket, "INVALID_MESSAGE", "Invalid WebSocket frame"
                )

    except WebSocketDisconnect:
        logger.info("websocket_disconnected")
    finally:
        # Cleanup P4-WS-012
        if current_session_id is not None:
            await session_service.end_session(current_session_id)
            if processor_task is not None and not processor_task.done():
                processor_task.cancel()
                try:
                    await processor_task
                except asyncio.CancelledError:
                    pass
        else:
            # Also try cleanup via ws index
            await session_service.cleanup_on_disconnect(websocket)
        # Ensure processor task cancelled
        logger.info("websocket_closed")
