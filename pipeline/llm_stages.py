"""Generacion de estrategia, titulos y guion vía LLM (OpenAI / Gemini)."""

from __future__ import annotations

import json
from typing import Any

from core.models import AIProviderConfig, AutomationProfile, ContentIdea, TitleHookCategory
from core.encryption import SecretVault
from core.logging_config import get_logger
from extensions import db
from pipeline.json_llm import extract_json_block
from providers.registry import build_llm_provider

log = get_logger(__name__)

HOOK_VALUES = {e.value for e in TitleHookCategory}


def _llm_for_profile(profile: AutomationProfile, vault: SecretVault):
    if not profile.llm_provider_id:
        return None
    row = db.session.get(AIProviderConfig, profile.llm_provider_id)
    if not row or row.user_id != profile.user_id:
        return None
    plain = vault.decrypt(row.credentials_encrypted)
    return build_llm_provider(row.kind, plain)


def _chat(llm, system: str, user: str) -> str:
    return llm.complete(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        model=None,
    )


def generate_strategy_llm(profile: AutomationProfile, vault: SecretVault) -> dict[str, Any]:
    llm = _llm_for_profile(profile, vault)
    if not llm:
        return {}
    system = (
        "Eres estratega de contenido para YouTube Shorts. Responde SOLO JSON valido, sin markdown."
    )
    user = f"""Prompt maestro del canal:
---
{profile.master_prompt[:12000]}
---
Idioma: {profile.language}. Tono: {profile.tone}. CTA preferido: {profile.cta_style}.
Devuelve JSON con claves: niches (array strings), pillars (array), series (array), tone (string),
narrative_style (string), optimization_rules (array strings), cta_framework (string),
seed_ideas (array de 8 ideas cortas), summary (string breve)."""
    raw = _chat(llm, system, user)
    data = extract_json_block(raw)
    if not isinstance(data, dict):
        return {}
    return data


def generate_titles_llm(
    profile: AutomationProfile,
    idea: ContentIdea,
    vault: SecretVault,
    *,
    count: int = 6,
) -> list[dict[str, Any]]:
    llm = _llm_for_profile(profile, vault)
    if not llm:
        return []
    strategy = idea.strategy_json or {}
    system = "Eres experto en titulos virales para YouTube Shorts. Responde SOLO JSON."
    user = f"""Contexto estrategia: {json.dumps(strategy, ensure_ascii=False)[:8000]}
Genera {count} titulos. Cada uno: title (string), hook_category (una de: {", ".join(sorted(HOOK_VALUES))}),
score (0-1 float), reasoning (string breve), variants (array de 2 titulos alternativos).
Formato: {{"titles":[...]}}"""
    raw = _chat(llm, system, user)
    data = extract_json_block(raw)
    titles = data.get("titles") if isinstance(data, dict) else None
    if not isinstance(titles, list):
        return []
    out = []
    for item in titles:
        if not isinstance(item, dict):
            continue
        title = (item.get("title") or "").strip()[:500]
        if not title:
            continue
        hook = (item.get("hook_category") or "curiosity").lower()
        if hook not in HOOK_VALUES:
            hook = "curiosity"
        out.append(
            {
                "title": title,
                "hook_category": hook,
                "score": float(item.get("score") or 0.7),
                "reasoning": (item.get("reasoning") or "")[:2000],
                "variants": item.get("variants") if isinstance(item.get("variants"), list) else [],
            }
        )
    return out


def generate_script_llm(
    profile: AutomationProfile,
    title_text: str,
    hook_category: str,
    vault: SecretVault,
) -> dict[str, Any]:
    llm = _llm_for_profile(profile, vault)
    if not llm:
        return {}
    system = (
        "Eres guionista de Shorts con alta retencion. Responde SOLO JSON valido. "
        "voiceover_final debe ser el texto completo a locutar, fluido, en parrafos cortos."
    )
    user = f"""Titulo elegido: {title_text}
Tipo de gancho: {hook_category}
Prompt maestro: {profile.master_prompt[:8000]}
Duracion objetivo: {profile.duration_min_seconds}-{profile.duration_max_seconds} segundos.
Idioma: {profile.language}. Tono: {profile.tone}.

JSON con claves:
hook_opening, promise, beats (array de {{text, seconds}}), body, micro_retentions (array strings),
cta_organic, closing, voiceover_final (texto locution completo),
subtitles_text (opcional, version corta), description_seo, hashtags (array strings),
thumbnail_prompt, scene_prompts (array strings, una por beat aprox),
format_kind (ej. short_narrated), quality_notes (string)."""
    raw = _chat(llm, system, user)
    data = extract_json_block(raw)
    return data if isinstance(data, dict) else {}
