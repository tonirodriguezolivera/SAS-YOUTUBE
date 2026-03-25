"""
Orquestación del pipeline editorial (fases A–I).

Incluye LLM (OpenAI/Gemini) para estrategia y títulos cuando el perfil tiene proveedor.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import not_, select
from sqlalchemy.orm.attributes import flag_modified

from core.logging_config import get_logger
from core.models import (
    AutomationProfile,
    ContentIdea,
    PipelineRun,
    PipelineStage,
    TitleCandidate,
    TitleHookCategory,
)
from extensions import db
from pipeline import repetition

log = get_logger(__name__)


def seed_content_for_profile(
    profile: AutomationProfile,
    *,
    vault=None,
    use_llm: bool = True,
) -> ContentIdea:
    """Crea ContentIdea; si hay LLM y vault, rellena strategy_json con el modelo."""
    strategy: dict[str, Any] = {
        "niches": [],
        "pillars": [],
        "series": [],
        "tone": profile.tone,
        "narrative_style": "retention_optimized",
        "optimization_rules": [],
        "cta_framework": profile.cta_style,
        "seed_ideas": [],
        "master_prompt_excerpt": (profile.master_prompt or "")[:2000],
    }
    if use_llm and vault and profile.llm_provider_id:
        from pipeline.llm_stages import generate_strategy_llm

        extra = generate_strategy_llm(profile, vault)
        for key in (
            "niches",
            "pillars",
            "series",
            "tone",
            "narrative_style",
            "optimization_rules",
            "cta_framework",
            "seed_ideas",
            "summary",
        ):
            if key in extra and extra[key]:
                strategy[key] = extra[key]
    idea = ContentIdea(automation_profile_id=profile.id, strategy_json=strategy, status="seeded")
    db.session.add(idea)
    db.session.commit()
    log.info("content_idea_seeded", automation_id=profile.id, idea_id=idea.id)
    return idea


def seed_content_all_active() -> dict:
    """Job: crea una nueva idea de contenido por cada automatización activa."""
    from flask import current_app

    from core.vault_util import secret_vault_from_config

    profiles = db.session.query(AutomationProfile).filter(AutomationProfile.status == "active").all()
    vault = secret_vault_from_config(current_app.config)
    created = 0
    for p in profiles:
        seed_content_for_profile(p, vault=vault, use_llm=True)
        created += 1
    log.info("seed_content_job", profiles=len(profiles), ideas_created=created)
    return {"profiles": len(profiles), "ideas_created": created}


def _persist_title_specs(
    profile: AutomationProfile,
    idea: ContentIdea,
    specs: list[dict[str, Any]],
) -> list[TitleCandidate]:
    user_id = profile.user_id
    out: list[TitleCandidate] = []
    for i, spec in enumerate(specs):
        title = spec["title"]
        hook = spec["hook_category"]
        fp = repetition.fingerprint(title)
        pen = repetition.repetition_penalty_for_title(
            user_id=user_id,
            automation_profile_id=profile.id,
            title=title,
        )
        base_score = float(spec.get("score_total", spec.get("score", 0.75)))
        quality = max(0.0, base_score - pen)
        variants = spec.get("variants_json") or spec.get("variants")
        if isinstance(variants, list):
            vj: list | dict = [{"title": v, "hook_variant": f"v{j}"} for j, v in enumerate(variants) if v]
        else:
            vj = [{"title": title, "hook_variant": f"v{i}"}]
        tc = TitleCandidate(
            automation_profile_id=profile.id,
            content_idea_id=idea.id,
            title_text=title,
            hook_category=hook,
            score_total=base_score,
            quality_score=quality,
            repetition_penalty=pen,
            variants_json=vj,
            reasoning_summary=spec.get("reasoning_summary") or spec.get("reasoning") or "",
            semantic_fingerprint=fp,
            status="candidate",
        )
        db.session.add(tc)
        out.append(tc)
    db.session.commit()
    return out


def generate_title_batch_placeholder(profile: AutomationProfile, idea: ContentIdea, count: int = 8) -> list[TitleCandidate]:
    """Títulos de ejemplo con scores y penalización por repetición."""
    hooks = list(TitleHookCategory)
    specs = []
    for i in range(count):
        title = f"Borrador {i + 1}: ángulo {hooks[i % len(hooks)].value} — {profile.name}"
        specs.append(
            {
                "title": title,
                "hook_category": hooks[i % len(hooks)].value,
                "score_total": 0.75 - 0.1 * i,
                "reasoning_summary": "Placeholder: sin LLM configurado.",
            }
        )
    return _persist_title_specs(profile, idea, specs)


def generate_title_batch(
    profile: AutomationProfile,
    idea: ContentIdea,
    *,
    vault,
    count: int = 8,
) -> list[TitleCandidate]:
    """LLM si hay proveedor; si no, placeholders."""
    if profile.llm_provider_id and vault:
        from pipeline.llm_stages import generate_titles_llm

        items = generate_titles_llm(profile, idea, vault, count=count)
        if items:
            specs = [
                {
                    "title": it["title"],
                    "hook_category": it["hook_category"],
                    "score_total": it["score"],
                    "reasoning_summary": it.get("reasoning") or "",
                    "variants": it.get("variants") or [],
                }
                for it in items
            ]
            return _persist_title_specs(profile, idea, specs)
    return generate_title_batch_placeholder(profile, idea, count=count)


def ensure_pipeline_run(
    profile: AutomationProfile,
    *,
    idea: ContentIdea | None = None,
    first_title: TitleCandidate | None = None,
    display_name: str = "",
) -> PipelineRun:
    """Crea trazabilidad visual inicial para una pieza."""
    stages = {
        PipelineStage.idea.value: {"status": "pending", "at": None, "log": []},
        PipelineStage.title.value: {"status": "pending", "at": None, "log": []},
        PipelineStage.script.value: {"status": "pending", "at": None, "log": []},
        PipelineStage.production_plan.value: {"status": "pending", "at": None, "log": []},
        PipelineStage.assets.value: {"status": "pending", "at": None, "log": []},
        PipelineStage.render.value: {"status": "pending", "at": None, "log": []},
        PipelineStage.qa.value: {"status": "pending", "at": None, "log": []},
        PipelineStage.published.value: {"status": "pending", "at": None, "log": []},
    }
    run = PipelineRun(
        automation_profile_id=profile.id,
        display_name=display_name or profile.name,
        stages_json=stages,
        current_stage=PipelineStage.idea.value,
        content_idea_id=idea.id if idea else None,
        title_candidate_id=first_title.id if first_title else None,
    )
    db.session.add(run)
    db.session.commit()
    return run


def _ideas_without_titles():
    subq = select(TitleCandidate.content_idea_id).where(TitleCandidate.content_idea_id.isnot(None)).distinct()
    return db.session.query(ContentIdea).filter(not_(ContentIdea.id.in_(subq))).all()


def process_pipeline_job() -> dict:
    """
    Job: para ideas sin títulos, genera lote (LLM o placeholder) y actualiza/crea PipelineRun.
    """
    from flask import current_app

    from core.vault_util import secret_vault_from_config

    vault = secret_vault_from_config(current_app.config)
    ideas = _ideas_without_titles()
    titles_total = 0
    runs = 0
    for idea in ideas:
        profile = db.session.get(AutomationProfile, idea.automation_profile_id)
        if not profile or profile.status != "active":
            continue
        titles = generate_title_batch(profile, idea, vault=vault, count=6)
        titles_total += len(titles)
        excerpt = (idea.strategy_json or {}).get("master_prompt_excerpt", "")[:80]
        run = ensure_pipeline_run(profile, idea=idea, first_title=titles[0] if titles else None, display_name=excerpt)
        run.stages_json[PipelineStage.idea.value]["status"] = "done"
        run.stages_json[PipelineStage.title.value]["status"] = "running"
        flag_modified(run, "stages_json")
        db.session.commit()
        runs += 1
    log.info("process_pipeline_job", ideas=len(ideas), titles=titles_total, runs=runs)
    return {"ideas_processed": len(ideas), "titles": titles_total, "pipeline_runs": runs}
