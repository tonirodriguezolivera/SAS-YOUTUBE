"""Lógica de negocio para proveedores de IA."""

from __future__ import annotations

import json

from core.encryption import SecretVault
from core.exceptions import NotFoundError, ValidationError
from core.logging_config import get_logger
from core.models import AIProviderKind
from providers import repository as repo
from providers.registry import build_llm_provider, build_video_provider, build_voice_provider

log = get_logger(__name__)


def mask_secret_display(credentials_plain: str, *, visible_tail: int = 4) -> str:
    """No exponer claves completas en UI."""
    if len(credentials_plain) <= visible_tail:
        return "****"
    return "****" + credentials_plain[-visible_tail:]


def validate_provider(kind: str, role: str, credentials_plain: str) -> tuple[bool, str]:
    """role: llm | video | voice"""
    try:
        if role == "llm":
            p = build_llm_provider(kind, json.dumps({"api_key": credentials_plain}))
            r = p.validate_credentials()
        elif role == "video":
            p = build_video_provider(kind, json.dumps({"api_key": credentials_plain}))
            r = p.validate_credentials()
        elif role == "voice":
            p = build_voice_provider(kind, json.dumps({"api_key": credentials_plain}))
            r = p.validate_credentials()
        else:
            return False, "Rol de proveedor desconocido"
        return r.ok, r.message
    except Exception as e:  # noqa: BLE001
        log.warning("provider_validate_failed", kind=kind, role=role, error=str(e))
        return False, str(e)


def infer_role_for_kind(kind: str) -> str:
    if kind == AIProviderKind.openai.value:
        return "llm"
    if kind == AIProviderKind.google_gemini.value:
        return "llm"
    if kind == AIProviderKind.google_veo.value:
        return "video"
    if kind == AIProviderKind.runway.value:
        return "video"
    if kind == AIProviderKind.elevenlabs.value:
        return "voice"
    raise ValidationError("Tipo de proveedor no reconocido")


def create_provider(
    *,
    user_id: int,
    vault: SecretVault,
    kind: str,
    display_label: str,
    api_key: str,
    run_validation: bool = True,
) -> tuple[object, str | None]:
    if not api_key.strip():
        raise ValidationError("La API key es obligatoria")
    role = infer_role_for_kind(kind)
    msg = None
    if run_validation:
        ok, message = validate_provider(kind, role, api_key.strip())
        msg = message
        if not ok:
            raise ValidationError(f"Validación fallida: {message}")
    enc = vault.encrypt(json.dumps({"api_key": api_key.strip()}))
    row = repo.create_entry(
        user_id=user_id,
        kind=kind,
        display_label=display_label,
        credentials_encrypted=enc,
        extra_settings_json=None,
        is_validated=bool(run_validation),
    )
    return row, msg


def delete_provider(user_id: int, config_id: int) -> None:
    if not repo.delete_for_user(user_id, config_id):
        raise NotFoundError("Proveedor no encontrado")
