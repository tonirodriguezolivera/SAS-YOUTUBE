"""ElevenLabs TTS — validación y síntesis vía API REST."""

from __future__ import annotations

from typing import Any

import httpx

from providers.base import BaseVoiceProvider, ProviderValidationResult


class ElevenLabsProvider(BaseVoiceProvider):
    def __init__(self, api_key: str, *, default_voice_id: str | None = None) -> None:
        self._api_key = api_key
        self._default_voice_id = default_voice_id

    def validate_credentials(self) -> ProviderValidationResult:
        if not self._api_key:
            return ProviderValidationResult(False, "API key vacía")
        try:
            r = httpx.get(
                "https://api.elevenlabs.io/v1/user",
                headers={"xi-api-key": self._api_key},
                timeout=15.0,
            )
            if r.status_code == 200:
                return ProviderValidationResult(True, "ElevenLabs: usuario válido")
            if r.status_code == 401:
                return ProviderValidationResult(False, "API key inválida")
            return ProviderValidationResult(False, f"Error HTTP {r.status_code}")
        except httpx.RequestError as e:
            return ProviderValidationResult(False, f"Error de red: {e!s}")

    def synthesize(self, text: str, voice_id: str | None = None, **kwargs: Any) -> bytes:
        vid = voice_id or self._default_voice_id
        if not vid:
            raise ValueError("ElevenLabs: falta voice_id (credenciales JSON o argumento)")
        text = (text or "").strip()
        if not text:
            raise ValueError("ElevenLabs: texto vacío")
        model_id = kwargs.get("model_id") or "eleven_multilingual_v2"
        out_fmt = kwargs.get("output_format") or "mp3_44100_128"
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}"
        payload = {
            "text": text[:500000],
            "model_id": model_id,
        }
        r = httpx.post(
            url,
            headers={
                "xi-api-key": self._api_key,
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
            },
            json=payload,
            params={"output_format": out_fmt},
            timeout=120.0,
        )
        r.raise_for_status()
        return r.content
