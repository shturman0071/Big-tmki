import textwrap
from datetime import date
from pathlib import Path

import pytest

from tmki_ingest import DedupStore, import_regulations_batch, scan_regulations_archive
from tmki_policy import build_policy_context, load_org_snapshot
from tmki_rag import ChunkIndex, FolderAclContext, load_folder_catalog, load_folder_grants

ROOT = Path(__file__).resolve().parents[2]


def _folder_acl():
    return FolderAclContext.from_catalog(
        load_folder_catalog(ROOT / "schemas/document/examples/satimol-folders.example.json"),
        load_folder_grants(ROOT / "schemas/org/examples/satimol-folder-grants.example.json"),
        as_of=date(2025, 9, 10),
    )


def _policy_context():
    snapshot = load_org_snapshot(ROOT / "schemas/org/examples/satimol-snapshot.example.json")
    return build_policy_context(
        snapshot,
        employee_id="emp_litovsky_d",
        env="production",
        as_of=date(2025, 9, 10),
    )


def test_scan_regulations_archive(tmp_path: Path):
    (tmp_path / "reglament.pdf").write_bytes(b"%PDF-1.4 test doc")
    (tmp_path / "org.vsdx").write_bytes(b"PK fake vsdx")
    (tmp_path / "skip.tmp").write_bytes(b"x")

    manifest = scan_regulations_archive(tmp_path, compute_hash=True)
    assert manifest["total_files"] == 3
    assert manifest["stats"]["ingest_candidate"] == 1
    assert manifest["stats"]["catalog_only"] == 1
    assert manifest["stats"]["skip"] == 1
    pdf = next(e for e in manifest["entries"] if e["file_name"] == "reglament.pdf")
    assert pdf["content_hash"].startswith("sha256:")


def test_scan_regulations_archive_not_found():
    with pytest.raises(FileNotFoundError):
        scan_regulations_archive(Path("/nonexistent/archive"))


def test_import_regulations_batch(tmp_path: Path):
    (tmp_path / "a.txt").write_text("маркшейдерская съёмка регламент", encoding="utf-8")
    (tmp_path / "b.pdf").write_bytes("%PDF регламент маркшейдер".encode("utf-8"))

    out = tmp_path / "out"
    index = ChunkIndex()
    result = import_regulations_batch(
        tmp_path,
        policy_context=_policy_context(),
        classification="restricted",
        folder_id="folder_ms_open",
        folder_acl=_folder_acl(),
        dedup_store=DedupStore(),
        index=index,
        limit=2,
        extensions={".txt", ".pdf"},
        state_path=out / "state.json",
        chunks_path=out / "chunks.json",
    )
    assert result["imported_count"] == 2
    assert len(index.list()) == 2


def test_import_regulations_skip_temp_office_files(tmp_path: Path):
    (tmp_path / "~$draft.docx").write_bytes(b"PK fake temp")
    (tmp_path / "ok.txt").write_text("нормальный документ", encoding="utf-8")
    out = tmp_path / "out"
    index = ChunkIndex()
    result = import_regulations_batch(
        tmp_path,
        policy_context=_policy_context(),
        classification="restricted",
        folder_id="folder_ms_open",
        folder_acl=_folder_acl(),
        dedup_store=DedupStore(),
        index=index,
        extensions={".txt", ".docx"},
        state_path=out / "state.json",
        chunks_path=out / "chunks.json",
    )
    assert result["imported_count"] == 1
    assert result["skip_temp_count"] == 1


def test_import_regulations_resume(tmp_path: Path):
    (tmp_path / "a.txt").write_text("документ a", encoding="utf-8")
    (tmp_path / "b.txt").write_text("документ b", encoding="utf-8")
    out = tmp_path / "out"
    index = ChunkIndex()
    kwargs = dict(
        policy_context=_policy_context(),
        classification="restricted",
        folder_id="folder_ms_open",
        folder_acl=_folder_acl(),
        dedup_store=DedupStore(),
        index=index,
        limit=1,
        extensions={".txt"},
        state_path=out / "state.json",
        chunks_path=out / "chunks.json",
        checkpoint_every=1,
    )
    from tmki_ingest.regulations import import_regulations_full

    r1 = import_regulations_full(tmp_path, **kwargs)
    assert r1["imported_count"] == 1
    kwargs2 = {**kwargs, "index": ChunkIndex(), "limit": 2}
    r2 = import_regulations_full(tmp_path, **kwargs2)
    assert r2["imported_count"] == 2
    assert len(kwargs2["index"].list()) == 2
