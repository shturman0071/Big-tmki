"""SharePoint ACL sync (stub adapter для MVP)."""

from tmki_sharepoint.graph import GraphSharePointAdapter, get_sharepoint_adapter, sync_grants_to_sharepoint
from tmki_sharepoint.sync import (
    SharePointPermissionChange,
    StubSharePointAdapter,
    build_sync_plan,
)

__all__ = [
    "GraphSharePointAdapter",
    "SharePointPermissionChange",
    "StubSharePointAdapter",
    "build_sync_plan",
    "get_sharepoint_adapter",
    "sync_grants_to_sharepoint",
]
