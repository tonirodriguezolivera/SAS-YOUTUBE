"""Reglas de negocio para perfiles de automatización."""

from __future__ import annotations

from core.exceptions import NotFoundError, ValidationError
from core.models import AIProviderConfig, AutomationProfile, YoutubeChannel
from automations import repository as repo
from extensions import db


def _validate_fk_user(user_id: int, channel_id: int | None, provider_ids: list[int | None]) -> None:
    if channel_id is not None:
        ch = db.session.get(YoutubeChannel, channel_id)
        if not ch or ch.user_id != user_id:
            raise ValidationError("Canal de YouTube no válido")
    for pid in provider_ids:
        if pid is None:
            continue
        p = db.session.get(AIProviderConfig, pid)
        if not p or p.user_id != user_id:
            raise ValidationError("Proveedor de IA no válido")


def create_automation(
    *,
    user_id: int,
    data: dict,
) -> AutomationProfile:
    _validate_fk_user(
        user_id,
        data.get("youtube_channel_id"),
        [
            data.get("llm_provider_id"),
            data.get("video_provider_id"),
            data.get("voice_provider_id"),
        ],
    )
    row = repo.create_profile(
        user_id=user_id,
        name=data["name"],
        youtube_channel_id=data.get("youtube_channel_id"),
        llm_provider_id=data.get("llm_provider_id"),
        video_provider_id=data.get("video_provider_id"),
        voice_provider_id=data.get("voice_provider_id"),
        videos_per_day=float(data.get("videos_per_day", 1)),
        duration_min_seconds=int(data.get("duration_min_seconds", 35)),
        duration_max_seconds=int(data.get("duration_max_seconds", 55)),
        language=data.get("language", "es"),
        tone=data.get("tone", "viral"),
        cta_style=data.get("cta_style", "comment_subscribe"),
        master_prompt=data.get("master_prompt", ""),
        status=data.get("status", "active"),
        content_format=data.get("content_format", "short"),
        publish_mode=data.get("publish_mode", "review"),
        schedule_config=data.get("schedule_config"),
    )
    return row


def update_automation(user_id: int, profile_id: int, data: dict) -> AutomationProfile:
    row = repo.get_for_user(user_id, profile_id)
    if not row:
        raise NotFoundError("Automatización no encontrada")
    _validate_fk_user(
        user_id,
        data.get("youtube_channel_id"),
        [
            data.get("llm_provider_id"),
            data.get("video_provider_id"),
            data.get("voice_provider_id"),
        ],
    )
    for key in (
        "name",
        "youtube_channel_id",
        "llm_provider_id",
        "video_provider_id",
        "voice_provider_id",
        "videos_per_day",
        "duration_min_seconds",
        "duration_max_seconds",
        "language",
        "tone",
        "cta_style",
        "master_prompt",
        "status",
        "content_format",
        "publish_mode",
        "schedule_config",
    ):
        if key in data:
            val = data[key]
            if key == "videos_per_day" and val is not None:
                val = float(val)
            setattr(row, key, val)
    return repo.save(row)


def toggle_pause(user_id: int, profile_id: int) -> AutomationProfile:
    row = repo.get_for_user(user_id, profile_id)
    if not row:
        raise NotFoundError("Automatización no encontrada")
    row.status = "paused" if row.status == "active" else "active"
    return repo.save(row)


def delete_automation(user_id: int, profile_id: int) -> None:
    if not repo.delete_for_user(user_id, profile_id):
        raise NotFoundError("Automatización no encontrada")
