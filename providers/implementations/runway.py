"""Runway (vídeo) — esqueleto con validación por presencia de API key."""

from __future__ import annotations

from typing import Any

from providers.base import BaseVideoProvider, ProviderValidationResult


class RunwayProvider(BaseVideoProvider):
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def validate_credentials(self) -> ProviderValidationResult:
        if not self._api_key or len(self._api_key) < 8:
            return ProviderValidationResult(False, "API key Runway no configurada")
        return ProviderValidationResult(
            True,
            "Clave presente; llamada real a Runway API pendiente (fase 3)",
        )

    def generate_clip(self, prompt: str, duration_sec: float, **kwargs: Any) -> str:
        raise NotImplementedError("Runway: implementar en fase 3")
