from __future__ import annotations

import os
from typing import Any

from tmki_sharepoint.http import HttpRequestFn, default_http_request
from tmki_sharepoint.sync import SharePointPermissionChange, StubSharePointAdapter, build_sync_plan

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class GraphSharePointAdapter:
    """
    Microsoft Graph / SharePoint ACL sync (production path).
    Env: AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, SHAREPOINT_SITE_ID.
    TMKI_GRAPH_DRY_RUN=1 (default) — план операций без HTTP.
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
        http_request: HttpRequestFn | None = None,
    ) -> None:
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._site_id = site_id
        self._graph_scope = graph_scope
        self._token: str | None = None
        self._employee_upn_map = employee_upn_map or {}
        self._http_request = http_request or default_http_request

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
        import urllib.error
        import urllib.request

        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                import json

                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            err = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Graph token error {exc.code}: {err}") from exc
        self._token = data["access_token"]
        return self._token

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _resolve_drive_item(self, physical_path: str, token: str) -> dict[str, Any]:
        path = physical_path.rstrip("/")
        url = f"{_GRAPH_BASE}/sites/{self._site_id}/drive/root:{path}"
        resp = self._http_request("GET", url, None, self._headers(token))
        if resp.get("error"):
            raise RuntimeError(f"Graph resolve failed {resp.get('status_code')}: {resp.get('body')}")
        body = resp["body"]
        drive_id = body.get("parentReference", {}).get("driveId")
        item_id = body.get("id")
        if not drive_id or not item_id:
            raise RuntimeError(f"Graph resolve: missing driveId/id for {path}")
        return {"drive_id": drive_id, "item_id": item_id}

    def _list_permissions(self, drive_id: str, item_id: str, token: str) -> list[dict[str, Any]]:
        url = f"{_GRAPH_BASE}/drives/{drive_id}/items/{item_id}/permissions"
        resp = self._http_request("GET", url, None, self._headers(token))
        if resp.get("error"):
            raise RuntimeError(f"Graph list permissions failed: {resp.get('body')}")
        return list(resp["body"].get("value", []))

    def _find_permission_id(
        self,
        permissions: list[dict[str, Any]],
        upn: str,
        action: str,
    ) -> str | None:
        want = "write" if action == "remove_write" else "read"
        upn_lower = upn.lower()
        for perm in permissions:
            granted = perm.get("grantedToV2") or perm.get("grantedTo") or {}
            user = granted.get("user") or {}
            email = (user.get("email") or user.get("userPrincipalName") or "").lower()
            if email != upn_lower:
                continue
            roles = {r.lower() for r in perm.get("roles", [])}
            if want == "write" and ("write" in roles or "owner" in roles):
                return perm.get("id")
            if want == "read" and roles:
                return perm.get("id")
        return None

    def _build_operation(self, change: SharePointPermissionChange) -> dict[str, Any]:
        path = change.physical_path.rstrip("/")
        upn = self._employee_upn(change.employee_id)
        resolve_url = f"{_GRAPH_BASE}/sites/{self._site_id}/drive/root:{path}"

        if change.action in ("add_read", "add_write"):
            role = "write" if change.action == "add_write" else "read"
            return {
                "steps": [
                    {"step": "resolve", "method": "GET", "url": resolve_url},
                    {
                        "step": "invite",
                        "method": "POST",
                        "url_template": f"{_GRAPH_BASE}/drives/{{drive_id}}/items/{{item_id}}/invite",
                        "body": {
                            "recipients": [{"email": upn}],
                            "roles": [role],
                            "sendInvitation": False,
                        },
                    },
                ],
                "employee_id": change.employee_id,
                "action": change.action,
                "grant_id": change.grant_id,
            }

        return {
            "steps": [
                {"step": "resolve", "method": "GET", "url": resolve_url},
                {
                    "step": "revoke",
                    "method": "DELETE",
                    "url_template": f"{_GRAPH_BASE}/drives/{{drive_id}}/items/{{item_id}}/permissions/{{permission_id}}",
                    "target_upn": upn,
                    "permission_kind": "write" if change.action == "remove_write" else "read",
                },
            ],
            "employee_id": change.employee_id,
            "action": change.action,
            "grant_id": change.grant_id,
        }

    def _execute_operation(self, op: dict[str, Any], token: str) -> dict[str, Any]:
        steps_done: list[dict[str, Any]] = []
        drive_id: str | None = None
        item_id: str | None = None

        for step in op["steps"]:
            if step["step"] == "resolve":
                resp = self._http_request("GET", step["url"], None, self._headers(token))
                if resp.get("error"):
                    raise RuntimeError(f"resolve failed: {resp.get('body')}")
                body = resp["body"]
                drive_id = body["parentReference"]["driveId"]
                item_id = body["id"]
                steps_done.append({"step": "resolve", "item_id": item_id})
                continue

            if step["step"] == "invite":
                assert drive_id and item_id
                url = step["url_template"].format(drive_id=drive_id, item_id=item_id)
                resp = self._http_request("POST", url, step["body"], self._headers(token))
                if resp.get("error"):
                    raise RuntimeError(f"invite failed: {resp.get('body')}")
                steps_done.append({"step": "invite", "status_code": resp["status_code"]})
                continue

            if step["step"] == "revoke":
                assert drive_id and item_id
                perms = self._list_permissions(drive_id, item_id, token)
                perm_id = self._find_permission_id(
                    perms,
                    step["target_upn"],
                    "remove_write" if step.get("permission_kind") == "write" else "remove_read",
                )
                if not perm_id:
                    steps_done.append({"step": "revoke", "status": "skipped"})
                    continue
                url = step["url_template"].format(
                    drive_id=drive_id,
                    item_id=item_id,
                    permission_id=perm_id,
                )
                resp = self._http_request("DELETE", url, None, self._headers(token))
                if resp.get("error") and resp.get("status_code") not in (204, 404):
                    raise RuntimeError(f"revoke failed: {resp.get('body')}")
                steps_done.append({"step": "revoke", "permission_id": perm_id})

        return {"status": "ok", "steps": steps_done}

    def apply(self, plan: list[SharePointPermissionChange]) -> dict[str, Any]:
        dry_run = os.environ.get("TMKI_GRAPH_DRY_RUN", "1") == "1"
        items: list[dict[str, Any]] = []
        token: str | None = None
        if not dry_run:
            token = self._fetch_token()

        for change in plan:
            op = self._build_operation(change)
            entry: dict[str, Any] = {
                "path": change.physical_path,
                "employee_id": change.employee_id,
                "action": change.action,
                "steps": [s["step"] for s in op["steps"]],
            }
            if dry_run:
                entry["graph_status"] = "dry_run"
            else:
                assert token is not None
                result = self._execute_operation(op, token)
                entry["graph_status"] = result["status"]
                entry["steps_done"] = result["steps"]
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
