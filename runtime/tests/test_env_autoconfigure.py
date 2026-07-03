from tmki_runtime.env_autoconfigure import _is_auto, autoconfigure, detect_ingest_parser


def test_is_auto_sentinel():
    assert _is_auto("auto")
    assert _is_auto("")
    assert _is_auto(None)
    assert not _is_auto("docling")


def test_autoconfigure_respects_locked_keys():
    current = {"TMKI_INGEST_PARSER": "auto", "TMKI_INDEX_BACKEND": "auto"}
    updates, _log = autoconfigure(current, locked_keys={"TMKI_INGEST_PARSER"})
    assert "TMKI_INGEST_PARSER" not in updates
    assert "TMKI_INDEX_BACKEND" in updates


def test_detect_ingest_parser_default_without_deps(monkeypatch):
    monkeypatch.setattr(
        "tmki_runtime.env_autoconfigure._module_available",
        lambda name: False,
    )
    assert detect_ingest_parser() == "default"
