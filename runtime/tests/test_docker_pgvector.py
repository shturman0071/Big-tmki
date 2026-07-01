from pathlib import Path


def test_docker_compose_files_exist():
    docker_dir = Path(__file__).resolve().parents[1] / "docker"
    assert (docker_dir / "docker-compose.yml").is_file()
    assert (docker_dir / "init.sql").is_file()
    assert (docker_dir / "env.example").is_file()
    compose = (docker_dir / "docker-compose.yml").read_text(encoding="utf-8")
    assert "pgvector/pgvector" in compose
    init_sql = (docker_dir / "init.sql").read_text(encoding="utf-8")
    assert "CREATE EXTENSION IF NOT EXISTS vector" in init_sql
