from unittest.mock import MagicMock, patch

from tmki_runtime.docker_check import docker_daemon_ready


def test_docker_daemon_ready_ok():
    proc = MagicMock(returncode=0, stdout="Server Version: 29", stderr="")
    with patch("tmki_runtime.docker_check.shutil.which", return_value="/usr/bin/docker"), patch(
        "tmki_runtime.docker_check.subprocess.run", return_value=proc
    ):
        ok, detail = docker_daemon_ready()
    assert ok is True
    assert "running" in detail


def test_docker_daemon_ready_missing_cli():
    with patch("tmki_runtime.docker_check.shutil.which", return_value=None):
        ok, detail = docker_daemon_ready()
    assert ok is False
    assert "not found" in detail
