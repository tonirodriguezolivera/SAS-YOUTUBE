"""Modelos SQLAlchemy del dominio."""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from flask_login import UserMixin
from sqlalchemy import JSON, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class ChannelConnectionStatus(str, enum.Enum):
    connected = "connected"
    error = "error"
    expired = "expired"
    pending = "pending"


class AIProviderKind(str, enum.Enum):
    openai = "openai"
    google_gemini = "google_gemini"
    google_veo = "google_veo"
    runway = "runway"
    elevenlabs = "elevenlabs"


class AutomationStatus(str, enum.Enum):
    active = "active"
    paused = "paused"


class ContentFormat(str, enum.Enum):
    short = "short"
    long_form = "long_form"
    both = "both"


class PublishMode(str, enum.Enum):
    automatic = "automatic"
    review = "review"


class PipelineStage(str, enum.Enum):
    idea = "idea"
    title = "title"
    script = "script"
    production_plan = "production_plan"
    assets = "assets"
    render = "render"
    qa = "qa"
    published = "published"


class TitleHookCategory(str, enum.Enum):
    surprise = "surprise"
    contradiction = "contradiction"
    curiosity = "curiosity"
    common_mistake = "common_mistake"
    danger = "danger"
    impactful_story = "impactful_story"
    list_ranking = "list_ranking"
    transformation = "transformation"
    comparison = "comparison"
    myth_vs_reality = "myth_vs_reality"


class TitleCandidateStatus(str, enum.Enum):
    candidate = "candidate"
    approved = "approved"
    rejected = "rejected"
    used = "used"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"
    cancelled = "cancelled"


class UsageRecordType(str, enum.Enum):
    title = "title"
    hook = "hook"
    cta = "cta"
    theme = "theme"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(32), default=UserRole.user.value, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)

    # Recuperación de contraseña (preparado)
    password_reset_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    password_reset_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    youtube_channels: Mapped[list["YoutubeChannel"]] = relationship(back_populates="user")
    provider_configs: Mapped[list["AIProviderConfig"]] = relationship(back_populates="user")
    automations: Mapped[list["AutomationProfile"]] = relationship(back_populates="user")
    secrets: Mapped[list["UserSecret"]] = relationship(back_populates="user")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")


class UserSecret(db.Model):
    """Secretos genéricos cifrados por usuario (extensión futura)."""

    __tablename__ = "user_secrets"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_user_secret_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    value_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="secrets")


class YoutubeChannel(db.Model):
    __tablename__ = "youtube_channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    google_channel_id: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expiry: Mapped[datetime | None] = mapped_column(nullable=True)
    scopes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=ChannelConnectionStatus.connected.value)
    last_synced_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="youtube_channels")
    automations: Mapped[list["AutomationProfile"]] = relationship(back_populates="youtube_channel")

    __table_args__ = (
        UniqueConstraint("user_id", "google_channel_id", name="uq_user_yt_channel"),
        Index("ix_yt_channels_user_status", "user_id", "status"),
    )


class AIProviderConfig(db.Model):
    __tablename__ = "ai_provider_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    display_label: Mapped[str] = mapped_column(String(120), nullable=False)
    credentials_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    extra_settings_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_validated: Mapped[bool] = mapped_column(default=False, nullable=False)
    last_validated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="provider_configs")

    __table_args__ = (Index("ix_ai_provider_user_kind", "user_id", "kind"),)


