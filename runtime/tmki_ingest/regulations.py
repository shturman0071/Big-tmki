from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal
from uuid import uuid4

from tmki_ingest.dedup import DedupStore
from tmki_ingest.pipeline import ingest_and_index
from tmki_rag.folders import FolderAclContext
from tmki_rag.index import ChunkIndex

ImportAction = Literal["ingest_candidate", "catalog_only", "skip"]

INGEST_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf"}
DEFAULT_MAX_FILE_BYTES = 100 * 1024 * 1024
CATALOG_ONLY_EXTENSIONS = {
    ".vsdx",
    ".vsd",
    ".xlsx",
    ".xls",
    ".dwg",
    ".dxf",
    ".zip",
    ".rar",
    ".7z",
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
}
SKIP_EXTENSIONS = {".tmp", ".bak", ".ds_store"}


@dataclass(frozen=True)
class RegulationFileEntry:
    relative_path: str
    file_name: str
    extension: str
    size_bytes: int
    import_action: ImportAction
    content_hash: str | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _update_doc_catalog_mapping(artifacts_dir: Path, doc_id: str, relative_path: str) -> None:
    from tmki_rag.doc_catalog import DocCatalog

    catalog = DocCatalog.load(artifacts_dir=artifacts_dir)
    catalog.register_mapping(doc_id, relative_path)
    catalog._save_cache()


def _classify_extension(ext: str) -> ImportAction:
    lowered = ext.lower()
    if lowered in SKIP_EXTENSIONS:
        return "skip"
    if lowered in INGEST_EXTENSIONS:
        return "ingest_candidate"
    if lowered in CATALOG_ONLY_EXTENSIONS:
        return "catalog_only"
    return "catalog_only"


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return f"sha256:{digest.hexdigest()}"


def scan_regulations_archive(
    root: Path,
    *,
    compute_hash: bool = False,
    max_entries: int | None = None,
) -> dict[str, Any]:
    """
    Сканирование локального архива регламентов (#6 MVP).
    Не импортирует содержимое — строит manifest для планирования ingest.
    """
    root = root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Архив не найден: {root}")

    entries: list[RegulationFileEntry] = []
    stats = {"ingest_candidate": 0, "catalog_only": 0, "skip": 0}

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        action = _classify_extension(ext)
        stats[action] += 1
        content_hash = _file_hash(path) if compute_hash and action == "ingest_candidate" else None
        entries.append(
            RegulationFileEntry(
                relative_path=str(path.relative_to(root)).replace("\\", "/"),
                file_name=path.name,
                extension=ext or "(none)",
                size_bytes=path.stat().st_size,
                import_action=action,
                content_hash=content_hash,
            )
        )
        if max_entries is not None and len(entries) >= max_entries:
            break

    return {
        "schema_version": "0.1",
        "archive_root": str(root),
        "scanned_at": _now_iso(),
        "total_files": len(entries),
        "stats": stats,
        "entries": [
            {
                "relative_path": e.relative_path,
                "file_name": e.file_name,
                "extension": e.extension,
                "size_bytes": e.size_bytes,
                "import_action": e.import_action,
                **({"content_hash": e.content_hash} if e.content_hash else {}),
            }
            for e in entries
        ],
    }


def build_ingest_request(
    file_path: Path,
    *,
    policy_context: dict[str, Any],
    classification: str,
    folder_id: str,
    trace_id: str | None = None,
) -> dict[str, Any]:
    raw = file_path.read_bytes()
    return {
        "schema_version": "0.1",
        "trace_id": trace_id or str(uuid4()),
        "policy_context": policy_context,
        "classification": classification,
        "folder_id": folder_id,
        "provenance": {"source_path": str(file_path)},
        "file": {"content_base64": base64.b64encode(raw).decode("ascii")},
    }


def _iter_ingest_candidates(root: Path, extensions: set[str]) -> list[Path]:
    return [
        p
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.suffix.lower() in extensions
    ]


def _load_import_state(state_path: Path) -> dict[str, Any]:
    if not state_path.is_file():
        return {
            "schema_version": "0.1",
            "processed": [],
            "stats": _empty_import_stats(),
        }
    data = json.loads(state_path.read_text(encoding="utf-8"))
    data.setdefault("processed", [])
    defaults = _empty_import_stats()
    saved = data.get("stats") or {}
    data["stats"] = {**defaults, **saved}
    return data


