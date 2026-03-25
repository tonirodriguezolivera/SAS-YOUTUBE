"""Lógica de negocio YouTube: OAuth, persistencia cifrada y API."""

from __future__ import annotations

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from core.encryption import SecretVault
from core.exceptions import ValidationError
from core.logging_config import get_logger
from core.models import YoutubeChannel
from extensions import db
from youtube import repository as repo
from youtube.oauth_flow import YOUTUBE_SCOPES

log = get_logger(__name__)


def _youtube_api(creds: Credentials):
    """Import perezoso: evita cargar googleapiclient al arrancar (y entornos globales rotos)."""
    from googleapiclient.discovery import build

    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def _youtube_credentials(
    *,
    vault: SecretVault,
    channel: YoutubeChannel,
    client_id: str,
    client_secret: str,
) -> Credentials:
    access = vault.decrypt(channel.access_token_encrypted)
    refresh = vault.decrypt(channel.refresh_token_encrypted) if channel.refresh_token_encrypted else None
    return Credentials(
        token=access,
        refresh_token=refresh,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=list(YOUTUBE_SCOPES),
        expiry=channel.token_expiry,
    )


def refresh_channel_tokens(
    *,
    vault: SecretVault,
    channel: YoutubeChannel,
    client_id: str,
    client_secret: str,
) -> None:
    """Actualiza tokens en BD si el access_token expiró."""
    creds = _youtube_credentials(
        vault=vault, channel=channel, client_id=client_id, client_secret=client_secret
    )
    if not creds.refresh_token:
        log.warning("no_refresh_token", channel_id=channel.id)
        return
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        channel.access_token_encrypted = vault.encrypt(creds.token or "")
        if creds.refresh_token:
            channel.refresh_token_encrypted = vault.encrypt(creds.refresh_token)
        channel.token_expiry = creds.expiry
        db.session.commit()


def fetch_my_channels_metadata(
    *,
    vault: SecretVault,
    channel_row: YoutubeChannel,
    client_id: str,
    client_secret: str,
) -> list[dict]:
    """Lista canales OAuth del usuario."""
    refresh_channel_tokens(
        vault=vault,
        channel=channel_row,
        client_id=client_id,
        client_secret=client_secret,
    )
    creds = _youtube_credentials(
        vault=vault, channel=channel_row, client_id=client_id, client_secret=client_secret
    )
    yt = _youtube_api(creds)
    resp = yt.channels().list(part="snippet", mine=True).execute()
    out: list[dict] = []
    for item in resp.get("items", []):
        sn = item.get("snippet") or {}
        thumbs = sn.get("thumbnails") or {}
        thumb = (thumbs.get("high") or thumbs.get("default") or {}).get("url")
        out.append(
            {
                "google_channel_id": item["id"],
                "title": sn.get("title") or "",
                "thumbnail_url": thumb,
            }
        )
    return out


def persist_oauth_tokens(
    *,
    user_id: int,
    vault: SecretVault,
    flow_credentials,
    client_id: str,
    client_secret: str,
) -> YoutubeChannel:
    """Tras callback OAuth: obtiene datos del canal y guarda tokens cifrados."""
    access = flow_credentials.token
    refresh = flow_credentials.refresh_token
    expiry = flow_credentials.expiry

    creds = Credentials(
        token=access,
        refresh_token=refresh,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=list(YOUTUBE_SCOPES),
        expiry=expiry,
    )
    yt = _youtube_api(creds)
    resp = yt.channels().list(part="snippet", mine=True).execute()
    items = resp.get("items") or []
    if not items:
        raise ValidationError("No se pudo leer ningún canal de YouTube para esta cuenta.")

    item = items[0]
    sn = item.get("snippet") or {}
    thumbs = sn.get("thumbnails") or {}
    thumb = (thumbs.get("high") or thumbs.get("default") or {}).get("url")
    google_channel_id = item["id"]
    title = sn.get("title") or "Canal"

    return repo.upsert_channel(
        user_id=user_id,
        google_channel_id=google_channel_id,
        title=title,
        thumbnail_url=thumb,
        access_token_encrypted=vault.encrypt(access),
        refresh_token_encrypted=vault.encrypt(refresh) if refresh else None,
        token_expiry=expiry,
        scopes=" ".join(YOUTUBE_SCOPES),
    )
