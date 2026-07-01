"""Ingest gate — проверка upload/delete до pipeline (Document Intelligence)."""

from tmki_ingest.dedup import DedupStore, check_dedup, compute_content_hash, dedup_key
from tmki_ingest.gate import IngestGateResult, validate_delete, validate_ingest
from tmki_ingest.pipeline import IngestAcceptResult, accept_ingest

__all__ = [
    "DedupStore",
    "IngestAcceptResult",
    "IngestGateResult",
    "accept_ingest",
    "check_dedup",
    "compute_content_hash",
    "dedup_key",
    "validate_delete",
    "validate_ingest",
]