def _empty_import_stats() -> dict[str, int]:
    return {
        "imported": 0,
        "duplicate": 0,
        "rejected": 0,
        "ocr_failed": 0,
        "too_large": 0,
        "skip_temp": 0,
        "errors": 0,
    }


def _is_temp_office_file(path: Path) -> bool:
    return path.name.startswith("~$")


def _save_import_state(state_path: Path, state: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _save_chunks_snapshot(chunks_path: Path, index: ChunkIndex) -> None:
    chunks_path.parent.mkdir(parents=True, exist_ok=True)
    chunks_path.write_text(
        json.dumps({"schema_version": "0.1", "chunks": index.list()}, ensure_ascii=False),
        encoding="utf-8",
    )


def _write_reindex_heartbeat(
    heartbeat_path: Path,
    *,
    relative_path: str,
    file_index: int,
    total_candidates: int,
    stats: dict[str, int],
) -> None:
    heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
    heartbeat_path.write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "current_file": relative_path,
                "file_index": file_index,
                "total_candidates": total_candidates,
                "stats": stats,
                "updated_at": _now_iso(),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _load_chunks_into_index(chunks_path: Path, index: ChunkIndex) -> int:
    if not chunks_path.is_file():
        return 0
    data = json.loads(chunks_path.read_text(encoding="utf-8"))
    chunks = data.get("chunks", [])
    if chunks:
        index.add(chunks)
    return len(chunks)


def import_regulations_batch(
    root: Path,
    *,
    policy_context: dict[str, Any],
    classification: str,
    folder_id: str,
    folder_acl: FolderAclContext,
    dedup_store: DedupStore,
    index: ChunkIndex,
    limit: int = 5,
    extensions: set[str] | None = None,
    **import_kwargs: Any,
) -> dict[str, Any]:
    """Импорт первых N ingest_candidate файлов из архива (OCR stub → index)."""
    return import_regulations_full(
        root,
        policy_context=policy_context,
        classification=classification,
        folder_id=folder_id,
        folder_acl=folder_acl,
        dedup_store=dedup_store,
        index=index,
        limit=limit,
        extensions=extensions,
        **import_kwargs,
    )


def import_regulations_full(
    root: Path,
    *,
    policy_context: dict[str, Any],
    classification: str,
    folder_id: str,
    folder_acl: FolderAclContext,
    dedup_store: DedupStore,
    index: ChunkIndex,
    limit: int | None = None,
    extensions: set[str] | None = None,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    state_path: Path | None = None,
    chunks_path: Path | None = None,
    checkpoint_every: int = 100,
    on_progress: Callable[[dict[str, Any]], None] | None = None,
    resume: bool = True,
    force_reprocess: bool = False,
) -> dict[str, Any]:
    """
    Полный импорт архива регламентов (stub OCR → ChunkIndex).
    limit=None — все ingest_candidate; resume + checkpoint для длинных прогонов.
    """
    root = root.resolve()
    allowed = extensions or INGEST_EXTENSIONS
    state_file = state_path or (root / ".tmki-import-state.json")
    chunks_file = chunks_path or (root / ".tmki-import-chunks.json")
    heartbeat_file = state_file.parent / "reindex-heartbeat.json"

    state = _load_import_state(state_file) if resume else {
        "schema_version": "0.1",
        "processed": [],
        "stats": _empty_import_stats(),
    }
    processed: set[str] = set(state.get("processed", []))
    stats = state.get("stats", _empty_import_stats())

    if resume and not index.list():
        _load_chunks_into_index(chunks_file, index)

    imported: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = list(state.get("recent_errors") or [])
    candidates = _iter_ingest_candidates(root, allowed)
    started = _now_iso()
    if not state.get("started_at"):
        state["started_at"] = started

    if on_progress:
        on_progress({"phase": "scan_done", "total_candidates": len(candidates), "stats": dict(stats)})

    for i, path in enumerate(candidates, start=1):
        if limit is not None and stats["imported"] >= limit:
            break

        rel = str(path.relative_to(root)).replace("\\", "/")
        if rel in processed:
            continue

        if _is_temp_office_file(path):
            stats["skip_temp"] += 1
            processed.add(rel)
            continue

        size = path.stat().st_size
        if size > max_file_bytes:
            stats["too_large"] += 1
            processed.add(rel)
            continue

        _write_reindex_heartbeat(
            heartbeat_file,
            relative_path=rel,
            file_index=i,
            total_candidates=len(candidates),
            stats=dict(stats),
        )

        try:
            raw = path.read_bytes()
            request = build_ingest_request(
                path,
                policy_context=policy_context,
                classification=classification,
                folder_id=folder_id,
            )
            if force_reprocess:
                request["force_reprocess"] = True
            result = ingest_and_index(
                request,
                index,
                folder_acl=folder_acl,
                dedup_store=dedup_store,
                raw_bytes=raw,
            )
            status = result.ingest_response.get("ingest_status")
            if result.chunks:
                stats["imported"] += 1
                doc_id = result.ingest_response.get("doc_id")
                if doc_id:
                    _update_doc_catalog_mapping(state_file.parent, doc_id, rel)
                for chunk in result.chunks:
                    chunk["source_relative_path"] = rel
                    chunk["source_file_name"] = path.name
                imported.append(
                    {
                        "relative_path": rel,
                        "doc_id": result.ingest_response.get("doc_id"),
                        "chunks": len(result.chunks),
                        "ingest_status": status,
                    }
                )
            elif status == "duplicate":
                stats["duplicate"] += 1
            elif status == "rejected":
                stats["rejected"] += 1
            else:
                stats["ocr_failed"] += 1
        except Exception as exc:  # noqa: BLE001 — batch report
            stats["errors"] += 1
            errors.append({"path": rel, "error": str(exc)})

        processed.add(rel)

        if on_progress and (i % 25 == 0 or checkpoint_every > 0 and i % checkpoint_every == 0):
            on_progress(
                {
                    "file_index": i,
                    "total_candidates": len(candidates),
                    "stats": dict(stats),
                    "current_file": rel,
                }
            )

        if checkpoint_every > 0 and i % checkpoint_every == 0:
            state["processed"] = sorted(processed)
            state["stats"] = stats
            state["total_candidates"] = len(candidates)
            state["recent_errors"] = errors[-50:]
            state["updated_at"] = _now_iso()
            state["archive_root"] = str(root)
            _save_import_state(state_file, state)
            _save_chunks_snapshot(chunks_file, index)

    state["processed"] = sorted(processed)
    state["stats"] = stats
    state["total_candidates"] = len(candidates)
    state["recent_errors"] = errors[-50:]
    state["updated_at"] = _now_iso()
    state["archive_root"] = str(root)
    state["started_at"] = state.get("started_at") or started
    _save_import_state(state_file, state)
    _save_chunks_snapshot(chunks_file, index)
    if heartbeat_file.is_file():
        heartbeat_file.unlink()

    return {
        "schema_version": "0.1",
        "archive_root": str(root),
        "limit": limit,
        "total_candidates": len(candidates),
        "imported_count": stats["imported"],
        "duplicate_count": stats["duplicate"],
        "rejected_count": stats["rejected"],
        "ocr_failed_count": stats["ocr_failed"],
        "too_large_count": stats["too_large"],
        "skip_temp_count": stats["skip_temp"],
        "error_count": stats["errors"],
        "chunks_in_index": len(index.list()),
        "state_path": str(state_file),
        "chunks_path": str(chunks_file),
        "imported": imported[-20:],
        "errors": errors[-20:],
        "occurred_at": _now_iso(),
    }


def reindex_regulations_full(
    root: Path,
    *,
    policy_context: dict[str, Any],
    classification: str,
    folder_id: str,
    folder_acl: FolderAclContext,
    output_dir: Path,
    limit: int | None = None,
    resume: bool = True,
    checkpoint_every: int = 100,
    on_progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """
    Re-index архива с TMKI_OCR_MODE=local (реальный текст txt/docx/pdf).
    Пишет chunks-v2.json и reindex-state.json в output_dir.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    index = ChunkIndex()
    return import_regulations_full(
        root,
        policy_context=policy_context,
        classification=classification,
        folder_id=folder_id,
        folder_acl=folder_acl,
        dedup_store=DedupStore(),
        index=index,
        limit=limit,
        state_path=output_dir / "reindex-state.json",
        chunks_path=output_dir / "chunks-v2.json",
        checkpoint_every=checkpoint_every,
        on_progress=on_progress,
        resume=resume,
        force_reprocess=True,
    )
