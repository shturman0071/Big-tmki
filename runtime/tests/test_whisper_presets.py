"""Тесты пресетов faster-whisper."""

from __future__ import annotations

import os

from tmki_voice.whisper_presets import WHISPER_PRESETS, resolve_whisper_config


def test_whisper_presets_defined():
    assert set(WHISPER_PRESETS) >= {"quality", "balanced", "fast"}
    for name, cfg in WHISPER_PRESETS.items():
        assert cfg["model"]
        assert cfg["beam_size"] >= 1
        assert cfg["vad_filter"] is True
        assert cfg["condition_on_previous_text"] is False


def test_resolve_whisper_config_balanced_default(monkeypatch):
    monkeypatch.delenv("WHISPER_PRESET", raising=False)
    monkeypatch.delenv("WHISPER_MODEL_SIZE", raising=False)
    cfg = resolve_whisper_config()
    assert cfg["preset"] == "fast"
    assert cfg["model"] == "medium"
    assert cfg["beam_size"] == 1


def test_resolve_whisper_config_quality_preset(monkeypatch):
    monkeypatch.setenv("WHISPER_PRESET", "quality")
    cfg = resolve_whisper_config()
    assert cfg["preset"] == "quality"
    assert cfg["model"] == "large-v3-turbo"


def test_env_overrides_model(monkeypatch):
    monkeypatch.setenv("WHISPER_PRESET", "fast")
    monkeypatch.setenv("WHISPER_MODEL_SIZE", "small")
    cfg = resolve_whisper_config()
    assert cfg["model"] == "small"
    assert cfg["beam_size"] == 1
