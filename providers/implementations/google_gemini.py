"""Google Gemini / Veo (placeholder LLM + extensión vídeo en fases posteriores)."""

from __future__ import annotations

from typing import Any

import httpx

from providers.base import BaseLLMProvider, BaseVideoProvider, ProviderValidationResult


class GoogleGeminiProvider(BaseLLMProvider):
    """Usa Gemini API REST para validación y completions simples."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def validate_credentials(self) -> ProviderValidationResult:
        if not self._api_key:
            return ProviderValidationResult(False, "API key vacía")
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self._api_key}"
        try:
            r = httpx.get(url, timeout=15.0)
            if r.status_code == 200:
                return ProviderValidationResult(True, "Gemini API accesible")
            if r.status_code in (400, 403):
                return ProviderValidationResult(False, "Credenciales o permisos incorrectos")
            return ProviderValidationResult(False, f"Error HTTP {r.status_code}")
        except httpx.RequestError as e:
            return ProviderValidationResult(False, f"Error de red: {e!s}")

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        model = kwargs.get("model", "gemini-1.5-flash")
        # Convierte messages a un solo bloque de texto para el endpoint generateContent
        text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payload = {"contents": [{"parts": [{"text": text}]}]}
        r = httpx.post(
            url,
            params={"key": self._api_key},
            json=payload,
            timeout=120.0,
        )
        r.raise_for_status()
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


class GoogleVeoProvider(BaseVideoProvider):
    """Reservado para Veo / generación de vídeo Google (esqueleto)."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def validate_credentials(self) -> ProviderValidationResult:
        if not self._api_key:
            return ProviderValidationResult(False, "API key vacía")
        return ProviderValidationResult(
            True,
            "Validación genérica: integración Veo pendiente (fase 3)",
        )

    def generate_clip(self, prompt: str, duration_sec: float, **kwargs: Any) -> str:
        raise NotImplementedError("Google Veo: implementar en fase 3")
