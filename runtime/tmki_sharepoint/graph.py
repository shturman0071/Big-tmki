from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from tmki_sharepoint.sync import SharePointPermissionChange, StubSharePointAdapter, build_sync_plan


class GraphSharePointAdapter:
    """
    Каркас Microsoft Graph / SharePoint ACL sync.
    Требует: AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, SHAREPOINT_SITE_ID.
  """

    def __init__(
        self,
        *,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        site_id: str,
        graph_scope: str = "https://graph.microsoft.com/.default",
    ) -> None:
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._site_id = site_id
        self._graph_scope = graph_scope
        self._token: str | None = None

    @classmethod
    def from_env(cls) -> GraphSharePointAdapter | None:
        tenant = os.environ.get("AZURE_TENANT_ID")
        client = os.environ.get("AZURE_CLIENT_ID")
        secret = os.environ.get("AZURE_CLIENT_SECRET")
        site = os.environ.get("SHAREPOINT_SITE_ID")
        if not all((tenant, client, secret, site)):
            return None
        return cls(
            tenant_id=tenant,
            client_id=client,
            client_secret=secret,
            site_id=site,
        )

    def _fetch_token(self) -> str:
        if self._token:
            return self._token
        url = f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token"
        body = (
            f"client_id={self._client_id}"
            f"&client_secret={self._client_secret}"
            f"&scope={self._graph_scope}"
            "&grant_type=client_credentials"
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            err = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Graph token error {exc.code}: {err}") from exc
        self._token = data["access_token"]
        return self._token

    def apply(self, plan: list[SharePointPermissionChange]) -> dict[str, Any]:
        token = self._fetch_token()
        applied: list[dict[str, Any]] = []
        for change in plan:
            # MVP: фиксируем намерение; production — driveItem permissions API
            applied.append(
                {
                    "site_id": self._site_id,
                    "path": change.physical_path,
                    "employee_id": change.employee_id,
                    "action": change.action,
                    "graph_status": "planned",
                    "token_prefix": token[:8] + "...",
                }
            )
        return {
            "adapter": "graph",
            "changes_applied": len(applied),
            "items": applied,
        }


def get_sharepoint_adapter() -> StubSharePointAdapter | GraphSharePointAdapter:
    """TMKI_SHAREPOINT_ADAPTER=stub|graph (auto graph if env задан)."""
    mode = os.environ.get("TMKI_SHAREPOINT_ADAPTER", "auto").lower()
    graph = GraphSharePointAdapter.from_env()
    if mode == "graph":
        if not graph:
            raise RuntimeError("Graph adapter: не заданы AZURE_* / SHAREPOINT_SITE_ID")
        return graph
    if mode == "stub":
        return StubSharePointAdapter()
    return graph or StubSharePointAdapter()


def sync_grants_to_sharepoint(
    grants: list[dict[str, Any]],
    folders: list[dict[str, Any]],
) -> dict[str, Any]:
    adapter = get_sharepoint_adapter()
    plan = build_sync_plan(grants, folders)
    return adapter.apply(plan)
