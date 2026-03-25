"""Publicación en YouTube Data API v3 a partir de PublicationJob."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import or_

from core.logging_config import get_logger
from core.models import (
    AutomationProfile,
    JobStatus,
    PublicationJob,
    PublishedVideo,
)
from extensions import db

log = get_logger(__name__)


def publish_due_jobs() -> dict:
    """Procesa PublicationJob pendientes cuya fecha programada haya pasado."""
    from flask import current_app

    from core.vault_util import secret_vault_from_config
    from youtube.upload_video import upload_local_video

    now = datetime.now(timezone.utc)
    vault = secret_vault_from_config(current_app.config)
    cid = (current_app.config.get("GOOGLE_CLIENT_ID") or "").strip()
    csec = (current_app.config.get("GOOGLE_CLIENT_SECRET") or "").strip()

    if not cid or not csec:
        log.warning("publish_skip_no_google_oauth")
        return {"processed": 0, "error": "faltan credenciales Google OAuth"}

    pending = (
        db.session.query(PublicationJob)
        .filter(
            PublicationJob.status == JobStatus.pending.value,
            or_(
                PublicationJob.scheduled_at.is_(None),
                PublicationJob.scheduled_at <= now,
            ),
        )
        .order_by(PublicationJob.id)
        .all()
    )

    processed = 0
    for job in pending:
        rend = job.render_job
        if not rend or rend.status != JobStatus.success.value or not rend.output_path:
            job.status = JobStatus.failed.value
            job.error_message = "El render no está listo o falló."
            db.session.commit()
            continue

        mp4 = Path(rend.output_path)
        if not mp4.is_file():
            job.status = JobStatus.failed.value
            job.error_message = "Archivo de vídeo no encontrado."
            db.session.commit()
            continue

        script = rend.script_draft
        if not script:
            job.status = JobStatus.failed.value
            job.error_message = "Sin guion asociado al render."
            db.session.commit()
            continue

        tc = script.title_candidate
        if not tc:
            job.status = JobStatus.failed.value
            job.error_message = "Sin título asociado."
            db.session.commit()
            continue

        profile = db.session.get(AutomationProfile, tc.automation_profile_id)
        if not profile or not profile.youtube_channel_id:
            job.status = JobStatus.failed.value
            job.error_message = "Perfil sin canal de YouTube."
            db.session.commit()
            continue

        channel = profile.youtube_channel
        if not channel:
            job.status = JobStatus.failed.value
            job.error_message = "Canal no cargado."
            db.session.commit()
            continue

        tags = script.hashtags_json or []
        if not isinstance(tags, list):
            tags = []
        tags = [str(t)[:50] for t in tags if t][:30]

        job.status = JobStatus.running.value
        db.session.commit()

        try:
            vid = upload_local_video(
                vault=vault,
                channel=channel,
                client_id=cid,
                client_secret=csec,
                file_path=mp4,
                title=tc.title_text,
                description=(script.description_seo or "")[:5000],
                tags=tags,
                privacy_status=job.privacy_status or "private",
            )
        except Exception as e:  # noqa: BLE001
            log.exception("youtube_upload_error", publication_job_id=job.id)
            job.status = JobStatus.failed.value
            job.error_message = str(e)[:2000]
            db.session.commit()
            continue

        pv = PublishedVideo(
            user_id=profile.user_id,
            youtube_channel_id=channel.id,
            publication_job_id=job.id,
            youtube_video_id=vid,
            title=tc.title_text[:500],
            published_at=now,
        )
        db.session.add(pv)
        job.status = JobStatus.success.value
        job.error_message = None
        db.session.commit()
        processed += 1
        log.info("published_video", youtube_video_id=vid, publication_job_id=job.id)

    return {"processed": processed}
