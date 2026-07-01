"""SharePoint ACL sync (stub adapter для MVP)."""

from tmki_sharepoint.sync import (
    SharePointPermissionChange,
    StubSharePointAdapter,
    build_sync_plan,
)

__all__ = ["SharePointPermissionChange", "StubSharePointAdapter", "build_sync_plan"]
