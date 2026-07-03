from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SttResult:
    text: str
    provider: str
    language: str | None = None
    speaker_employee_id: str | None = None
    raw_text: str | None = None


class SttProvider(Protocol):
    def transcribe(self, audio_path: str, *, employee_id_hint: str | None = None) -> SttResult: ...


class StubSttProvider:
    def transcribe(self, audio_path: str, *, employee_id_hint: str | None = None) -> SttResult:
        return SttResult(
            text="",
            provider="stub",
            language="ru",
            speaker_employee_id=employee_id_hint,
        )


class FasterWhisperSttProvider:
    """
    Локальный STT через faster-whisper (лучший офлайн-вариант для русского).

    pip install -e ".[stt]"  # faster-whisper
    Пресеты (WHISPER_PRESET):
      quality  — large-v3-turbo, beam 5, VAD (макс. точность RU)
      balanced — medium, beam 5 (по умолчанию, CPU-диктовка)
      fast     — medium, beam 1 (быстрее, чуть хуже на шуме)
    Переопределения: WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE,
      WHISPER_BEAM_SIZE, WHISPER_CPU_THREADS.
    """

    _model_cache: dict = {}

    def __init__(self, model_size: str | None = None, *, preset: str | None = None) -> None:
        from tmki_voice.whisper_presets import resolve_whisper_config

        cfg = resolve_whisper_config(preset=preset)
        if model_size:
            cfg["model"] = model_size
        self._cfg = cfg
        self._model_size = cfg["model"]
        self._device = cfg["device"]
        self._compute_type = cfg["compute_type"]
        self._cpu_threads = cfg.get("cpu_threads") or 0

    def _get_model(self):
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError('pip install -e ".[stt]" для TMKI_STT_PROVIDER=whisper') from exc

        key = (self._model_size, self._device, self._compute_type, self._cpu_threads)
        model = FasterWhisperSttProvider._model_cache.get(key)
        if model is None:
            kwargs: dict = {
                "device": self._device,
                "compute_type": self._compute_type,
            }
            if self._cpu_threads > 0:
                kwargs["cpu_threads"] = self._cpu_threads
            model = WhisperModel(self._model_size, **kwargs)
            FasterWhisperSttProvider._model_cache[key] = model
        return model

    def transcribe(self, audio_path: str, *, employee_id_hint: str | None = None) -> SttResult:
        model = self._get_model()
        cfg = self._cfg
        segments, info = model.transcribe(
            audio_path,
            language="ru",
            beam_size=int(cfg.get("beam_size", 5)),
            vad_filter=bool(cfg.get("vad_filter", True)),
            vad_parameters=dict(cfg.get("vad_parameters") or {}),
            condition_on_previous_text=bool(cfg.get("condition_on_previous_text", False)),
            initial_prompt=str(cfg.get("initial_prompt") or ""),
            no_speech_threshold=float(cfg.get("no_speech_threshold", 0.6)),
            compression_ratio_threshold=float(cfg.get("compression_ratio_threshold", 2.4)),
            log_prob_threshold=float(cfg.get("log_prob_threshold", -1.0)),
        )
        text = " ".join(s.text.strip() for s in segments).strip()
        from tmki_voice.stt_corrections import apply_stt_corrections

        raw_text = text
        text = apply_stt_corrections(text)
        preset = cfg.get("preset", "quality")
        provider = f"faster-whisper/{preset}"
        if text != raw_text:
            provider += "+fix"
        return SttResult(
            text=text,
            provider=provider,
            language=info.language,
            speaker_employee_id=employee_id_hint,
            raw_text=raw_text if text != raw_text else None,
        )


def preload_whisper_model(*, preset: str | None = None) -> str:
    """Загрузить модель в память (фоновый прогрев при старте демо)."""
    if os.environ.get("TMKI_STT_PROVIDER", "stub").lower() != "whisper":
        return "skipped"
    provider = FasterWhisperSttProvider(preset=preset)
    provider._get_model()
    return provider._cfg.get("preset", "fast")


def get_stt_provider() -> SttProvider:
    mode = os.environ.get("TMKI_STT_PROVIDER", "stub").lower()
    if mode == "whisper":
        return FasterWhisperSttProvider()
    return StubSttProvider()


def transcribe_audio(audio_path: str, *, employee_id_hint: str | None = None) -> SttResult:
    return get_stt_provider().transcribe(audio_path, employee_id_hint=employee_id_hint)
