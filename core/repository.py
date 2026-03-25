"""Utilidades mínimas para repositorios (consultas por tenant)."""

from __future__ import annotations

from typing import TypeVar

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from extensions import db

T = TypeVar("T")


def scoped_session() -> Session:
    """Sesión SQLAlchemy actual (request-scoped con Flask-SQLAlchemy)."""
    return db.session


def ensure_user_filter(stmt: Select[tuple[T]], model, user_id: int, user_column_name: str = "user_id") -> Select[tuple[T]]:
    """Añade filtro por usuario a un select (multi-tenant)."""
    col = getattr(model, user_column_name)
    return stmt.where(col == user_id)
