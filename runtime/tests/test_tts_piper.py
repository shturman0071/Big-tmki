import os

from tmki_voice import StubTtsProvider, get_tts_provider, synthesize_speech


def test_stub_tts_default():
    os.environ.pop("TMKI_TTS_PROVIDER", None)
    result = synthesize_speech("Тест озвучки")
    assert result.provider == "stub"
    assert result.audio_path is None
    assert "Тест" in result.text


def test_get_tts_provider_piper_mode():
    os.environ["TMKI_TTS_PROVIDER"] = "piper"
    provider = get_tts_provider()
    assert provider.__class__.__name__ == "PiperTtsProvider"
    os.environ.pop("TMKI_TTS_PROVIDER", None)


def test_stub_tts_explicit():
    result = StubTtsProvider(voice_id="generated_default").synthesize("Привет")
    assert result.voice_id == "generated_default"
