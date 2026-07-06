"""Конвертация legacy .doc → .docx для локального ingest."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def _find_soffice() -> str | None:
    found = shutil.which("soffice") or shutil.which("soffice.exe")
    if found:
        return found
    for candidate in (
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "/usr/bin/soffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ):
        if Path(candidate).is_file():
            return candidate
    return None


def convert_doc_to_docx_bytes(raw_bytes: bytes, *, source_name: str = "document.doc") -> bytes | None:
    """
    LibreOffice headless: .doc → .docx.
    Возвращает bytes docx или None если конвертер недоступен / ошибка.
    """
    soffice = _find_soffice()
    if not soffice:
        return None
    name = Path(source_name).name
    if not name.lower().endswith(".doc"):
        name = f"{Path(name).stem}.doc"
    with tempfile.TemporaryDirectory(prefix="tmki-doc-") as tmp:
        tmp_path = Path(tmp)
        doc_path = tmp_path / name
        doc_path.write_bytes(raw_bytes)
        try:
            proc = subprocess.run(
                [
                    soffice,
                    "--headless",
                    "--norestore",
                    "--convert-to",
                    "docx",
                    "--outdir",
                    str(tmp_path),
                    str(doc_path),
                ],
                capture_output=True,
                timeout=int(os.environ.get("TMKI_DOC_CONVERT_TIMEOUT", "120")),
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if proc.returncode != 0:
            return None
        out = tmp_path / f"{doc_path.stem}.docx"
        if not out.is_file():
            matches = list(tmp_path.glob("*.docx"))
            if not matches:
                return None
            out = matches[0]
        data = out.read_bytes()
        return data if data.startswith(b"PK\x03\x04") else None
