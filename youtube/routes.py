"""Rutas OAuth y listado de canales."""

from __future__ import annotations

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from core.audit import log_audit
from core.encryption import SecretVault, get_fernet
from core.exceptions import ValidationError
from youtube.oauth_flow import build_flow
from youtube import repository as repo
from youtube.service import persist_oauth_tokens

youtube_bp = Blueprint("youtube", __name__, url_prefix="/youtube")


def _vault() -> SecretVault:
    f = get_fernet(
        current_app.config.get("FERNET_KEY"),
        current_app.config["SECRET_KEY"],
        allow_dev_derive=not current_app.config.get("TESTING"),
    )
    return SecretVault(f)


@youtube_bp.route("/channels")
@login_required
def channels():
    rows = repo.list_for_user(current_user.id)
    return render_template("youtube/channels.html", channels=rows)


@youtube_bp.route("/oauth/start")
@login_required
def oauth_start():
    if not current_app.config.get("GOOGLE_CLIENT_ID") or not current_app.config.get("GOOGLE_CLIENT_SECRET"):
        flash("Configura GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET en el entorno.", "warning")
        return redirect(url_for("youtube.channels"))
    flow = build_flow(current_app)
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    session["youtube_oauth_state"] = state
    return redirect(authorization_url)


@youtube_bp.route("/oauth/callback")
@login_required
def oauth_callback():
    state = session.pop("youtube_oauth_state", None)
    if state is None:
        flash("Sesión OAuth inválida. Vuelve a conectar.", "danger")
        return redirect(url_for("youtube.channels"))
    if not current_app.config.get("GOOGLE_CLIENT_ID"):
        abort(500)
    flow = build_flow(current_app)
    flow.state = state
    try:
        flow.fetch_token(authorization_response=request.url)
    except Exception as e:  # noqa: BLE001
        flash(f"Error OAuth: {e!s}", "danger")
        return redirect(url_for("youtube.channels"))
    creds = flow.credentials
    try:
        persist_oauth_tokens(
            user_id=current_user.id,
            vault=_vault(),
            flow_credentials=creds,
            client_id=current_app.config["GOOGLE_CLIENT_ID"],
            client_secret=current_app.config["GOOGLE_CLIENT_SECRET"],
        )
    except ValidationError as e:
        flash(str(e), "danger")
        return redirect(url_for("youtube.channels"))
    log_audit(
        user_id=current_user.id,
        action="youtube_channel_connected",
        resource_type="youtube_channel",
        ip_address=request.remote_addr,
    )
    flash("Canal de YouTube conectado correctamente.", "success")
    return redirect(url_for("youtube.channels"))
