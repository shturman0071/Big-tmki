import os

import pytest

from tmki_sharepoint import StubSharePointAdapter, get_sharepoint_adapter


def test_get_sharepoint_adapter_stub_default(monkeypatch):
    monkeypatch.delenv("AZURE_TENANT_ID", raising=False)
    monkeypatch.setenv("TMKI_SHAREPOINT_ADAPTER", "stub")
    adapter = get_sharepoint_adapter()
    assert isinstance(adapter, StubSharePointAdapter)


def test_get_sharepoint_adapter_graph_requires_env(monkeypatch):
    monkeypatch.setenv("TMKI_SHAREPOINT_ADAPTER", "graph")
    monkeypatch.delenv("AZURE_TENANT_ID", raising=False)
    with pytest.raises(RuntimeError, match="AZURE"):
        get_sharepoint_adapter()
