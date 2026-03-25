"""CRUD de perfiles de automatización."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from core.audit import log_audit
from core.exceptions import NotFoundError, ValidationError
from automations.forms import AutomationProfileForm
from automations import repository as repo
from automations import service as automation_service
from core.models import AIProviderConfig, AIProviderKind, YoutubeChannel
from extensions import db

automations_bp = Blueprint("automations", __name__, url_prefix="/automations")


def _choices_channels(user_id: int) -> list[tuple[int, str]]:
    rows = db.session.query(YoutubeChannel).filter(YoutubeChannel.user_id == user_id).all()
    return [(0, "— Ninguno —")] + [(r.id, r.title or r.google_channel_id) for r in rows]


def _choices_providers(user_id: int, kinds: list[str]) -> list[tuple[int, str]]:
    q = db.session.query(AIProviderConfig).filter(
        AIProviderConfig.user_id == user_id,
        AIProviderConfig.kind.in_(kinds),
    )
    rows = q.all()
    return [(0, "— Ninguno —")] + [(r.id, f"{r.display_label} ({r.kind})") for r in rows]


def _bind_form_choices(form: AutomationProfileForm, user_id: int) -> None:
    form.youtube_channel_id.choices = _choices_channels(user_id)
    form.llm_provider_id.choices = _choices_providers(
        user_id,
        [AIProviderKind.openai.value, AIProviderKind.google_gemini.value],
    )
    form.video_provider_id.choices = _choices_providers(
        user_id,
        [AIProviderKind.runway.value, AIProviderKind.google_veo.value],
    )
    form.voice_provider_id.choices = _choices_providers(user_id, [AIProviderKind.elevenlabs.value])


def _none_if_zero(v: int | None) -> int | None:
    if v is None or v == 0:
        return None
    return v


@automations_bp.route("/")
@login_required
def list_profiles():
    rows = repo.list_for_user(current_user.id)
    return render_template("automations/list.html", profiles=rows)


@automations_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = AutomationProfileForm()
    _bind_form_choices(form, current_user.id)
    if form.validate_on_submit():
        try:
            automation_service.create_automation(
                user_id=current_user.id,
                data={
                    "name": form.name.data.strip(),
                    "youtube_channel_id": _none_if_zero(form.youtube_channel_id.data),
                    "llm_provider_id": _none_if_zero(form.llm_provider_id.data),
                    "video_provider_id": _none_if_zero(form.video_provider_id.data),
                    "voice_provider_id": _none_if_zero(form.voice_provider_id.data),
                    "videos_per_day": form.videos_per_day.data,
                    "duration_min_seconds": form.duration_min_seconds.data,
                    "duration_max_seconds": form.duration_max_seconds.data,
                    "language": form.language.data.strip(),
                    "tone": form.tone.data.strip(),
                    "cta_style": form.cta_style.data.strip(),
                    "master_prompt": form.master_prompt.data,
                    "content_format": form.content_format.data,
                    "publish_mode": form.publish_mode.data,
                    "status": form.status.data,
                    "schedule_config": None,
                },
            )
            log_audit(
                user_id=current_user.id,
                action="automation_created",
                resource_type="automation_profile",
                ip_address=request.remote_addr,
            )
            flash("Automatización creada.", "success")
            return redirect(url_for("automations.list_profiles"))
        except ValidationError as e:
            flash(str(e), "danger")
    return render_template("automations/form.html", form=form, title="Nueva automatización")


@automations_bp.route("/<int:pid>/edit", methods=["GET", "POST"])
@login_required
def edit(pid: int):
    row = repo.get_for_user(current_user.id, pid)
    if not row:
        flash("No encontrado.", "danger")
        return redirect(url_for("automations.list_profiles"))
    form = AutomationProfileForm(obj=row)
    _bind_form_choices(form, current_user.id)
    if not form.is_submitted():
        form.youtube_channel_id.data = row.youtube_channel_id or 0
        form.llm_provider_id.data = row.llm_provider_id or 0
        form.video_provider_id.data = row.video_provider_id or 0
        form.voice_provider_id.data = row.voice_provider_id or 0
    if form.validate_on_submit():
        try:
            automation_service.update_automation(
                current_user.id,
                pid,
                {
                    "name": form.name.data.strip(),
                    "youtube_channel_id": _none_if_zero(form.youtube_channel_id.data),
                    "llm_provider_id": _none_if_zero(form.llm_provider_id.data),
                    "video_provider_id": _none_if_zero(form.video_provider_id.data),
                    "voice_provider_id": _none_if_zero(form.voice_provider_id.data),
                    "videos_per_day": form.videos_per_day.data,
                    "duration_min_seconds": form.duration_min_seconds.data,
                    "duration_max_seconds": form.duration_max_seconds.data,
                    "language": form.language.data.strip(),
                    "tone": form.tone.data.strip(),
                    "cta_style": form.cta_style.data.strip(),
                    "master_prompt": form.master_prompt.data,
                    "content_format": form.content_format.data,
                    "publish_mode": form.publish_mode.data,
                    "status": form.status.data,
                },
            )
            log_audit(
                user_id=current_user.id,
                action="automation_updated",
                resource_type="automation_profile",
                resource_id=str(pid),
                ip_address=request.remote_addr,
            )
            flash("Cambios guardados.", "success")
            return redirect(url_for("automations.list_profiles"))
        except (ValidationError, NotFoundError) as e:
            flash(str(e), "danger")
    return render_template("automations/form.html", form=form, title="Editar automatización")


@automations_bp.route("/<int:pid>/toggle", methods=["POST"])
@login_required
def toggle(pid: int):
    try:
        automation_service.toggle_pause(current_user.id, pid)
        flash("Estado actualizado.", "success")
    except NotFoundError as e:
        flash(str(e), "danger")
    return redirect(url_for("automations.list_profiles"))


@automations_bp.route("/<int:pid>/delete", methods=["POST"])
@login_required
def delete(pid: int):
    try:
        automation_service.delete_automation(current_user.id, pid)
        flash("Eliminada.", "info")
    except NotFoundError as e:
        flash(str(e), "danger")
    return redirect(url_for("automations.list_profiles"))
