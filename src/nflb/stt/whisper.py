"""Transcripción local de notas de voz con faster-whisper (el audio no sale del equipo).

Telegram envía OGG/Opus; faster-whisper lo decodifica con PyAV (incluye ffmpeg).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from nflb.config import get_settings


@lru_cache
def _model():
    from faster_whisper import WhisperModel

    return WhisperModel(get_settings().whisper_model, device="cpu", compute_type="int8")


def transcribe(path: Path) -> str:
    segments, _info = _model().transcribe(str(path), language="es", vad_filter=True,
                                          beam_size=5)  # fmt: skip
    return " ".join(s.text.strip() for s in segments).strip()
