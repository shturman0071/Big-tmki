from tmki_runtime.cli_encoding import fix_windows_cli_text, resolve_cli_message


def test_fix_mojibake_utf8_from_powershell():
    good = "промбезопасность кран"
    broken = good.encode("utf-8").decode("latin-1")
    assert fix_windows_cli_text(broken) == good


def test_fix_leaves_valid_cyrillic():
    good = "промбезопасность кран"
    assert fix_windows_cli_text(good) == good


def test_fix_leaves_ascii():
    assert fix_windows_cli_text("safety crane") == "safety crane"


def test_safe_console_text_replaces_unencodable():
    from tmki_runtime.cli_encoding import safe_console_text

    text = "prefix ü suffix"
    safe = safe_console_text(text)
    encoding = __import__("sys").stdout.encoding or "utf-8"
    safe.encode(encoding)  # must not raise


def test_resolve_cli_message_prefers_positional(monkeypatch):
    monkeypatch.setenv("TMKI_MVP_MESSAGE", "из env")
    assert resolve_cli_message(positional="из argv", default="default") == "из argv"
