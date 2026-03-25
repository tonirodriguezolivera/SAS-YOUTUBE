"""Rutas de perfil."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from core.audit import log_audit
from users.forms import ProfileForm
from users.repository import update_profile

users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        update_profile(current_user, display_name=form.display_name.data.strip())
        log_audit(
            user_id=current_user.id,
            action="profile_updated",
            resource_type="user",
            resource_id=str(current_user.id),
            ip_address=request.remote_addr,
        )
        flash("Perfil actualizado.", "success")
        return redirect(url_for("users.profile"))
    return render_template("users/profile.html", form=form)
