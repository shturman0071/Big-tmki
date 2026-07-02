"""Каталог файлов архива: поиск по имени и сопоставление doc_id → путь."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tmki_ingest.dedup import compute_content_hash
from tmki_ingest.regulations import INGEST_EXTENSIONS

_TOKEN_RE = re.compile(r"[а-яёa-z0-9]{2,}", re.IGNORECASE)

DEFAULT_ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts" / "regulations-import"
DEFAULT_ARCHIVE = Path(r"D:\Курсор\СКРУ-2")


def doc_id_from_bytes(raw: bytes) -> str:
    content_hash = compute_content_hash(raw)
    return f"doc_{content_hash[7:19]}"


def doc_id_from_path(path: Path) -> str:
    return doc_id_from_bytes(path.read_bytes())


@dataclass
class DocCatalog:
    archive_root: Path
    cache_path: Path
    by_doc_id: dict[str, str] = field(default_factory=dict)
    paths: list[str] = field(default_factory=list)

    @classmethod
    def load(
        cls,
        *,
        archive_root: Path | None = None,
        cache_path: Path | None = None,
        artifacts_dir: Path | None = None,
        index_paths: bool = True,
    ) -> "DocCatalog":
        artifacts = artifacts_dir or DEFAULT_ARTIFACTS
        root = archive_root or resolve_archive_root(artifacts) or DEFAULT_ARCHIVE
        cache = cache_path or (artifacts / "doc-catalog.json")
        catalog = cls(archive_root=root, cache_path=cache)
        catalog._load_cache()
        if index_paths:
            catalog._ensure_path_index()
        return catalog

    def _load_cache(self) -> None:
        if not self.cache_path.is_file():
            return
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if data.get("archive_root") != str(self.archive_root):
            return
        entries = data.get("entries") or {}
        if isinstance(entries, dict):
            self.by_doc_id = {str(k): str(v) for k, v in entries.items()}

    def _save_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "0.1",
            "archive_root": str(self.archive_root),
            "entries": self.by_doc_id,
            "path_count": len(self.paths),
        }
        self.cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _ensure_path_index(self) -> None:
        if self.paths:
            return
        priority = _priority_paths(self.cache_path.parent)
        if priority:
            allowed = {ext.lower() for ext in INGEST_EXTENSIONS}
            self.paths = [
                rel
                for rel in priority
                if Path(rel).suffix.lower() in allowed
                and (self.archive_root / rel).is_file()
            ]
            if self.paths:
                return
        if not self.archive_root.is_dir():
            return
        self.paths = [
            str(p.relative_to(self.archive_root)).replace("\\", "/")
            for p in sorted(self.archive_root.rglob("*"))
            if p.is_file() and p.suffix.lower() in INGEST_EXTENSIONS
        ]

    def register_mapping(self, doc_id: str, relative_path: str) -> None:
        if doc_id and relative_path:
            self.by_doc_id[doc_id] = relative_path.replace("\\", "/")

    def warm_from_processed(self, *, limit: int = 0, save_every: int = 200) -> int:
        """Заполнить cache doc_id→path по списку processed из reindex-state (без rglob архива)."""
        priority = _priority_paths(self.cache_path.parent)
        if not priority or not self.archive_root.is_dir():
            return 0
        known_rels = set(self.by_doc_id.values())
        added = 0
        for rel_path in priority:
            if rel_path in known_rels:
                continue
            full = self.archive_root / rel_path
            if not full.is_file():
                continue
            try:
                did = doc_id_from_path(full)
            except OSError:
                continue
            self.by_doc_id[did] = rel_path
            known_rels.add(rel_path)
            added += 1
            if save_every and added % save_every == 0:
                self._save_cache()
            if limit and added >= limit:
                break
        if added:
            self._save_cache()
        return added

    def search_paths(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        """Поиск файлов по токенам в имени/пути (как в проводнике)."""
        self._ensure_path_index()
        tokens = [t for t in _TOKEN_RE.findall(query.lower()) if len(t) >= 2]
        if not tokens:
            return []
        scored: list[tuple[float, str]] = []
        for rel in self.paths:
            target = rel.lower()
            name = Path(rel).name.lower()
            hits = sum(1 for tok in tokens if tok in target)
            if hits == 0:
                continue
            name_hits = sum(1 for tok in tokens if tok in name)
            score = hits + 0.5 * name_hits + (0.25 if all(tok in target for tok in tokens[:2]) else 0.0)
            scored.append((score, rel))
        scored.sort(key=lambda x: x[0], reverse=True)
        out: list[dict[str, Any]] = []
        for score, rel in scored[:limit]:
            full = self.archive_root / rel
            out.append(
                {
                    "relative_path": rel,
                    "file_name": full.name,
                    "absolute_path": str(full),
                    "score": round(score, 3),
                }
            )
        return out

    def resolve_doc_id(self, doc_id: str, *, max_new_hashes: int = 80) -> dict[str, Any] | None:
        """Сопоставить doc_id с файлом; при необходимости догружает cache по хешу."""
        if not doc_id:
            return None
        rel = self.by_doc_id.get(doc_id)
        if rel:
            full = self.archive_root / rel
            return _entry_from_path(full, rel, doc_id=doc_id)
        if not self.archive_root.is_dir():
            return None

        priority = _priority_paths(self.cache_path.parent)
        scanned = 0
        for rel_path in priority:
            if doc_id in self.by_doc_id:
                break
            full = self.archive_root / rel_path
            if not full.is_file():
                continue
            try:
                did = doc_id_from_path(full)
            except OSError:
                continue
            self.by_doc_id[did] = rel_path
            scanned += 1
            if did == doc_id:
                self._save_cache()
                return _entry_from_path(full, rel_path, doc_id=doc_id)
            if scanned >= max_new_hashes:
                break

        if doc_id not in self.by_doc_id:
            for rel_path in priority:
                if doc_id in self.by_doc_id:
                    break
                if rel_path in self.by_doc_id.values():
                    continue
                full = self.archive_root / rel_path
                if not full.is_file():
                    continue
                try:
                    did = doc_id_from_path(full)
                except OSError:
                    continue
                self.by_doc_id[did] = rel_path
                scanned += 1
                if did == doc_id:
                    self._save_cache()
                    return _entry_from_path(full, rel_path, doc_id=doc_id)
                if scanned >= max_new_hashes:
                    break

        if scanned:
            self._save_cache()
        rel = self.by_doc_id.get(doc_id)
        if not rel:
            return None
        full = self.archive_root / rel
        return _entry_from_path(full, rel, doc_id=doc_id)

    def enrich_citations(self, citations: list[dict[str, Any]], *, resolve_missing: bool = False) -> list[dict[str, Any]]:
        enriched: list[dict[str, Any]] = []
        for citation in citations:
            item = dict(citation)
            if item.get("relative_path") and item.get("file_name"):
                rel = str(item["relative_path"])
                full = self.archive_root / rel
                item["absolute_path"] = str(full)
                enriched.append(item)
                continue
            doc_id = item.get("doc_id") or ""
            rel = self.by_doc_id.get(doc_id) if doc_id else None
            if rel:
                full = self.archive_root / rel
                item["file_name"] = full.name
                item["relative_path"] = rel
                item["absolute_path"] = str(full)
                enriched.append(item)
                continue
            if resolve_missing and doc_id:
                resolved = self.resolve_doc_id(doc_id, max_new_hashes=8)
                if resolved:
                    item["file_name"] = resolved["file_name"]
                    item["relative_path"] = resolved["relative_path"]
                    item["absolute_path"] = resolved["absolute_path"]
            enriched.append(item)
        return enriched


def resolve_archive_root(artifacts_dir: Path | None = None) -> Path | None:
    artifacts = artifacts_dir or DEFAULT_ARTIFACTS
    state = artifacts / "reindex-state.json"
    if state.is_file():
        try:
            data = json.loads(state.read_text(encoding="utf-8"))
            root = data.get("archive_root")
            if root:
                return Path(str(root))
        except (OSError, json.JSONDecodeError):
            pass
    env = os.environ.get("TMKI_REGULATIONS_ARCHIVE")
    if env:
        return Path(env)
    if DEFAULT_ARCHIVE.is_dir():
        return DEFAULT_ARCHIVE
    return None


def _priority_paths(artifacts_dir: Path) -> list[str]:
    state = artifacts_dir / "reindex-state.json"
    if not state.is_file():
        return []
    try:
        data = json.loads(state.read_text(encoding="utf-8"))
        processed = data.get("processed") or []
        if isinstance(processed, list):
            return [str(p) for p in processed]
    except (OSError, json.JSONDecodeError):
        pass
    return []


def _entry_from_path(full: Path, rel: str, *, doc_id: str) -> dict[str, Any]:
    return {
        "doc_id": doc_id,
        "relative_path": rel,
        "file_name": full.name,
        "absolute_path": str(full),
    }
