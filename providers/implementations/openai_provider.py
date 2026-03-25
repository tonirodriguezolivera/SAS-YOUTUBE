"""Proveedor OpenAI (LLM). Fase 2: llamadas reales; ahora validación opcional vía API."""

from __future__ import annotations

import json
from typing import Any

import httpx

from providers.base import BaseLLMProvider, ProviderValidationResult


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, *, base_url: str = "https://api.openai.com/v1") -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    def validate_credentials(self) -> ProviderValidationResult:
        if not self._api_key or len(self._api_key) < 8:
            return ProviderValidationResult(False, "API key vacía o demasiado corta")
        try:
            r = httpx.get(
                f"{self._base_url}/models",
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=15.0,
            )
            if r.status_code == 200:
                return ProviderValidationResult(True, "Conexión correcta con OpenAI")
            if r.status_code == 401:
                return ProviderValidationResult(False, "Credenciales inválidas (401)")
            return ProviderValidationResult(False, f"Error HTTP {r.status_code}")
        except httpx.RequestError as e:
            return ProviderValidationResult(False, f"Error de red: {e!s}")

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        model = kwargs.get("model", "gpt-4o-mini")
        payload = {"model": model, "messages": messages}
        r = httpx.post(
            f"{self._base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            content=json.dumps(payload),
            timeout=120.0,
        )
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]
