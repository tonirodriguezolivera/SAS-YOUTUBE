"""Montaje mínimo: vídeo vertical + audio (FFmpeg en PATH)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from core.logging_config import get_logger

log = get_logger(__name__)


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def render_vertical_mp4(
    audio_path: Path,
    output_path: Path,
    *,
    width: int = 1080,
    height: int = 1920,
    color: str = "0x1a0a0a",
) -> None:
    """
    Genera MP4 H.264 + AAC: fondo sólido + audio.
    """
    if not ffmpeg_available():
        raise RuntimeError("FFmpeg no está en PATH; instálalo y reinicia la terminal.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c={color}:s={width}x{height}",
        "-i",
        str(audio_path),
        "-shortest",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(output_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        log.error("ffmpeg_failed", stderr=r.stderr[-4000:])
        raise RuntimeError(f"FFmpeg falló: {r.stderr[-500:]!s}")