class AutomationProfile(db.Model):
    __tablename__ = "automation_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    youtube_channel_id: Mapped[int | None] = mapped_column(
        ForeignKey("youtube_channels.id", ondelete="SET NULL"),
        nullable=True,
    )
    llm_provider_id: Mapped[int | None] = mapped_column(
        ForeignKey("ai_provider_configs.id", ondelete="SET NULL"),
        nullable=True,
    )
    video_provider_id: Mapped[int | None] = mapped_column(
        ForeignKey("ai_provider_configs.id", ondelete="SET NULL"),
        nullable=True,
    )
    voice_provider_id: Mapped[int | None] = mapped_column(
        ForeignKey("ai_provider_configs.id", ondelete="SET NULL"),
        nullable=True,
    )

    videos_per_day: Mapped[float] = mapped_column(default=1.0, nullable=False)
    duration_min_seconds: Mapped[int] = mapped_column(default=35, nullable=False)
    duration_max_seconds: Mapped[int] = mapped_column(default=55, nullable=False)
    language: Mapped[str] = mapped_column(String(16), default="es", nullable=False)
    tone: Mapped[str] = mapped_column(String(64), default="viral", nullable=False)
    cta_style: Mapped[str] = mapped_column(String(64), default="comment_subscribe", nullable=False)
    master_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")

    status: Mapped[str] = mapped_column(String(16), default=AutomationStatus.active.value, nullable=False)
    content_format: Mapped[str] = mapped_column(String(16), default=ContentFormat.short.value, nullable=False)
    publish_mode: Mapped[str] = mapped_column(String(16), default=PublishMode.review.value, nullable=False)
    schedule_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="automations")
    youtube_channel: Mapped["YoutubeChannel | None"] = relationship(
        foreign_keys=[youtube_channel_id],
        back_populates="automations",
    )
    llm_provider: Mapped["AIProviderConfig | None"] = relationship(foreign_keys=[llm_provider_id])
    video_provider: Mapped["AIProviderConfig | None"] = relationship(foreign_keys=[video_provider_id])
    voice_provider: Mapped["AIProviderConfig | None"] = relationship(foreign_keys=[voice_provider_id])
    content_ideas: Mapped[list["ContentIdea"]] = relationship(back_populates="automation")
    pipeline_runs: Mapped[list["PipelineRun"]] = relationship(back_populates="automation")


class ContentIdea(db.Model):
    """Fase A — estrategia editorial derivada del prompt maestro."""

    __tablename__ = "content_ideas"

    id: Mapped[int] = mapped_column(primary_key=True)
    automation_profile_id: Mapped[int] = mapped_column(
        ForeignKey("automation_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    strategy_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    automation: Mapped["AutomationProfile"] = relationship(back_populates="content_ideas")
    title_candidates: Mapped[list["TitleCandidate"]] = relationship(back_populates="content_idea")


class TitleCandidate(db.Model):
    __tablename__ = "title_candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    automation_profile_id: Mapped[int] = mapped_column(
        ForeignKey("automation_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    content_idea_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_ideas.id", ondelete="SET NULL"),
        nullable=True,
    )
    title_text: Mapped[str] = mapped_column(String(500), nullable=False)
    hook_category: Mapped[str] = mapped_column(String(32), nullable=False)
    score_total: Mapped[float] = mapped_column(default=0.0, nullable=False)
    quality_score: Mapped[float] = mapped_column(default=0.0, nullable=False)
    repetition_penalty: Mapped[float] = mapped_column(default=0.0, nullable=False)
    variants_json: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    reasoning_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    semantic_fingerprint: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    duplicate_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("title_candidates.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(24), default=TitleCandidateStatus.candidate.value)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    automation: Mapped["AutomationProfile"] = relationship()
    content_idea: Mapped["ContentIdea | None"] = relationship(back_populates="title_candidates")
    script_drafts: Mapped[list["ScriptDraft"]] = relationship(back_populates="title_candidate")


class ScriptDraft(db.Model):
    """Fase C — guion optimizado para retención."""

    __tablename__ = "script_drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title_candidate_id: Mapped[int] = mapped_column(
        ForeignKey("title_candidates.id", ondelete="CASCADE"),
        index=True,
    )
    hook_opening: Mapped[str | None] = mapped_column(Text, nullable=True)
    promise: Mapped[str | None] = mapped_column(Text, nullable=True)
    beats_json: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    micro_retentions_json: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    cta_organic: Mapped[str | None] = mapped_column(Text, nullable=True)
    closing: Mapped[str | None] = mapped_column(Text, nullable=True)
    voiceover_final: Mapped[str | None] = mapped_column(Text, nullable=True)
    subtitles_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_seo: Mapped[str | None] = mapped_column(Text, nullable=True)
    hashtags_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    thumbnail_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    scene_prompts_json: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    format_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    quality_score: Mapped[float] = mapped_column(default=0.0, nullable=False)
    publish_readiness_score: Mapped[float] = mapped_column(default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)

    title_candidate: Mapped["TitleCandidate"] = relationship(back_populates="script_drafts")
    production_plans: Mapped[list["ProductionPlan"]] = relationship(back_populates="script_draft")
    render_jobs: Mapped[list["RenderJob"]] = relationship(back_populates="script_draft")


class ProductionPlan(db.Model):
    """Fase D — plan de producción por escenas."""

    __tablename__ = "production_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    script_draft_id: Mapped[int] = mapped_column(
        ForeignKey("script_drafts.id", ondelete="CASCADE"),
        index=True,
    )
    scenes_json: Mapped[list | dict] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    script_draft: Mapped["ScriptDraft"] = relationship(back_populates="production_plans")
    assets: Mapped[list["Asset"]] = relationship(back_populates="production_plan")


