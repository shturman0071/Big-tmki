"""Silero TTS v5 (русский): омографы, офлайн на CPU."""

from __future__ import annotations

import os
import tempfile
import wave
from pathlib import Path
from typing import Any

SILERO_SPEAKERS: list[dict[str, str]] = [
    {"id": "aidar", "label": "Айдар (муж.)"},
    {"id": "baya", "label": "Бая (жен.)"},
    {"id": "kseniya", "label": "Ксения (жен.)"},
    {"id": "xenia", "label": "Ксения 2 (жен.)"},
    {"id": "eugene", "label": "Евгений (муж.)"},
]

DEFAULT_SILERO_MODEL = "v5_3_ru"
DEFAULT_SILERO_VOICE = "kseniya"
DEFAULT_SILERO_SAMPLE_RATE = 24000
DEFAULT_MODEL_URL = "https://models.silero.ai/models/tts/ru/v5_3_ru.pt"

_MODEL_CACHE: dict[str, Any] = {}


def silero_model_path() -> Path:
    env = os.environ.get("SILERO_MODEL_PATH", "").strip()
    if env:
        return Path(env)
    custom = os.environ.get("SILERO_MODEL_DIR", "").strip()
    if custom:
        base = Path(custom)
    else:
        base = Path.home() / ".local" / "share" / "tmki-models" / "silero"
    return base / f"{os.environ.get('SILERO_MODEL_ID', DEFAULT_SILERO_MODEL)}.pt"


def list_silero_voices() -> list[dict[str, str]]:
    return list(SILERO_SPEAKERS)


def normalize_silero_voice(voice_id: str | None) -> str:
    if not voice_id:
        return os.environ.get("SILERO_VOICE", DEFAULT_SILERO_VOICE)
    key = voice_id.strip().lower()
    ids = {s["id"] for s in SILERO_SPEAKERS}
    return key if key in ids else os.environ.get("SILERO_VOICE", DEFAULT_SILERO_VOICE)


def _download_model_file(url: str, dest: Path) -> None:
    import ssl
    import urllib.request

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".pt.part")
    ctx = ssl.create_default_context()
    try:
        urllib.request.urlretrieve(url, tmp)  # noqa: S310
    except Exception:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(url, context=ctx) as resp:  # noqa: S310
            tmp.write_bytes(resp.read())
    tmp.replace(dest)


def ensure_silero_model() -> Path:
    path = silero_model_path()
    if path.is_file() and path.stat().st_size > 5_000_000:
        return path
    url = os.environ.get("SILERO_MODEL_URL", DEFAULT_MODEL_URL)
    _download_model_file(url, path)
    return path


def _load_model() -> Any:
    if "model" in _MODEL_CACHE:
        return _MODEL_CACHE["model"]

    from torch import package

    model_path = ensure_silero_model()
    imp = package.PackageImporter(str(model_path))
    model = imp.load_pickle("tts_models", "model")
    _MODEL_CACHE["model"] = model
    return model


def preload_silero_model() -> str:
    _load_model()
    return os.environ.get("SILERO_MODEL_ID", DEFAULT_SILERO_MODEL)


def _write_wav(path: Path, audio_tensor: Any, sample_rate: int) -> None:
    audio = audio_tensor.detach().cpu().numpy()
    if audio.ndim > 1:
        audio = audio.squeeze()
    pcm = (audio * 32767).clip(-32768, 32767).astype("int16")
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


class SileroTtsProvider:
    """Локальный neural TTS Silero v5 (CC BY-NC 4.0 — см. лицензию для prod)."""

    def __init__(
        self,
        *,
        voice_id: str | None = None,
        sample_rate: int | None = None,
    ) -> None:
        self._voice_id = normalize_silero_voice(voice_id)
        self._sample_rate = int(
            sample_rate or os.environ.get("SILERO_SAMPLE_RATE", str(DEFAULT_SILERO_SAMPLE_RATE))
        )

    def synthesize(self, text: str):
        from tmki_voice.tts import TtsResult

        model = _load_model()
        audio = model.apply_tts(
            text=text,
            speaker=self._voice_id,
            sample_rate=self._sample_rate,
        )
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            out_path = Path(tmp.name)
        _write_wav(out_path, audio, self._sample_rate)
        return TtsResult(
            text=text,
            audio_path=str(out_path),
            provider="silero",
            voice_id=self._voice_id,
            sample_rate_hz=self._sample_rate,
        )
