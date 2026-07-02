from unittest.mock import patch

from scripts.check_ollama import probe_ollama, resolve_demo_llm


def test_probe_ollama_unreachable():
    with patch("scripts.check_ollama.urllib.request.urlopen", side_effect=OSError("down")):
        status = probe_ollama()
    assert status["ready"] is False


def test_resolve_demo_llm_stub_when_down():
    with patch("scripts.check_ollama.probe_ollama", return_value={"ready": False}):
        assert resolve_demo_llm(prefer="auto") == "stub"


def test_resolve_demo_llm_ollama_when_ready():
    with patch("scripts.check_ollama.probe_ollama", return_value={"ready": True}):
        assert resolve_demo_llm(prefer="auto") == "ollama"
