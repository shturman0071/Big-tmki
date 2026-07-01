from __future__ import annotations

import json
import os
import webbrowser
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
            return DisplayResult(
                target=target.value,
                delivered=False,
                method="browser",
                detail="TV cast — backlog (Chromecast/Miracast)",
            )
        self._out.mkdir(parents=True, exist_ok=True)
        answer = content.get("answer", "")
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>TMKI</title></head>
<body><h1>TMKI Assistant</h1><pre style="white-space:pre-wrap;font-size:18px">{answer}</pre></body></html>"""
        path = self._out / "last_answer.html"
        path.write_text(html, encoding="utf-8")
        webbrowser.open(path.as_uri())
        return DisplayResult(target=target.value, delivered=True, method="browser", detail=str(path))


def get_display_provider() -> DisplayProvider:
    mode = os.environ.get("TMKI_DISPLAY_PROVIDER", "stub").lower()
    if mode == "browser":
        return BrowserDisplayProvider()
    return StubDisplayProvider()


def cast_mvp_output(output: dict[str, Any], *, target: str = "computer") -> DisplayResult:
    try:
        tgt = DisplayTarget(target)
    except ValueError:
        tgt = DisplayTarget.COMPUTER
    return get_display_provider().show(output, target=tgt)
