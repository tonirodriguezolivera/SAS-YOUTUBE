"""Registro de auditoría (sin credenciales en details)."""

from __future__ import annotations

from typing import Any

from core.models import AuditLog
from extensions import db


def log_audit(
    *,
    user_id: int | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    row = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details_json=details,
        ip_address=ip_address,
    )
    db.session.add(row)
    db.session.commit()
