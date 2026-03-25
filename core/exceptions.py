"""Excepciones de dominio."""


class DomainError(Exception):
    """Error de reglas de negocio visible al usuario (mensaje seguro)."""


class NotFoundError(DomainError):
    """Recurso inexistente o sin acceso."""


class ValidationError(DomainError):
    """Datos inválidos."""
