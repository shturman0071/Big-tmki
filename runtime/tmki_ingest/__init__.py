"""Ingest gate — проверка upload/delete до pipeline (Document Intelligence)."""

from tmki_ingest.gate import IngestGateResult, validate_delete, validate_ingest

__all__ = ["IngestGateResult", "validate_delete", "validate_ingest"]
