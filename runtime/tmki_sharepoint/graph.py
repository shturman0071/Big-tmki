from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from tmki_sharepoint.sync import SharePointPermissionChange, StubSharePointAdapter, build_sync_plan

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class GraphSharePointAdapter:
    """
    Microsoft Graph / SharePoint ACL sync.
    Env: AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, SHAREPOINT_SITE_ID.
    TMKI_GRAPH_DRY_RUN=1 (default) — только план операций без HTTP к Graph.
    """

    def __init__(
        self,
        *,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        site_id: str,
        graph_scope: str = "https://graph.microsoft.com/.default",
        employee_upn_map: dict[str, str] | None = None,
    ) -> None:
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._site_id = site_id
        self._graph_scope = graph_scope
        self._token: str | None = None
        self._employee_upn_map = employee_upn_map or {}

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

    def _employee_upn(self, employee_id: str) -> str:
        if employee_id in self._employee_upn_map:
            return self._employee_upn_map[employee_id]
        domain = os.environ.get("SHAREPOINT_USER_DOMAIN", "tmki.local")
        return f"{employee_id}@{domain}"

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

    def _build_operation(self, change: SharePointPermissionChange) -> dict[str, Any]:
        path = change.physical_path.rstrip("/")
        drive_path = f"/sites/{self._site_id}/drive/root:{path}"
        upn = self._employee_upn(change.employee_id)

        if change.action in ("add_read", "add_write"):
            role = "write" if change.action == "add_write" else "read"
            return {
                "method": "POST",
                "url": f"{_GRAPH_BASE}{drive_path}:/invite",
                "body": {
                    "recipients": [{"email": upn}],
                    "roles": [role],
                    "sendInvitation": False,
                },
                "employee_id": change.employee_id,
                "action": change.action,
                "grant_id": change.grant_id,
            }

        return {
            "method": "POST",
            "url": f"{_GRAPH_BASE}{drive_path}:/permissions/revoke",
            "body": {
                "recipient": {"email": upn},
                "permission": "read" if change.action == "remove_read" else "write",
            },
            "employee_id": change.employee_id,
            "action": change.action,
            "grant_id": change.grant_id,
        }

    def _execute(self, op: dict[str, Any], token: str) -> dict[str, Any]:
        req = urllib.request.Request(
            op["url"],
            data=json.dumps(op.get("body") or {}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method=op["method"],
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                body = json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            err = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Graph API {exc.code} {op['url']}: {err}") from exc
        return {"status": "ok", "response": body}

    def apply(self, plan: list[SharePointPermissionChange]) -> dict[str, Any]:
        dry_run = os.environ.get("TMKI_GRAPH_DRY_RUN", "1") == "1"
        items: list[dict[str, Any]] = []
        token: str | None = None
        if not dry_run:
            token = self._fetch_token()

        for change in plan:
            op = self._build_operation(change)
            entry = {
                "path": change.physical_path,
                "employee_id": change.employee_id,
                "action": change.action,
                "graph_method": op["method"],
                "graph_url": op["url"],
            }
            if dry_run:
                entry["graph_status"] = "dry_run"
            else:
                assert token is not None
                result = self._execute(op, token)
                entry["graph_status"] = result["status"]
            items.append(entry)

        return {
            "adapter": "graph",
            "dry_run": dry_run,
            "changes_applied": len(items),
            "items": items,
        }


def get_sharepoint_adapter() -> StubSharePointAdapter | GraphSharePointAdapter:
    """TMKI_SHAREPOINT_ADAPTER=stub|graph|auto"""
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
