"""Dashboard principal."""

from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import current_user, login_required
from sqlalchemy import func

from core.models import (
    AuditLog,
    AutomationProfile,
    PipelineRun,
    PublishedVideo,
    TitleCandidate,
    YoutubeChannel,
)
from extensions import db

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    uid = current_user.id
    n_channels = db.session.query(func.count(YoutubeChannel.id)).filter(YoutubeChannel.user_id == uid).scalar() or 0
    n_auto_active = (
        db.session.query(func.count(AutomationProfile.id))
        .filter(AutomationProfile.user_id == uid, AutomationProfile.status == "active")
        .scalar()
        or 0
    )
    n_titles = (
        db.session.query(func.count(TitleCandidate.id))
        .select_from(TitleCandidate)
        .join(AutomationProfile, TitleCandidate.automation_profile_id == AutomationProfile.id)
        .filter(AutomationProfile.user_id == uid)
        .scalar()
        or 0
    )
    n_published = (
        db.session.query(func.count(PublishedVideo.id)).filter(PublishedVideo.user_id == uid).scalar() or 0
    )
    recent_logs = (
        db.session.query(AuditLog)
        .filter(AuditLog.user_id == uid)
        .order_by(AuditLog.created_at.desc())
        .limit(12)
        .all()
    )
    pipeline_runs = (
        db.session.query(PipelineRun)
        .join(AutomationProfile, PipelineRun.automation_profile_id == AutomationProfile.id)
        .filter(AutomationProfile.user_id == uid)
        .order_by(PipelineRun.updated_at.desc())
        .limit(15)
        .all()
    )
    return render_template(
        "dashboard/index.html",
        kpis={
            "channels": int(n_channels),
            "automations_active": int(n_auto_active),
            "titles": int(n_titles),
            "published": int(n_published),
        },
        recent_logs=recent_logs,
        pipeline_runs=pipeline_runs,
    )


@dashboard_bp.route("/pipeline/<int:run_id>")
@login_required
def pipeline_detail(run_id: int):
    run = db.session.get(PipelineRun, run_id)
    if not run or run.automation.user_id != current_user.id:
        from flask import abort

        abort(404)
    return render_template("dashboard/pipeline_detail.html", run=run)
