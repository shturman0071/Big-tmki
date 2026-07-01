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
    Локальный STT через faster-whisper (опционально: pip install faster-whisper).
    """

    def __init__(self, model_size: str | None = None) -> None:
        self._model_size = model_size or os.environ.get("WHISPER_MODEL_SIZE", "small")

    def transcribe(self, audio_path: str, *, employee_id_hint: str | None = None) -> SttResult:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError("pip install faster-whisper для TMKI_STT_PROVIDER=whisper") from exc

        model = WhisperModel(self._model_size, device="cpu", compute_type="int8")
        segments, info = model.transcribe(audio_path, language="ru")
        text = " ".join(s.text.strip() for s in segments).strip()
        return SttResult(
            text=text,
            provider="faster-whisper",
            language=info.language,
            speaker_employee_id=employee_id_hint,
        )


def get_stt_provider() -> SttProvider:
    mode = os.environ.get("TMKI_STT_PROVIDER", "stub").lower()
    if mode == "whisper":
        return FasterWhisperSttProvider()
    return StubSttProvider()


def transcribe_audio(audio_path: str, *, employee_id_hint: str | None = None) -> SttResult:
    return get_stt_provider().transcribe(audio_path, employee_id_hint=employee_id_hint)
