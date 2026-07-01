from pathlib import Path

from tmki_voice.display import StubDisplayProvider, cast_mvp_output
from tmki_desktop_sync.ingest_hook import ingest_synced_file


def test_display_stub_writes_artifact(tmp_path):
    provider = StubDisplayProvider(tmp_path)
    r = provider.show({"answer": "тест"}, target=__import__("tmki_voice.display", fromlist=["DisplayTarget"]).DisplayTarget.COMPUTER)
    assert r.delivered
    assert Path(r.detail).is_file()


def test_cast_mvp_output():
    r = cast_mvp_output({"answer": "ответ"}, target="computer")
    assert r.target == "computer"


def test_ingest_synced_txt(tmp_path):
    f = tmp_path / "note.txt"
    f.write_text("маркшейдерская съёмка регламент", encoding="utf-8")
    out = ingest_synced_file(f)
    assert out["ingest_status"] in ("accepted", "duplicate", "processing")
    assert out["chunks"] >= 0
