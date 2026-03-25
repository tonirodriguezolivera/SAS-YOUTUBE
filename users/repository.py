"""Acceso a datos de usuario."""

from __future__ import annotations

from core.models import User
from extensions import db


def get_by_id(user_id: int) -> User | None:
    return db.session.get(User, user_id)


def get_by_email(email: str) -> User | None:
    return db.session.query(User).filter(User.email == email.lower().strip()).first()


def create_user(*, email: str, password_hash: str, display_name: str) -> User:
    u = User(
        email=email.lower().strip(),
        password_hash=password_hash,
        display_name=display_name,
    )
    db.session.add(u)
    db.session.commit()
    return u


def update_profile(user: User, *, display_name: str) -> User:
    user.display_name = display_name
    db.session.commit()
    return user
