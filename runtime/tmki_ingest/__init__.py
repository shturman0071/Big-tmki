"""Ingest gate — проверка upload/delete до pipeline (Document Intelligence)."""

from tmki_ingest.dedup import DedupStore, check_dedup, compute_content_hash, dedup_key
from tmki_ingest.gate import IngestGateResult, validate_delete, validate_ingest
from tmki_ingest.pipeline import DocumentPipelineResult, IngestAcceptResult, accept_ingest, process_document

__all__ = [
    "DedupStore",
    "DocumentPipelineResult",
    "IngestAcceptResult",
    "IngestGateResult",
    "accept_ingest",
    "check_dedup",
    "compute_content_hash",
    "dedup_key",
    "process_document",
    "validate_delete",
    "validate_ingest",
]
