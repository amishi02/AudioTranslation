"""WebSocket gateway — P4-WS-001..013, P10 hardening."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections import deque

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.models.session import TranslationSession
from app.schemas.errors import ERROR_RETRYABLE, ErrorCode
from app.schemas.websocket import (
    ErrorEvent,
    SessionEndedEvent,
    SessionReadyEvent,
    SessionStart,
    SessionStop,
)
from app.services.metrics import (
    record_dropped,
    record_frames,
    record_latency,
    record_queue_depth,
    record_rate_limited,
    record_session_ended,
    record_session_started,
    record_timeout,
)
from app.services.session_service import session_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _safe_code(code: str) -> str:
    try:
        return ErrorCode(code).value
    except Exception:
        # allow unknown but restrict to known set; fallback to INTERNAL_ERROR
        if code in {c.value for c in ErrorCode}:
            return code
        return ErrorCode.INTERNAL_ERROR.value


async def _send_error(
    websocket: WebSocket, code: str, message: str, session_id: str | None = None
) -> None:
    safe = _safe_code(code)
    # Never leak raw exception / stack — message is already sanitized by caller
    retryable = ERROR_RETRYABLE.get(safe, False)
    err = ErrorEvent(
        code=safe,
        message=message,
        retryable=retryable,
        session_id=session_id,
        timestamp=time.time(),
    )
    try:
        await websocket.send_json(err.model_dump())
    except Exception:
        pass
    # structured log with code/session
    logger.info(
        "ws_error code=%s retryable=%s session_id=%s msg=%s",
        safe,
        retryable,
        (session_id or "")[:8],
        message,
    )


async def _processor_loop(session: TranslationSession, websocket: WebSocket) -> None:
    """Phase 6/10: audio_queue -> pipeline -> normalized events -> WS with perf instrumentation."""
    audio_task: asyncio.Task[bytes] | None = None
    inference_task: asyncio.Task[list[dict | bytes]] | None = None
    audio_since_inference = False
    try:
        audio_task = asyncio.create_task(session.audio_queue.get())
        while True:
            pipeline = session.pipeline
            if pipeline is None:
                await asyncio.sleep(0)
                continue

            wait_tasks: set[asyncio.Task[object]] = {audio_task}
            if inference_task is not None:
                wait_tasks.add(inference_task)
            done, _ = await asyncio.wait(
                wait_tasks, return_when=asyncio.FIRST_COMPLETED
            )

            if audio_task in done:
                pcm = audio_task.result()
                # T1 capture — WS receive timestamp for perf (P10-PERF-001)
                t1 = time.monotonic()
                session.last_frame_at = time.time()
                audio_task = asyncio.create_task(session.audio_queue.get())
                await pipeline.push_audio(session.session_id, pcm)  # type: ignore[attr-defined]
                audio_since_inference = True
                if inference_task is None:
                    # Annotate session for latency correlation
                    session._last_t1 = t1  # type: ignore[attr-defined]
                    inference_task = asyncio.create_task(
                        pipeline.poll_events(session.session_id)
                    )  # type: ignore[attr-defined]

            if inference_task is not None and inference_task in done:
                t2 = time.monotonic()
                events = inference_task.result()
                inference_task = None
                # latency breakdown
                t1_val = getattr(session, "_last_t1", None)
                if t1_val is not None:
                    total_ms = (t2 - t1_val) * 1000
                    # queue depth at poll time
                    qd = session.audio_queue.qsize()
                    record_queue_depth(qd)
                    # For cascaded we approximate stt as dominant; providers emit finer breakdown via metadata
                    record_latency(total_ms=total_ms)
                    # attach perf metadata if enabled
                    if settings.perf_enabled:
                        for ev in events:
                            if isinstance(ev, dict):
                                ev.setdefault("perf", {})  # type: ignore
                                ev["perf"]["total_ms"] = round(total_ms, 2)
                                ev["perf"]["queue_depth"] = qd
                for ev in events:
                    if isinstance(ev, (bytes, bytearray)):
                        try:
                            await websocket.send_bytes(ev)
                        except Exception:
                            return
                    else:
                        # add timestamp if missing
                        if isinstance(ev, dict) and "timestamp" not in ev:
                            ev["timestamp"] = time.time()
                        try:
                            await websocket.send_json(ev)
                        except Exception:
                            return
                if audio_since_inference:
                    audio_since_inference = False
                    # start next inference if more audio arrived
                    session._last_t1 = time.monotonic()  # type: ignore[attr-defined]
                    inference_task = asyncio.create_task(
                        pipeline.poll_events(session.session_id)
                    )  # type: ignore[attr-defined]
    except asyncio.CancelledError:
        if audio_task is not None:
            audio_task.cancel()
        if inference_task is not None:
            inference_task.cancel()
        return
    except Exception as exc:
        # P10-ERR-006: never leak raw exception/stack to client — map to INTERNAL_ERROR or MODEL_ERROR
        code = getattr(exc, "code", ErrorCode.MODEL_ERROR.value)
        safe = _safe_code(code)
        if safe not in {c.value for c in ErrorCode}:
            safe = ErrorCode.INTERNAL_ERROR.value
        # sanitize message — do not expose model names or stacks
        msg = (
            str(exc)[:200]
            if safe in (ErrorCode.MODEL_ERROR, ErrorCode.MODEL_NOT_READY)
            else "Processing error"
        )
        if safe == ErrorCode.INTERNAL_ERROR:
            msg = "Internal server error"
            logger.exception(
                "processor_loop internal_error session_id=%s", session.session_id[:8]
            )
        try:
            await websocket.send_json(
                {
                    "type": "error",
                    "code": safe,
                    "message": msg,
                    "retryable": ERROR_RETRYABLE.get(safe, False),
                    "session_id": session.session_id,
                    "timestamp": time.time(),
                }
            )
        except Exception:
            return


async def _session_timeout_watch(websocket: WebSocket, session_id: str) -> None:
    """P10-ERR-004: idle + max duration timeout."""
    idle_ms = settings.session_idle_timeout_ms
    max_ms = settings.session_max_duration_ms
    try:
        while True:
            await asyncio.sleep(1.0)
            sess = await session_service.get_session(session_id)
            if sess is None:
                return
            now = time.time()
            # max duration
            if (now - sess.created_at) * 1000 >= max_ms:
                logger.info(
                    "session_timeout max_duration session_id=%s", session_id[:8]
                )
                record_timeout()
                await _send_error(
                    websocket,
                    ErrorCode.SESSION_TIMEOUT.value,
                    "Session exceeded maximum duration.",
                    session_id=session_id,
                )
                await session_service.end_session(session_id)
                record_session_ended()
                try:
                    await websocket.send_json(
                        {
                            "type": "session.ended",
                            "session_id": session_id,
                            "reason": "timeout",
                        }
                    )
                except Exception:
                    pass
                return
            # idle timeout — only if no audio and queue empty and no pipeline active
            last = sess.last_frame_at or sess.created_at
            queue_empty = sess.audio_queue.empty()
            # grace: don't timeout while inference pending (queue drain)
            if queue_empty and (now - last) * 1000 >= idle_ms:
                logger.info(
                    "session_timeout idle session_id=%s idle_ms=%s",
                    session_id[:8],
                    idle_ms,
                )
                record_timeout()
                await _send_error(
                    websocket,
                    ErrorCode.SESSION_TIMEOUT.value,
                    "Session timed out due to inactivity.",
                    session_id=session_id,
                )
                await session_service.end_session(session_id)
                record_session_ended()
                try:
                    await websocket.send_json(
                        {
                            "type": "session.ended",
                            "session_id": session_id,
                            "reason": "timeout",
                        }
                    )
                except Exception:
                    pass
                return
    except asyncio.CancelledError:
        return


@router.websocket(settings.ws_v1_path)
async def translate_ws(websocket: WebSocket) -> None:
    """Thin gateway — validates, delegates to SessionService, manages lifecycle."""
    # P10-SEC-003: CORS enforcement on WS upgrade in production
    if settings.app_env == "production":
        origin = websocket.headers.get("origin")
        if origin and origin not in settings.cors_origins:
            await websocket.close(code=1008)
            logger.warning("ws_rejected origin=%s not in cors", origin)
            return
    await websocket.accept()
    logger.info("websocket_connected path=%s", settings.ws_v1_path)
    current_session_id: str | None = None
    processor_task: asyncio.Task[None] | None = None
    timeout_task: asyncio.Task[None] | None = None
    # P10-SEC-002: per-session rate-limit sliding window
    frame_times: deque[float] = deque()
    byte_window: deque[tuple[float, int]] = deque()
    # keep window 1s

    def _check_rate_limit(frame_len: int) -> str | None:
        now = time.monotonic()
        # frames per second
        frame_times.append(now)
        while frame_times and now - frame_times[0] > 1.0:
            frame_times.popleft()
        if len(frame_times) > settings.rate_limit_frames_per_second:
            return ErrorCode.RATE_LIMITED.value
        # bytes per second
        byte_window.append((now, frame_len))
        while byte_window and now - byte_window[0][0] > 1.0:
            byte_window.popleft()
        total_bytes = sum(b for _, b in byte_window)
        if total_bytes > settings.rate_limit_bytes_per_second:
            return ErrorCode.RATE_LIMITED.value
        return None

    try:
        while True:
            try:
                msg = await websocket.receive()
            except WebSocketDisconnect:
                break
            except RuntimeError as exc:
                if "Cannot call" in str(exc):
                    break
                logger.exception("websocket_receive_error: %s", exc)
                break
            except Exception as exc:  # pragma: no cover
                logger.exception("websocket_receive_error: %s", exc)
                break

            if "text" in msg and msg["text"] is not None:
                raw_text: str = msg["text"]
                # P10-SEC-001 / P10-ERR-003: oversize JSON
                if len(raw_text.encode("utf-8")) > settings.max_json_bytes:
                    await _send_error(
                        websocket,
                        ErrorCode.INVALID_MESSAGE.value,
                        "Message too large.",
                        session_id=current_session_id,
                    )
                    continue
                # Empty JSON
                if not raw_text.strip():
                    await _send_error(
                        websocket,
                        ErrorCode.INVALID_MESSAGE.value,
                        "Empty message.",
                        session_id=current_session_id,
                    )
                    continue
                try:
                    data = json.loads(raw_text)
                except json.JSONDecodeError:
                    await _send_error(
                        websocket,
                        ErrorCode.INVALID_MESSAGE.value,
                        "Invalid JSON frame.",
                        session_id=current_session_id,
                    )
                    continue

                if not isinstance(data, dict):
                    await _send_error(
                        websocket,
                        ErrorCode.INVALID_MESSAGE.value,
                        "Message must be JSON object.",
                        session_id=current_session_id,
                    )
                    continue

                msg_type = data.get("type")
                if msg_type == "start":
                    try:
                        start = SessionStart.model_validate(data)
                    except Exception as e:
                        await _send_error(
                            websocket,
                            ErrorCode.INVALID_SESSION_CONFIG.value,
                            f"Invalid session config: {e}",
                            session_id=current_session_id,
                        )
                        continue
                    if current_session_id is not None:
                        await _send_error(
                            websocket,
                            ErrorCode.SESSION_ERROR.value,
                            "Session already started.",
                            session_id=current_session_id,
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
                        if ErrorCode.UNSUPPORTED_LANGUAGE.value in msg_str:
                            code = ErrorCode.UNSUPPORTED_LANGUAGE.value
                        elif ErrorCode.UNSUPPORTED_PIPELINE.value in msg_str:
                            code = ErrorCode.UNSUPPORTED_PIPELINE.value
                        elif ErrorCode.MODEL_NOT_READY.value in msg_str:
                            code = ErrorCode.MODEL_NOT_READY.value
                        elif ErrorCode.MODEL_ERROR.value in msg_str:
                            code = ErrorCode.MODEL_ERROR.value
                        elif ErrorCode.INVALID_SESSION_CONFIG.value in msg_str:
                            code = ErrorCode.INVALID_SESSION_CONFIG.value
                        else:
                            code = ErrorCode.SESSION_ERROR.value
                        clean = (
                            msg_str.split(":", 1)[-1].strip()
                            if ":" in msg_str
                            else msg_str
                        )
                        await _send_error(websocket, code, clean, session_id=None)
                        continue
                    current_session_id = session_id
                    frame_times.clear()
                    byte_window.clear()
                    record_session_started()
                    session.processor_task = asyncio.create_task(
                        _processor_loop(session, websocket)
                    )
                    processor_task = session.processor_task
                    # start timeout watcher
                    timeout_task = asyncio.create_task(
                        _session_timeout_watch(websocket, session_id)
                    )
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
                            websocket,
                            ErrorCode.INVALID_MESSAGE.value,
                            "Invalid stop message.",
                            session_id=current_session_id,
                        )
                        continue
                    if current_session_id is None:
                        await _send_error(
                            websocket,
                            ErrorCode.SESSION_ERROR.value,
                            "No active session.",
                            session_id=None,
                        )
                        continue
                    sid = current_session_id
                    if timeout_task and not timeout_task.done():
                        timeout_task.cancel()
                        try:
                            await timeout_task
                        except asyncio.CancelledError:
                            pass
                        timeout_task = None
                    await session_service.end_session(sid)
                    record_session_ended()
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
                    frame_times.clear()
                    byte_window.clear()
                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                else:
                    await _send_error(
                        websocket,
                        ErrorCode.INVALID_MESSAGE.value,
                        f"Unknown message type: {msg_type}",
                        session_id=current_session_id,
                    )

            elif "bytes" in msg and msg["bytes"] is not None:
                frame: bytes = msg["bytes"]
                # P10-ERR-003: binary validation
                if current_session_id is None:
                    await _send_error(
                        websocket,
                        ErrorCode.SESSION_ERROR.value,
                        "No active session for audio.",
                        session_id=None,
                    )
                    continue
                if len(frame) == 0:
                    await _send_error(
                        websocket,
                        ErrorCode.INVALID_AUDIO_DATA.value,
                        "Empty audio frame.",
                        session_id=current_session_id,
                    )
                    continue
                if len(frame) % 2 != 0:
                    await _send_error(
                        websocket,
                        ErrorCode.INVALID_AUDIO_DATA.value,
                        "Audio frame must be even length (S16LE).",
                        session_id=current_session_id,
                    )
                    continue
                if len(frame) > settings.max_audio_frame_bytes:
                    await _send_error(
                        websocket,
                        ErrorCode.INVALID_AUDIO_DATA.value,
                        "Audio frame too large.",
                        session_id=current_session_id,
                    )
                    continue
                # P10-PERF-003 / SEC: rate limit check without disconnect
                rl = _check_rate_limit(len(frame))
                if rl is not None:
                    record_rate_limited()
                    # Drop frame, signal RATE_LIMITED but keep connection
                    await _send_error(
                        websocket,
                        rl,
                        "Rate limit exceeded. Slow down.",
                        session_id=current_session_id,
                    )
                    record_dropped()
                    continue
                assert current_session_id is not None
                session_opt = await session_service.get_session(current_session_id)
                if session_opt is None:
                    await _send_error(
                        websocket,
                        ErrorCode.SESSION_ERROR.value,
                        "Session not found.",
                        session_id=current_session_id,
                    )
                    continue
                # P10-SEC-004: never log raw bytes, only meta
                logger.debug(
                    "ws audio chunk session_id=%s bytes=%s qsize_before=%s total_frames=%s",
                    current_session_id[:8] if current_session_id else "unknown",
                    len(frame),
                    session_opt.audio_queue.qsize(),
                    session_opt.frames_received + 1,
                )
                # Enforce queue depth cap P10-SEC-001
                max_depth = settings.ws_max_queue_depth
                if session_opt.audio_queue.qsize() >= max_depth:
                    # Drop oldest (circular) + count
                    try:
                        session_opt.audio_queue.get_nowait()
                        session_opt.dropped_frames += 1
                        record_dropped()
                    except asyncio.QueueEmpty:
                        pass
                    logger.debug(
                        "audio_queue saturated depth=%s dropped session_id=%s",
                        max_depth,
                        current_session_id[:8],
                    )
                try:
                    session_opt.audio_queue.put_nowait(frame)
                    session_opt.frames_received += 1
                    session_opt.bytes_received += len(frame)
                    session_opt.last_frame_at = time.time()
                    record_frames(1)
                    record_queue_depth(session_opt.audio_queue.qsize())
                    if session_opt.frames_received % 20 == 0:
                        logger.debug(
                            "audio_queue qsize=%s frames=%s bytes=%s session_id=%s",
                            session_opt.audio_queue.qsize(),
                            session_opt.frames_received,
                            session_opt.bytes_received,
                            current_session_id,
                        )
                except asyncio.QueueFull:
                    # Fallback circular drop
                    try:
                        session_opt.audio_queue.get_nowait()
                        session_opt.dropped_frames += 1
                        record_dropped()
                    except asyncio.QueueEmpty:
                        pass
                    try:
                        session_opt.audio_queue.put_nowait(frame)
                        session_opt.frames_received += 1
                        session_opt.bytes_received += len(frame)
                        session_opt.last_frame_at = time.time()
                        record_frames(1)
                    except asyncio.QueueFull:
                        pass
                    logger.debug(
                        "audio_queue full dropped_frames=%s qsize=%s session_id=%s",
                        session_opt.dropped_frames,
                        session_opt.audio_queue.qsize(),
                        current_session_id[:8],
                    )
                    await _send_error(
                        websocket,
                        ErrorCode.RATE_LIMITED.value,
                        "Audio queue full. Slow down.",
                        session_id=current_session_id,
                    )
                    record_rate_limited()
                    continue
            else:
                await _send_error(
                    websocket,
                    ErrorCode.INVALID_MESSAGE.value,
                    "Invalid WebSocket frame.",
                    session_id=current_session_id,
                )

    except WebSocketDisconnect:
        logger.info("websocket_disconnected")
    except Exception as exc:  # P10-ERR-006 global guard — never leak
        logger.exception("websocket_unhandled: %s", exc)
        try:
            await _send_error(
                websocket,
                ErrorCode.INTERNAL_ERROR.value,
                "Internal server error.",
                session_id=current_session_id,
            )
        except Exception:
            pass
    finally:
        if timeout_task and not timeout_task.done():
            timeout_task.cancel()
            try:
                await timeout_task
            except asyncio.CancelledError:
                pass
        if current_session_id is not None:
            await session_service.end_session(current_session_id)
            record_session_ended()
            if processor_task is not None and not processor_task.done():
                processor_task.cancel()
                try:
                    await processor_task
                except asyncio.CancelledError:
                    pass
        else:
            await session_service.cleanup_on_disconnect(websocket)
        logger.info("websocket_closed")
