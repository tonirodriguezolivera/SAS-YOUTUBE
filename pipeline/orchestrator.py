"""
Encadena guion (LLM) → plan → TTS → FFmpeg → PublicationJob.
Ejecutar dentro de app context (p. ej. `flask jobs run-cycle`).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import exists

from core.logging_config import get_logger
from core.models import (
    AIProviderConfig,
    Asset,
    AutomationProfile,
    JobStatus,
    ProductionPlan,
    PublicationJob,
    PublishMode,
    RenderJob,
    ScriptDraft,
    TitleCandidate,
)
from core.vault_util import secret_vault_from_config
from extensions import db
from pipeline import llm_stages
from pipeline.video_render import ffmpeg_available, render_vertical_mp4
from providers.registry import build_voice_provider

log = get_logger(__name__)


def _voice_provider_for_profile(profile: AutomationProfile, vault):
    if not profile.voice_provider_id:
        return None
    row = db.session.get(AIProviderConfig, profile.voice_provider_id)
    if not row or row.user_id != profile.user_id:
        return None
    plain = vault.decrypt(row.credentials_encrypted)
    return build_voice_provider(row.kind, plain)


def _title_without_script(profile: AutomationProfile) -> TitleCandidate | None:
    has_script = exists().where(ScriptDraft.title_candidate_id == TitleCandidate.id)
    return (
        db.session.query(TitleCandidate)
        .filter(
            TitleCandidate.automation_profile_id == profile.id,
            ~has_script,
        )
        .order_by(TitleCandidate.quality_score.desc())
        .first()
    )


def _script_without_plan(profile: AutomationProfile) -> ScriptDraft | None:
    return (
        db.session.query(ScriptDraft)
        .join(TitleCandidate)
        .outerjoin(ProductionPlan, ProductionPlan.script_draft_id == ScriptDraft.id)
        .filter(
            TitleCandidate.automation_profile_id == profile.id,
            ProductionPlan.id.is_(None),
        )
        .first()
    )


def _plan_for_script(script: ScriptDraft) -> ProductionPlan | None:
    return (
        db.session.query(ProductionPlan)
        .filter(ProductionPlan.script_draft_id == script.id)
        .order_by(ProductionPlan.id.desc())
        .first()
    )


def _voice_asset(plan: ProductionPlan) -> Asset | None:
    return (
        db.session.query(Asset)
        .filter(
            Asset.production_plan_id == plan.id,
            Asset.kind.in_(("voice", "audio", "tts")),
        )
        .first()
    )


def _successful_render(script: ScriptDraft) -> RenderJob | None:
    return (
        db.session.query(RenderJob)
        .filter(
            RenderJob.script_draft_id == script.id,
            RenderJob.status == JobStatus.success.value,
            RenderJob.output_path.isnot(None),
        )
        .order_by(RenderJob.id.desc())
        .first()
    )


def _pending_or_failed_render(script: ScriptDraft) -> RenderJob | None:
    return (
        db.session.query(RenderJob)
        .filter(RenderJob.script_draft_id == script.id)
        .order_by(RenderJob.id.desc())
        .first()
    )


def _build_scenes_from_script(script: ScriptDraft) -> list[dict[str, Any]]:
    beats = script.beats_json or []
    vo = (script.voiceover_final or script.body or "").strip()
    duration = 45
    if isinstance(beats, list) and beats:
        try:
            duration = max(15, min(180, int(sum(float(b.get("seconds") or 5) for b in beats if isinstance(b, dict)))))
        except (TypeError, ValueError):
            duration = 45
    return [
        {
            "index": 0,
            "duration_sec": duration,
            "asset_type": "voice_plus_visual",
            "narration_text": vo[:20000],
            "on_screen_text": "",
            "transition": "cut",
        }
    ]


def advance_profile_pipeline(profile: AutomationProfile, config: dict) -> dict[str, Any]:
    """Un paso de avance por invocación (idempotente en la medida posible)."""
    out: dict[str, Any] = {"profile_id": profile.id, "step": None}
    vault = secret_vault_from_config(config)
    media_root = Path(config["MEDIA_ROOT"])

    if not profile.youtube_channel_id:
        out["skip"] = "sin_canal_youtube"
        return out

    tc = _title_without_script(profile)
    if tc:
        if profile.llm_provider_id:
            data = llm_stages.generate_script_llm(profile, tc.title_text, tc.hook_category, vault)
            if not data:
                out["skip"] = "llm_sin_guion"
                return out
        else:
            data = {
                "hook_opening": tc.title_text,
                "promise": "",
                "beats": [{"text": "intro", "seconds": 20}],
                "body": "",
                "voiceover_final": (
                    f"{tc.title_text}. "
                    "Vídeo generado en modo rápido sin proveedor LLM; "
                    "configura OpenAI o Gemini en el perfil para guiones más ricos."
                ),
                "description_seo": tc.title_text,
                "hashtags": [],
                "format_kind": "short_placeholder",
            }
        beats = data.get("beats")
        if not isinstance(beats, list):
            beats = []
        hashtags = data.get("hashtags")
        if not isinstance(hashtags, list):
            hashtags = []
        sd = ScriptDraft(
            title_candidate_id=tc.id,
            hook_opening=data.get("hook_opening"),
            promise=data.get("promise"),
            beats_json=beats,
            body=data.get("body"),
            micro_retentions_json=data.get("micro_retentions")
            if isinstance(data.get("micro_retentions"), list)
            else None,
            cta_organic=data.get("cta_organic"),
            closing=data.get("closing"),
            voiceover_final=data.get("voiceover_final") or data.get("body"),
            subtitles_text=data.get("subtitles_text"),
            description_seo=data.get("description_seo"),
            hashtags_json=hashtags,
            thumbnail_prompt=data.get("thumbnail_prompt"),
            scene_prompts_json=data.get("scene_prompts") if isinstance(data.get("scene_prompts"), list) else None,
            format_kind=data.get("format_kind"),
            status="draft",
        )
        db.session.add(sd)
        db.session.commit()
        out["step"] = "script_draft"
        out["script_draft_id"] = sd.id
        return out

    sd = _script_without_plan(profile)
    if sd:
        plan = ProductionPlan(script_draft_id=sd.id, scenes_json=_build_scenes_from_script(sd))
        db.session.add(plan)
        db.session.commit()
        out["step"] = "production_plan"
        out["production_plan_id"] = plan.id
        return out

    # Plan existente: localizar script vía plan
    plan_row = (
        db.session.query(ProductionPlan)
        .join(ScriptDraft)
        .join(TitleCandidate)
        .filter(TitleCandidate.automation_profile_id == profile.id)
        .order_by(ProductionPlan.id.desc())
        .first()
    )
    if not plan_row:
        out["skip"] = "sin_plan"
        return out

    script = plan_row.script_draft
    voice_path: Path | None = None
    asset = _voice_asset(plan_row)
    if asset and asset.storage_path:
        p = Path(asset.storage_path)
        if p.is_file():
            voice_path = p

    if voice_path is None:
        prov = _voice_provider_for_profile(profile, vault)
        if not prov:
            out["skip"] = "sin_proveedor_voz"
            return out
        text = (script.voiceover_final or script.body or "").strip()
        if not text:
            out["skip"] = "guion_sin_texto_voz"
            return out
        default_vid = (config.get("ELEVENLABS_DEFAULT_VOICE_ID") or "").strip() or None
        try:
            audio_bytes = prov.synthesize(text, voice_id=default_vid)
        except Exception as e:  # noqa: BLE001
            log.exception("tts_failed", profile_id=profile.id)
            out["error"] = str(e)
            return out
        rel = Path("automation") / str(profile.id) / "plans" / str(plan_row.id)
        dest_dir = media_root / rel
        dest_dir.mkdir(parents=True, exist_ok=True)
        audio_file = dest_dir / "voiceover.mp3"
        audio_file.write_bytes(audio_bytes)
        if asset:
            asset.storage_path = str(audio_file.resolve())
            asset.meta_json = {"format": "mp3"}
        else:
            asset = Asset(
                production_plan_id=plan_row.id,
                kind="voice",
                scene_index=0,
                storage_path=str(audio_file.resolve()),
                meta_json={"format": "mp3"},
            )
            db.session.add(asset)
        db.session.commit()
        voice_path = audio_file
        out["step"] = "tts"
        return out

    rend = _successful_render(script)
    if rend and rend.output_path and Path(rend.output_path).is_file():
        pass  # ya hay vídeo
    else:
        if not ffmpeg_available():
            out["skip"] = "ffmpeg_no_disponible"
            return out
        job = _pending_or_failed_render(script)
        if not job or job.status == JobStatus.success.value:
            job = RenderJob(script_draft_id=script.id, status=JobStatus.pending.value)
            db.session.add(job)
            db.session.commit()
        job.status = JobStatus.running.value
        job.started_at = datetime.now(timezone.utc)
        job.log_excerpt = None
        db.session.commit()
        try:
            out_mp4 = media_root / "automation" / str(profile.id) / "renders" / f"{job.id}.mp4"
            render_vertical_mp4(voice_path, out_mp4)
            job.status = JobStatus.success.value
            job.output_path = str(out_mp4.resolve())
            job.finished_at = datetime.now(timezone.utc)
            db.session.commit()
            out["step"] = "render"
            out["render_job_id"] = job.id
        except Exception as e:  # noqa: BLE001
            job.status = JobStatus.failed.value
            job.log_excerpt = str(e)[:4000]
            job.finished_at = datetime.now(timezone.utc)
            db.session.commit()
            log.exception("render_failed", profile_id=profile.id)
            out["error"] = str(e)
        return out

    rend = _successful_render(script)
    if not rend or not rend.output_path:
        out["skip"] = "sin_render"
        return out

    existing_pub = (
        db.session.query(PublicationJob)
        .filter(
            PublicationJob.render_job_id == rend.id,
            PublicationJob.status == JobStatus.success.value,
        )
        .first()
    )
    if existing_pub:
        out["skip"] = "ya_publicado"
        return out

    pending = (
        db.session.query(PublicationJob)
        .filter(PublicationJob.render_job_id == rend.id)
        .first()
    )
    if pending:
        out["skip"] = "publicacion_pendiente"
        return out

    privacy = "private"
    if profile.publish_mode == PublishMode.automatic.value:
        privacy = (config.get("YOUTUBE_DEFAULT_PRIVACY") or "private").lower()
        if privacy not in ("public", "private", "unlisted"):
            privacy = "private"

    pub = PublicationJob(
        render_job_id=rend.id,
        scheduled_at=datetime.now(timezone.utc),
        privacy_status=privacy,
        status=JobStatus.pending.value,
    )
    db.session.add(pub)
    db.session.commit()
    out["step"] = "publication_scheduled"
    out["publication_job_id"] = pub.id
    return out


def run_production_cycle() -> dict[str, Any]:
    from flask import current_app

    cfg = current_app.config
    profiles = (
        db.session.query(AutomationProfile)
        .filter(AutomationProfile.status == "active")
        .order_by(AutomationProfile.id)
        .all()
    )
    results = []
    for p in profiles:
        try:
            results.append(advance_profile_pipeline(p, cfg))
        except Exception as e:  # noqa: BLE001
            log.exception("orchestrator_profile_error", profile_id=p.id)
            results.append({"profile_id": p.id, "error": str(e)})
    return {"profiles": len(profiles), "results": results}
