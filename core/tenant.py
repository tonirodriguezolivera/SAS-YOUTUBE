"""Garantías multi-tenant en capa de servicio."""

from __future__ import annotations

from core.exceptions import NotFoundError


def assert_owned(instance, user_id: int, *, owner_attr: str = "user_id") -> None:
    """Comprueba que el recurso pertenece al usuario."""
    if instance is None:
        raise NotFoundError("Recurso no encontrado")
    if getattr(instance, owner_attr, None) != user_id:
        raise NotFoundError("Recurso no encontrado")
