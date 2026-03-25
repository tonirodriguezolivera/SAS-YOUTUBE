"""Gestión de credenciales de proveedores IA."""

from __future__ import annotations

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from core.audit import log_audit
from core.encryption import SecretVault, get_fernet
from core.exceptions import NotFoundError, ValidationError
from providers.forms import AIProviderForm
from providers import repository as repo
from providers import service as provider_service

providers_bp = Blueprint("providers", __name__, url_prefix="/providers")


def _vault() -> SecretVault:
    f = get_fernet(
        current_app.config.get("FERNET_KEY"),
        current_app.config["SECRET_KEY"],
        allow_dev_derive=not current_app.config.get("TESTING"),
    )
    return SecretVault(f)


@providers_bp.route("/")
@login_required
def list_providers():
    rows = repo.list_for_user(current_user.id)
    return render_template("providers/list.html", providers=rows)


@providers_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = AIProviderForm()
    if form.validate_on_submit():
        try:
            _, msg = provider_service.create_provider(
                user_id=current_user.id,
                vault=_vault(),
                kind=form.kind.data,
                display_label=form.display_label.data.strip(),
                api_key=form.api_key.data.strip(),
                run_validation=True,
            )
            log_audit(
                user_id=current_user.id,
                action="ai_provider_created",
                resource_type="ai_provider_config",
                ip_address=request.remote_addr,
            )
            flash(f"Proveedor guardado. {msg or ''}", "success")
            return redirect(url_for("providers.list_providers"))
        except ValidationError as e:
            flash(str(e), "danger")
    return render_template("providers/form.html", form=form)


@providers_bp.route("/<int:pid>/delete", methods=["POST"])
@login_required
def delete(pid: int):
    try:
        provider_service.delete_provider(current_user.id, pid)
        flash("Proveedor eliminado.", "info")
    except NotFoundError as e:
        flash(str(e), "danger")
    return redirect(url_for("providers.list_providers"))
