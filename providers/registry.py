"""Factoría de proveedores a partir de credenciales descifradas."""

from __future__ import annotations

import json
from typing import Any

from core.models import AIProviderKind
from providers.base import BaseLLMProvider, BaseVideoProvider, BaseVoiceProvider
from providers.implementations.elevenlabs import ElevenLabsProvider
from providers.implementations.google_gemini import GoogleGeminiProvider, GoogleVeoProvider
from providers.implementations.openai_provider import OpenAIProvider
from providers.implementations.runway import RunwayProvider


def _parse_credentials(blob: str) -> dict[str, Any]:
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return {"api_key": blob}


def build_llm_provider(kind: str, credentials_json: str) -> BaseLLMProvider:
    data = _parse_credentials(credentials_json)
    key = data.get("api_key") or data.get("key") or ""
    if kind == AIProviderKind.openai.value:
        return OpenAIProvider(key, base_url=data.get("base_url", "https://api.openai.com/v1"))
    if kind == AIProviderKind.google_gemini.value:
        return GoogleGeminiProvider(key)
    raise ValueError(f"Proveedor LLM no soportado: {kind}")


def build_video_provider(kind: str, credentials_json: str) -> BaseVideoProvider:
    data = _parse_credentials(credentials_json)
    key = data.get("api_key") or data.get("key") or ""
    if kind == AIProviderKind.runway.value:
        return RunwayProvider(key)
    if kind == AIProviderKind.google_veo.value:
        return GoogleVeoProvider(key)
    raise ValueError(f"Proveedor de vídeo no soportado: {kind}")


def build_voice_provider(kind: str, credentials_json: str) -> BaseVoiceProvider:
    data = _parse_credentials(credentials_json)
    key = data.get("api_key") or data.get("key") or ""
    if kind == AIProviderKind.elevenlabs.value:
        vid = data.get("voice_id") or data.get("voiceId")
        return ElevenLabsProvider(key, default_voice_id=vid if isinstance(vid, str) else None)
    raise ValueError(f"Proveedor de voz no soportado: {kind}")
