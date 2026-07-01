"""Админ-UI и API управления folder grant/deny (MVP)."""

from tmki_admin.grants_service import GrantService, GrantStore, open_grant_service

__all__ = ["GrantService", "GrantStore", "open_grant_service"]
