"""Acceso al cofre de secretos desde código sin Flask request."""

from __future__ import annotations

from typing import Any

from core.encryption import SecretVault, get_fernet


def secret_vault_from_config(config: dict[str, Any]) -> SecretVault:
    f = get_fernet(
        config.get("FERNET_KEY"),
        config["SECRET_KEY"],
        allow_dev_derive=not config.get("TESTING"),
    )
    return SecretVault(f)
