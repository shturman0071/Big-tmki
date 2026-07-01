import json
from pathlib import Path

from tmki_ingest.reindex_lock import acquire_reindex_lock, process_alive, read_lock, release_reindex_lock


def test_acquire_and_release_lock(tmp_path: Path):
    lock = tmp_path / "reindex.lock"
    assert acquire_reindex_lock(lock) is None
    data = read_lock(lock)
    assert data is not None
    assert data["pid"] > 0
    release_reindex_lock(lock)
    assert not lock.is_file()


def test_acquire_blocks_second_holder(tmp_path: Path, monkeypatch):
    lock = tmp_path / "reindex.lock"
    lock.write_text(json.dumps({"pid": 999999, "started_at": "t"}), encoding="utf-8")
    monkeypatch.setattr("tmki_ingest.reindex_lock.process_alive", lambda pid: pid == 999999)
    held = acquire_reindex_lock(lock)
    assert held is not None
    assert held["pid"] == 999999


def test_force_lock_replaces_stale(tmp_path: Path, monkeypatch):
    import os

    lock = tmp_path / "reindex.lock"
    lock.write_text(json.dumps({"pid": 1, "started_at": "t"}), encoding="utf-8")
    monkeypatch.setattr("tmki_ingest.reindex_lock.process_alive", lambda pid: True)
    assert acquire_reindex_lock(lock, force=True) is None
    assert read_lock(lock)["pid"] == os.getpid()
