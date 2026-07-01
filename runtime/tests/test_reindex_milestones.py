from pathlib import Path

from tmki_ingest.reindex_milestones import list_done_milestones, milestone_summary


def test_milestone_summary_next_at_49(tmp_path: Path):
    ms = milestone_summary(49.2, tmp_path)
    assert ms["next_milestone"] == 50
    assert ms["milestone_ready"] == 25


def test_milestone_summary_ready_at_50(tmp_path: Path):
    (tmp_path / "milestone-25.json").write_text("{}", encoding="utf-8")
    ms = milestone_summary(50.0, tmp_path)
    assert ms["milestone_ready"] == 50


def test_milestone_summary_skips_done(tmp_path: Path):
    (tmp_path / "milestone-25.json").write_text("{}", encoding="utf-8")
    (tmp_path / "milestone-50.json").write_text("{}", encoding="utf-8")
    ms = milestone_summary(55.0, tmp_path)
    assert ms["milestones_done"] == [25, 50]
    assert ms["milestone_ready"] is None
    assert ms["next_milestone"] == 75


def test_list_done_milestones(tmp_path: Path):
    (tmp_path / "milestone-25.json").write_text("{}", encoding="utf-8")
    assert list_done_milestones(tmp_path) == [25]
