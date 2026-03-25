"""Acceso a datos de automatizaciones."""

from __future__ import annotations

from core.models import AutomationProfile
from extensions import db


def list_for_user(user_id: int) -> list[AutomationProfile]:
    return (
        db.session.query(AutomationProfile)
        .filter(AutomationProfile.user_id == user_id)
        .order_by(AutomationProfile.updated_at.desc())
        .all()
    )


def get_for_user(user_id: int, profile_id: int) -> AutomationProfile | None:
    return (
        db.session.query(AutomationProfile)
        .filter(AutomationProfile.user_id == user_id, AutomationProfile.id == profile_id)
        .first()
    )


def create_profile(**kwargs) -> AutomationProfile:
    row = AutomationProfile(**kwargs)
    db.session.add(row)
    db.session.commit()
    return row


def save(row: AutomationProfile) -> AutomationProfile:
    db.session.commit()
    return row


def delete_for_user(user_id: int, profile_id: int) -> bool:
    row = get_for_user(user_id, profile_id)
    if not row:
        return False
    db.session.delete(row)
    db.session.commit()
    return True


def list_active() -> list[AutomationProfile]:
    return (
        db.session.query(AutomationProfile)
        .filter(AutomationProfile.status == "active")
        .all()
    )
