from tmki_demo.director_dashboard import build_director_dashboard, ensure_seed_file


def test_build_director_dashboard():
    ensure_seed_file()
    dash = build_director_dashboard(index_stats={"skru-2": 1000})
    assert dash["role_key"] == "Direktor"
    assert dash["role_label"] == "Директор"
    assert len(dash["contracts"]) >= 5
    assert len(dash["objects"]) >= 4
    assert "satimola" in dash["briefs"]
    assert dash["system"]["index_skru2_chunks"] == 1000
    assert dash["agent"]["corpus_default"] == "skru-2"
