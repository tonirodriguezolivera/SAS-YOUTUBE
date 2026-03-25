"""Configuración por entorno."""

from __future__ import annotations

import os
from pathlib import Path


class BaseConfig:
    """Valores comunes y por defecto."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    # Cifrado de secretos (obligatorio en producción; ver README)
    FERNET_KEY = os.environ.get("FERNET_KEY", "")

    # Google OAuth (YouTube)
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_OAUTH_REDIRECT_URI = os.environ.get(
        "GOOGLE_OAUTH_REDIRECT_URI",
        "http://127.0.0.1:5000/youtube/oauth/callback",
    )

    # Almacenamiento de assets generados
    MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", "instance/media")).resolve()

    # YouTube: visibilidad por defecto si publish_mode=automatic (review siempre sube private)
    YOUTUBE_DEFAULT_PRIVACY = os.environ.get("YOUTUBE_DEFAULT_PRIVACY", "private").lower()

    # Voz: si no hay voice_id en credenciales ElevenLabs (JSON), usar este id de voz
    ELEVENLABS_DEFAULT_VOICE_ID = os.environ.get("ELEVENLABS_DEFAULT_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

    # Sesión
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME_DAYS = 14

    # CSRF
    WTF_CSRF_ENABLED = True

    # Rate limiting (memoria; en producción usar Redis URI)
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    STRUCTLOG_JSON = os.environ.get("STRUCTLOG_JSON", "").lower() in ("1", "true", "yes")


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + str(Path(__file__).resolve().parent / "instance" / "app.db"),
    )


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "")

    @classmethod
    def init_app(cls, app):  # noqa: ARG003
        if not os.environ.get("SECRET_KEY"):
            raise RuntimeError("SECRET_KEY es obligatoria en producción")
        if not os.environ.get("FERNET_KEY"):
            raise RuntimeError("FERNET_KEY es obligatoria en producción para cifrar API keys")


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


def get_config(name: str | None) -> type[BaseConfig]:
    """Resuelve la clase de configuración según FLASK_ENV / variable explícita."""
    env = (name or os.environ.get("FLASK_ENV") or "development").lower()
    mapping = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig,
    }
    return mapping.get(env, DevelopmentConfig)
