from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

# Рекомендуемый бесплатный TTS: Piper (OHF-Voice/piper1-gpl)
# pip install piper-tts
# Голоса: https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md
DEFAULT_PIPER_VOICE = "ru_RU-denis-medium"
DEFAULT_PIPER_VOICE_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/denis/medium"
)


@dataclass(frozen=True)
class TtsResult:
    text: str
    audio_path: str | None
    provider: str
    voice_id: str
    sample_rate_hz: int | None = None


class TtsProvider(Protocol):
    def synthesize(self, text: str) -> TtsResult: ...


class StubTtsProvider:
    """Заглушка без аудио (тесты, CI)."""

    def __init__(self, voice_id: str = "stub") -> None:
        self._voice_id = voice_id

    def synthesize(self, text: str) -> TtsResult:
        return TtsResult(
            text=text,
            audio_path=None,
            provider="stub",
            voice_id=self._voice_id,
        )


class PiperTtsProvider:
    """
    Локальный neural TTS через Piper CLI (бесплатно, офлайн).
    Голоса скачиваются с HuggingFace (rhasspy/piper-voices).
    """

    def __init__(
        self,
        *,
        voice_id: str | None = None,
        voice_dir: Path | None = None,
        piper_bin: str | None = None,
    ) -> None:
        self._voice_id = voice_id or os.environ.get("PIPER_VOICE", DEFAULT_PIPER_VOICE)
        self._voice_dir = voice_dir or Path(
            os.environ.get("PIPER_VOICE_DIR", Path.home() / ".local" / "share" / "piper-voices")
        )
        self._piper_bin = piper_bin or os.environ.get("PIPER_BIN", "piper")

    def _model_paths(self) -> tuple[Path, Path]:
        onnx = self._voice_dir / f"{self._voice_id}.onnx"
        json_path = self._voice_dir / f"{self._voice_id}.onnx.json"
        return onnx, json_path

    def synthesize(self, text: str) -> TtsResult:
        onnx, cfg = self._model_paths()
        if not onnx.is_file() or not cfg.is_file():
            raise FileNotFoundError(
                f"Piper voice не найден: {onnx}. "
                f"Скачайте {self._voice_id} с HuggingFace (rhasspy/piper-voices) "
                f"или задайте PIPER_VOICE_DIR."
            )
        if not shutil.which(self._piper_bin):
            raise RuntimeError(
                "piper CLI не найден. Установите: pip install piper-tts"
            )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            out_path = Path(tmp.name)

        cmd = [
            self._piper_bin,
            "--model",
            str(onnx),
            "--config",
            str(cfg),
            "--output_file",
            str(out_path),
        ]
        proc = subprocess.run(
            cmd,
            input=text.encode("utf-8"),
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            err = proc.stderr.decode("utf-8", errors="replace")
            raise RuntimeError(f"piper failed: {err}")

        return TtsResult(
            text=text,
            audio_path=str(out_path),
            provider="piper",
            voice_id=self._voice_id,
            sample_rate_hz=22050,
        )


def get_tts_provider() -> TtsProvider:
    mode = os.environ.get("TMKI_TTS_PROVIDER", "stub").lower()
    if mode == "piper":
        return PiperTtsProvider()
    return StubTtsProvider(voice_id="generated_default")


def synthesize_speech(text: str) -> TtsResult:
    return get_tts_provider().synthesize(text)
