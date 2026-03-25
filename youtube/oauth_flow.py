"""Configuración del cliente OAuth de Google para YouTube."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flask import Flask


YOUTUBE_SCOPES: tuple[str, ...] = (
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
)


def client_config_from_app(app: Flask) -> dict[str, Any]:
    return {
        "web": {
            "client_id": app.config["GOOGLE_CLIENT_ID"],
            "client_secret": app.config["GOOGLE_CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [app.config["GOOGLE_OAUTH_REDIRECT_URI"]],
        }
    }


def build_flow(app: Flask):
    from google_auth_oauthlib.flow import Flow

    return Flow.from_client_config(
        client_config_from_app(app),
        scopes=list(YOUTUBE_SCOPES),
        redirect_uri=app.config["GOOGLE_OAUTH_REDIRECT_URI"],
    )
