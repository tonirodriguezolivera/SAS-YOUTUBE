"""Grupo `flask jobs` para tareas programadas."""

from __future__ import annotations

import click
from flask import current_app
from flask.cli import with_appcontext


@click.group(name="jobs")
def jobs_group():
    """Tareas batch disparadas por cron."""


@jobs_group.command("seed-content")
@with_appcontext
def seed_content():
    """Fase A: genera ideas de contenido (estrategia) por automatización activa."""
    from pipeline.service import seed_content_all_active

    r = seed_content_all_active()
    click.echo(r)


@jobs_group.command("process-pipeline")
@with_appcontext
def process_pipeline():
    """Avanza pipeline: títulos placeholder y runs de trazabilidad."""
    from pipeline.service import process_pipeline_job

    r = process_pipeline_job()
    click.echo(r)


@jobs_group.command("publish-due")
@with_appcontext
def publish_due():
    """Publica trabajos pendientes cuya fecha haya llegado."""
    from publishing.service import publish_due_jobs

    click.echo(publish_due_jobs())


@jobs_group.command("run-cycle")
@with_appcontext
def run_cycle():
    """Un ciclo: avanza pipeline (guion → TTS → render → cola de publicación) y publica lo debido."""
    from pipeline.orchestrator import run_production_cycle
    from publishing.service import publish_due_jobs

    r1 = run_production_cycle()
    r2 = publish_due_jobs()
    click.echo({"production": r1, "publish": r2})


@jobs_group.command("refresh-youtube-tokens")
@with_appcontext
def refresh_youtube_tokens():
    """Refresca access_token de canales con refresh_token."""
    from core.encryption import SecretVault, get_fernet
    from core.logging_config import get_logger
    from youtube import repository as yt_repo
    from youtube.service import refresh_channel_tokens

    log = get_logger(__name__)
    f = get_fernet(
        current_app.config.get("FERNET_KEY"),
        current_app.config["SECRET_KEY"],
        allow_dev_derive=not current_app.config.get("TESTING"),
    )
    vault = SecretVault(f)
    cid = current_app.config.get("GOOGLE_CLIENT_ID") or ""
    csec = current_app.config.get("GOOGLE_CLIENT_SECRET") or ""
    if not cid or not csec:
        click.echo("Faltan GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET; no se refresca.")
        return
    n = 0
    for ch in yt_repo.all_channels_for_refresh():
        try:
            refresh_channel_tokens(vault=vault, channel=ch, client_id=cid, client_secret=csec)
            n += 1
        except Exception as e:  # noqa: BLE001
            log.warning("youtube_refresh_failed", channel_id=ch.id, error=str(e))
    click.echo({"refreshed": n})


@jobs_group.command("sync-analytics")
@with_appcontext
def sync_analytics():
    """Sincroniza métricas de YouTube Analytics."""
    from analytics.service import sync_analytics_snapshots

    click.echo(sync_analytics_snapshots())


def register_cli(app):
    app.cli.add_command(jobs_group)
