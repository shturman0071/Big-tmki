from __future__ import annotations

import json
import os
import webbrowser
import html as html_module
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Protocol


class DisplayTarget(str, Enum):
    COMPUTER = "computer"
    TABLET = "tablet"
    TV = "tv"
    BROWSER = "browser"


@dataclass(frozen=True)
class DisplayResult:
    target: str
    delivered: bool
    method: str
    detail: str | None = None


class DisplayProvider(Protocol):
    def show(self, content: dict[str, Any], *, target: DisplayTarget) -> DisplayResult: ...


class StubDisplayProvider:
    """Заглушка: пишет payload в artifacts/display/."""

    def __init__(self, out_dir: Path | None = None) -> None:
        self._out = out_dir or Path(__file__).resolve().parents[1] / "artifacts" / "display"

    def show(self, content: dict[str, Any], *, target: DisplayTarget) -> DisplayResult:
        self._out.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = self._out / f"{target.value}_{ts}.json"
        path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
        return DisplayResult(target=target.value, delivered=True, method="artifact_file", detail=str(path))


class BrowserDisplayProvider:
    """Открыть HTML-страницу с ответом в браузере (computer/tablet)."""

    def __init__(self, out_dir: Path | None = None) -> None:
        self._out = out_dir or Path(__file__).resolve().parents[1] / "artifacts" / "display"

    def show(self, content: dict[str, Any], *, target: DisplayTarget) -> DisplayResult:
        if target == DisplayTarget.TV:
            return HttpCastDisplayProvider(self._out).show(content, target=target)
        self._out.mkdir(parents=True, exist_ok=True)
        answer = content.get("answer", "")
        html = _answer_html(answer)
        path = self._out / "last_answer.html"
        path.write_text(html, encoding="utf-8")
        webbrowser.open(path.as_uri())
        return DisplayResult(target=target.value, delivered=True, method="browser", detail=str(path))


def _answer_html(answer: str) -> str:
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>TMKI</title>
<style>body{{font-family:sans-serif;margin:2rem;max-width:960px}}pre{{white-space:pre-wrap;font-size:22px;line-height:1.5}}</style></head>
<body><h1>TMKI Assistant</h1><pre>{html_module.escape(answer)}</pre></body></html>"""


class HttpCastDisplayProvider:
    """LAN HTTP cast для TV/планшета (браузер на устройстве открывает URL)."""

    def __init__(self, out_dir: Path | None = None) -> None:
        self._out = out_dir or Path(__file__).resolve().parents[1] / "artifacts" / "display"

    def show(self, content: dict[str, Any], *, target: DisplayTarget) -> DisplayResult:
        from tmki_voice.cast_server import publish_cast_html

        self._out.mkdir(parents=True, exist_ok=True)
        answer = content.get("answer", "")
        html = _answer_html(answer)
        (self._out / "tv_cast.html").write_text(html, encoding="utf-8")
        host = os.environ.get("TMKI_CAST_HOST", "0.0.0.0")
        port = int(os.environ.get("TMKI_CAST_PORT", "8766"))
        url = publish_cast_html(html, host=host, port=port)
        return DisplayResult(target=target.value, delivered=True, method="http_cast", detail=url)


def get_display_provider() -> DisplayProvider:
    mode = os.environ.get("TMKI_DISPLAY_PROVIDER", "stub").lower()
    if mode == "browser":
        return BrowserDisplayProvider()
    if mode == "http_cast":
        return HttpCastDisplayProvider()
    return StubDisplayProvider()


def cast_mvp_output(output: dict[str, Any], *, target: str = "computer") -> DisplayResult:
    try:
        tgt = DisplayTarget(target)
    except ValueError:
        tgt = DisplayTarget.COMPUTER
    return get_display_provider().show(output, target=tgt)