class Asset(db.Model):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    production_plan_id: Mapped[int] = mapped_column(
        ForeignKey("production_plans.id", ondelete="CASCADE"),
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    scene_index: Mapped[int | None] = mapped_column(nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    provider_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    production_plan: Mapped["ProductionPlan"] = relationship(back_populates="assets")


class RenderJob(db.Model):
    __tablename__ = "render_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    script_draft_id: Mapped[int] = mapped_column(
        ForeignKey("script_drafts.id", ondelete="CASCADE"),
        index=True,
    )
    status: Mapped[str] = mapped_column(String(24), default=JobStatus.pending.value, nullable=False)
    output_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    qa_score: Mapped[float | None] = mapped_column(nullable=True)
    qa_details_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    log_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    script_draft: Mapped["ScriptDraft"] = relationship(back_populates="render_jobs")
    publication_jobs: Mapped[list["PublicationJob"]] = relationship(back_populates="render_job")


class PublicationJob(db.Model):
    __tablename__ = "publication_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    render_job_id: Mapped[int] = mapped_column(
        ForeignKey("render_jobs.id", ondelete="CASCADE"),
        index=True,
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    privacy_status: Mapped[str] = mapped_column(String(24), default="private", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default=JobStatus.pending.value, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)

    render_job: Mapped["RenderJob"] = relationship(back_populates="publication_jobs")
    published_video: Mapped["PublishedVideo | None"] = relationship(back_populates="publication_job")


class PublishedVideo(db.Model):
    __tablename__ = "published_videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    youtube_channel_id: Mapped[int] = mapped_column(
        ForeignKey("youtube_channels.id", ondelete="CASCADE"),
        index=True,
    )
    publication_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("publication_jobs.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    youtube_video_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    user: Mapped["User"] = relationship()
    youtube_channel: Mapped["YoutubeChannel"] = relationship()
    publication_job: Mapped["PublicationJob | None"] = relationship(back_populates="published_video")
    analytics_snapshots: Mapped[list["AnalyticsSnapshot"]] = relationship(back_populates="published_video")


class AnalyticsSnapshot(db.Model):
    __tablename__ = "analytics_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    published_video_id: Mapped[int] = mapped_column(
        ForeignKey("published_videos.id", ondelete="CASCADE"),
        index=True,
    )
    captured_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    metrics_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    published_video: Mapped["PublishedVideo"] = relationship(back_populates="analytics_snapshots")


class ContentUsageRecord(db.Model):
    """Base para penalizar repetición de títulos, hooks, CTAs y temas."""

    __tablename__ = "content_usage_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    automation_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("automation_profiles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    usage_type: Mapped[str] = mapped_column(String(24), nullable=False)
    normalized_fingerprint: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    sample_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)

    __table_args__ = (Index("ix_usage_user_type_fp", "user_id", "usage_type", "normalized_fingerprint"),)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False, index=True)

    user: Mapped["User | None"] = relationship(back_populates="audit_logs")


class PipelineRun(db.Model):
    """
    Trazabilidad visual: una fila por pieza en producción con estado por etapa.
    """

    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    automation_profile_id: Mapped[int] = mapped_column(
        ForeignKey("automation_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    stages_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    current_stage: Mapped[str] = mapped_column(String(32), default=PipelineStage.idea.value)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_idea_id: Mapped[int | None] = mapped_column(ForeignKey("content_ideas.id", ondelete="SET NULL"))
    title_candidate_id: Mapped[int | None] = mapped_column(ForeignKey("title_candidates.id", ondelete="SET NULL"))
    script_draft_id: Mapped[int | None] = mapped_column(ForeignKey("script_drafts.id", ondelete="SET NULL"))
    production_plan_id: Mapped[int | None] = mapped_column(ForeignKey("production_plans.id", ondelete="SET NULL"))
    render_job_id: Mapped[int | None] = mapped_column(ForeignKey("render_jobs.id", ondelete="SET NULL"))
    publication_job_id: Mapped[int | None] = mapped_column(ForeignKey("publication_jobs.id", ondelete="SET NULL"))
    published_video_id: Mapped[int | None] = mapped_column(ForeignKey("published_videos.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)

    automation: Mapped["AutomationProfile"] = relationship(back_populates="pipeline_runs")
