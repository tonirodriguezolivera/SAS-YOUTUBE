"""Cifrado simétrico para secretos en reposo (Fernet)."""

from __future__ import annotations

import base64
import hashlib
import os
from typing import Final

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_DEV_SALT: Final[bytes] = b"youtube-automator-dev-salt"


def build_fernet_from_secret_key(secret_key: str) -> Fernet:
    """
    Deriva una clave Fernet desde SECRET_KEY (solo desarrollo si no hay FERNET_KEY).
    No usar en producción para datos sensibles de larga vida.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_DEV_SALT,
        iterations=480_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode("utf-8")))
    return Fernet(key)


def get_fernet(fernet_key_b64: str | None, secret_key: str, *, allow_dev_derive: bool = True) -> Fernet:
    """
    Obtiene instancia Fernet.
    Prioridad: FERNET_KEY explícita > derivación desde SECRET_KEY (solo si allow_dev_derive).
    """
    if fernet_key_b64:
        key = fernet_key_b64.strip().encode("utf-8")
        return Fernet(key)
    if allow_dev_derive and secret_key and secret_key != "dev-change-me-in-production":
        return build_fernet_from_secret_key(secret_key)
    if allow_dev_derive:
        # Último recurso para `flask run` sin .env: clave estable por proceso
        fallback = hashlib.sha256((secret_key or "dev").encode()).digest()
        return Fernet(base64.urlsafe_b64encode(fallback))
    raise RuntimeError("FERNET_KEY no configurada")


class SecretVault:
    """Encapsula cifrado/descifrado de strings."""

    def __init__(self, fernet: Fernet) -> None:
        self._fernet = fernet

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode("utf-8")).decode("utf-8")
        except InvalidToken as e:
            raise ValueError("No se pudo descifrar el secreto") from e


def generate_fernet_key() -> str:
    """Genera una clave Fernet nueva (para documentar en README)."""
    return Fernet.generate_key().decode("utf-8")
