"""Sincronización de métricas (YouTube Analytics API) — esqueleto."""

from __future__ import annotations

from core.logging_config import get_logger

log = get_logger(__name__)


def sync_analytics_snapshots() -> dict:
    log.info("analytics_sync_placeholder")
    return {"snapshots": 0}
