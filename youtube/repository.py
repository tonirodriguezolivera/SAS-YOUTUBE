"""Acceso a datos de canales de YouTube."""

from __future__ import annotations

from core.models import YoutubeChannel
from extensions import db


def list_for_user(user_id: int) -> list[YoutubeChannel]:
    return (
        db.session.query(YoutubeChannel)
        .filter(YoutubeChannel.user_id == user_id)
        .order_by(YoutubeChannel.created_at.desc())
        .all()
    )


def get_by_google_channel_id(user_id: int, google_channel_id: str) -> YoutubeChannel | None:
    return (
        db.session.query(YoutubeChannel)
        .filter(
            YoutubeChannel.user_id == user_id,
            YoutubeChannel.google_channel_id == google_channel_id,
        )
        .first()
    )


def upsert_channel(
    *,
    user_id: int,
    google_channel_id: str,
    title: str,
    thumbnail_url: str | None,
    access_token_encrypted: str,
    refresh_token_encrypted: str | None,
    token_expiry,
    scopes: str | None,
) -> YoutubeChannel:
    row = get_by_google_channel_id(user_id, google_channel_id)
    if row is None:
        row = YoutubeChannel(user_id=user_id, google_channel_id=google_channel_id)
        db.session.add(row)
    row.title = title
    row.thumbnail_url = thumbnail_url
    row.access_token_encrypted = access_token_encrypted
    row.refresh_token_encrypted = refresh_token_encrypted
    row.token_expiry = token_expiry
    row.scopes = scopes
    row.status = "connected"
    db.session.commit()
    return row


def all_channels_for_refresh() -> list[YoutubeChannel]:
    return db.session.query(YoutubeChannel).filter(YoutubeChannel.refresh_token_encrypted.isnot(None)).all()
