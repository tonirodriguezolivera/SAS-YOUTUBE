"""Acceso a datos de configuración de proveedores."""

from __future__ import annotations

from core.models import AIProviderConfig
from extensions import db


def list_for_user(user_id: int) -> list[AIProviderConfig]:
    return (
        db.session.query(AIProviderConfig)
        .filter(AIProviderConfig.user_id == user_id)
        .order_by(AIProviderConfig.created_at.desc())
        .all()
    )


def get_for_user(user_id: int, config_id: int) -> AIProviderConfig | None:
    return (
        db.session.query(AIProviderConfig)
        .filter(AIProviderConfig.user_id == user_id, AIProviderConfig.id == config_id)
        .first()
    )


def create_entry(
    *,
    user_id: int,
    kind: str,
    display_label: str,
    credentials_encrypted: str,
    extra_settings_json: dict | None = None,
    is_validated: bool = False,
) -> AIProviderConfig:
    row = AIProviderConfig(
        user_id=user_id,
        kind=kind,
        display_label=display_label,
        credentials_encrypted=credentials_encrypted,
        extra_settings_json=extra_settings_json,
        is_validated=is_validated,
    )
    db.session.add(row)
    db.session.commit()
    return row


def delete_for_user(user_id: int, config_id: int) -> bool:
    row = get_for_user(user_id, config_id)
    if not row:
        return False
    db.session.delete(row)
    db.session.commit()
    return True
