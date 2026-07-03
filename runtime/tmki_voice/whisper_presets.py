"""Проверенные пресеты faster-whisper для русского (офлайн STT)."""

from __future__ import annotations

import os
from typing import Any

from tmki_voice.stt_corrections import DOMAIN_INITIAL_PROMPT
WHISPER_PRESETS: dict[str, dict[str, Any]] = {
  # large-v3-turbo: лучший баланс точности/скорости для RU (рекомендация 2024–2025)
    "quality": {
        "model": "large-v3-turbo",
        "beam_size": 5,
        "vad_filter": True,
        "vad_parameters": {
            "min_silence_duration_ms": 500,
            "speech_pad_ms": 100,
            "threshold": 0.5,
        },
        "condition_on_previous_text": False,
        "no_speech_threshold": 0.6,
        "compression_ratio_threshold": 2.4,
        "log_prob_threshold": -1.0,
        "initial_prompt": DOMAIN_INITIAL_PROMPT,
    },
    # medium + beam 5 — компромисс на CPU
    "balanced": {
        "model": "medium",
        "beam_size": 5,
        "vad_filter": True,
        "vad_parameters": {
            "min_silence_duration_ms": 500,
            "speech_pad_ms": 100,
            "threshold": 0.5,
        },
        "condition_on_previous_text": False,
        "no_speech_threshold": 0.6,
        "compression_ratio_threshold": 2.4,
        "log_prob_threshold": -1.0,
        "initial_prompt": DOMAIN_INITIAL_PROMPT,
    },
    # medium + beam 1 — основной для голосового ввода в демо (быстро + автофиксы)
    "fast": {
        "model": "medium",
        "beam_size": 1,
        "vad_filter": True,
        "vad_parameters": {
            "min_silence_duration_ms": 400,
            "speech_pad_ms": 80,
            "threshold": 0.45,
        },
        "condition_on_previous_text": False,
        "no_speech_threshold": 0.6,
        "compression_ratio_threshold": 2.4,
        "log_prob_threshold": -1.0,
        "initial_prompt": DOMAIN_INITIAL_PROMPT,
    },
    # small + beam 1 — максимальная скорость на CPU (короткие фразы)
    "voice": {
        "model": "small",
        "beam_size": 1,
        "vad_filter": True,
        "vad_parameters": {
            "min_silence_duration_ms": 350,
            "speech_pad_ms": 60,
            "threshold": 0.45,
        },
        "condition_on_previous_text": False,
        "no_speech_threshold": 0.6,
        "compression_ratio_threshold": 2.4,
        "log_prob_threshold": -1.0,
        "initial_prompt": DOMAIN_INITIAL_PROMPT,
    },
}


def resolve_whisper_config(preset: str | None = None) -> dict[str, Any]:
    """Пресет + переопределения из окружения (WHISPER_MODEL_SIZE, WHISPER_BEAM_SIZE, …).

    Явный ``preset`` (напр. из запроса UI) имеет приоритет над WHISPER_PRESET.
    """
    explicit = bool(preset)
    preset_name = (preset or os.environ.get("WHISPER_PRESET", "fast")).strip().lower()
    base = dict(WHISPER_PRESETS.get(preset_name, WHISPER_PRESETS["fast"]))
    base["preset"] = preset_name if preset_name in WHISPER_PRESETS else "fast"

    # Явный пресет (из UI) не перекрываем env — иначе тест пресетов бессмыслен.
    if not explicit:
        if os.environ.get("WHISPER_MODEL_SIZE"):
            base["model"] = os.environ["WHISPER_MODEL_SIZE"]
        if os.environ.get("WHISPER_BEAM_SIZE"):
            try:
                base["beam_size"] = int(os.environ["WHISPER_BEAM_SIZE"])
            except ValueError:
                pass

    base["device"] = os.environ.get("WHISPER_DEVICE", "cpu")
    base["compute_type"] = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")
    try:
        base["cpu_threads"] = int(os.environ.get("WHISPER_CPU_THREADS", "0"))
    except ValueError:
        base["cpu_threads"] = 0
    if base["cpu_threads"] <= 0 and base["device"] == "cpu":
        cores = os.cpu_count() or 4
        base["cpu_threads"] = min(8, cores)

    return base
