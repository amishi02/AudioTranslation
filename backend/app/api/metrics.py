"""Metrics endpoint — P10-PERF-003."""

from __future__ import annotations

from fastapi import APIRouter

from app.services.metrics import get_metrics

router = APIRouter()


@router.get("/metrics")
async def metrics() -> dict:
    return get_metrics().snapshot()
