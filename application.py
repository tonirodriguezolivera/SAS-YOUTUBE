"""Factoría Flask: registra extensiones, blueprints y CLI."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash, redirect, url_for

from config import get_config
from core.exceptions import DomainError
from core.logging_config import configure_logging, get_logger
from extensions import csrf, db, limiter, login_manager, migrate

log = get_logger(__name__)


def _load_env_files() -> None:
    """Carga .env en UTF-8; si falla (p. ej. UTF-16 en Windows), reintenta."""
    try:
        load_dotenv(encoding="utf-8")
    except UnicodeDecodeError:
        p = Path(".env")
        if p.exists():
            load_dotenv(p, encoding="utf-16")


def create_app(config_name: str | None = None) -> Flask:
    _load_env_files()
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
        instance_relative_config=True,
    )
    cfg = get_config(config_name)
    app.config.from_object(cfg)
    if hasattr(cfg, "init_app"):
        cfg.init_app(app)

    configure_logging(
        level=app.config.get("LOG_LEVEL", "INFO"),
        json_format=bool(app.config.get("STRUCTLOG_JSON")),
    )

    media_root: Path = app.config["MEDIA_ROOT"]
    media_root.mkdir(parents=True, exist_ok=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    import core.models  # noqa: F401 — metadata SQLAlchemy

    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicia sesión para acceder a esta página."
    login_manager.login_message_category = "warning"

    from core.models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    from auth.routes import auth_bp
    from automations.routes import automations_bp
    from cli.commands import register_cli
    from dashboard.routes import dashboard_bp
    from providers.routes import providers_bp
    from users.routes import users_bp
    from youtube.routes import youtube_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(youtube_bp)
    app.register_blueprint(providers_bp)
    app.register_blueprint(automations_bp)

    register_cli(app)

    @app.errorhandler(DomainError)
    def _domain_error(exc: DomainError):
        flash(str(exc), "danger")
        return redirect(url_for("dashboard.index"))

    @app.get("/health")
    def health():
        return {"status": "ok"}

    log.info("app_ready", env=config_name or "default")
    return app
