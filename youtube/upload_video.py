"""Subida de vídeo local a YouTube Data API v3."""

from __future__ import annotations

from pathlib import Path

from googleapiclient.http import MediaFileUpload

from core.logging_config import get_logger
from youtube.service import _youtube_api, _youtube_credentials, refresh_channel_tokens

log = get_logger(__name__)


def upload_local_video(
    *,
    vault,
    channel,
    client_id: str,
    client_secret: str,
    file_path: Path,
    title: str,
    description: str,
    tags: list[str],
    privacy_status: str,
) -> str:
    """
    Sube un archivo y devuelve el youtube_video_id.
    Requiere scope de upload en el OAuth del canal.
    """
    refresh_channel_tokens(
        vault=vault, channel=channel, client_id=client_id, client_secret=client_secret
    )
    creds = _youtube_credentials(
        vault=vault, channel=channel, client_id=client_id, client_secret=client_secret
    )
    yt = _youtube_api(creds)
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    body = {
        "snippet": {
            "title": (title or "Sin título")[:100],
            "description": (description or "")[:5000],
            "tags": tags[:30],
            "categoryId": "22",
        },
        "status": {
            "privacyStatus": privacy_status if privacy_status in ("public", "private", "unlisted") else "private",
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(str(path), mimetype="video/mp4", resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = req.next_chunk()
        if status:
            log.debug("youtube_upload_progress", pct=int(status.progress() * 100))
    vid = (response or {}).get("id")
    if not vid:
        raise RuntimeError("YouTube no devolvió id de vídeo")
    log.info("youtube_upload_ok", video_id=vid)
    return vid
