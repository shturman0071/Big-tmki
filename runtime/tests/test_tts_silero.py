import os

from tmki_voice import get_tts_provider, tts_voice_catalog
from tmki_voice.silero_tts import list_silero_voices, normalize_silero_voice


def test_get_tts_provider_silero_mode():
    os.environ["TMKI_TTS_PROVIDER"] = "silero"
    provider = get_tts_provider()
    assert provider.__class__.__name__ == "SileroTtsProvider"
    os.environ.pop("TMKI_TTS_PROVIDER", None)


def test_silero_voice_catalog():
    os.environ["TMKI_TTS_PROVIDER"] = "silero"
    catalog = tts_voice_catalog()
    assert catalog["provider"] == "silero"
    assert len(catalog["voices"]) == 5
    ids = {v["id"] for v in catalog["voices"]}
    assert ids == {"aidar", "baya", "kseniya", "xenia", "eugene"}
    os.environ.pop("TMKI_TTS_PROVIDER", None)


def test_normalize_silero_voice():
    assert normalize_silero_voice("aidar") == "aidar"
    assert normalize_silero_voice("unknown") in {v["id"] for v in list_silero_voices()}
