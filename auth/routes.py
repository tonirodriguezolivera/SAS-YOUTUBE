"""Rutas de registro, login y logout."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from core.audit import log_audit
from auth.forms import LoginForm, PasswordResetRequestForm, RegisterForm
from extensions import limiter
from users.repository import create_user, get_by_email

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = RegisterForm()
    if form.validate_on_submit():
        pw_hash = generate_password_hash(form.password.data)
        user = create_user(
            email=form.email.data,
            password_hash=pw_hash,
            display_name=form.display_name.data.strip(),
        )
        log_audit(
            user_id=user.id,
            action="user_registered",
            resource_type="user",
            resource_id=str(user.id),
            ip_address=request.remote_addr,
        )
        login_user(user)
        flash("Cuenta creada. Bienvenido.", "success")
        return redirect(url_for("dashboard.index"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("20 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = get_by_email(form.email.data)
        if user and check_password_hash(user.password_hash, form.password.data):
            if not user.is_active:
                flash("Cuenta desactivada.", "danger")
            else:
                login_user(user, remember=True)
                log_audit(
                    user_id=user.id,
                    action="login",
                    resource_type="user",
                    resource_id=str(user.id),
                    ip_address=request.remote_addr,
                )
                next_url = request.args.get("next")
                if next_url and next_url.startswith("/"):
                    return redirect(next_url)
                return redirect(url_for("dashboard.index"))
        flash("Email o contraseña incorrectos.", "danger")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
def logout():
    if current_user.is_authenticated:
        log_audit(
            user_id=current_user.id,
            action="logout",
            resource_type="user",
            resource_id=str(current_user.id),
            ip_address=request.remote_addr,
        )
        logout_user()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password_request():
    """
    Punto de extensión: aquí se integrará envío de email con token firmado.
    """
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        flash(
            "Si existe una cuenta con ese email, recibirás instrucciones (pendiente de configurar SMTP).",
            "info",
        )
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_request.html", form=form)
