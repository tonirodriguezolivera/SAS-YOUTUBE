"""Contratos comunes para proveedores de IA (LLM, vídeo, voz)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ProviderValidationResult:
    ok: bool
    message: str


class BaseLLMProvider(ABC):
    """Texto / razonamiento (OpenAI, Gemini, etc.)."""

    kind: str = "llm"

    @abstractmethod
    def validate_credentials(self) -> ProviderValidationResult:
        """Comprueba credenciales (test de conexión ligero)."""

    @abstractmethod
    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Genera una respuesta de chat/completion."""


class BaseVideoProvider(ABC):
    """Generación de vídeo o clips (Runway, Veo, etc.)."""

    kind: str = "video"

    @abstractmethod
    def validate_credentials(self) -> ProviderValidationResult:
        """Comprueba credenciales."""

    @abstractmethod
    def generate_clip(self, prompt: str, duration_sec: float, **kwargs: Any) -> str:
        """
        Devuelve referencia al asset (URL, id de job o ruta local).
        La implementación real dependerá del proveedor.
        """


class BaseVoiceProvider(ABC):
    """Síntesis de voz / TTS."""

    kind: str = "voice"

    @abstractmethod
    def validate_credentials(self) -> ProviderValidationResult:
        """Comprueba credenciales."""

    @abstractmethod
    def synthesize(self, text: str, voice_id: str | None = None, **kwargs: Any) -> bytes:
        """Devuelve audio en bruto (p. ej. mp3)."""
