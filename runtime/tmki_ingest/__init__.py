"""Ingest gate — проверка upload/delete до pipeline (Document Intelligence)."""

from tmki_ingest.dedup import DedupStore, check_dedup, compute_content_hash, dedup_key
from tmki_ingest.gate import IngestGateResult, validate_delete, validate_ingest
from tmki_rag.index import ChunkIndex
from tmki_ingest.pipeline import DocumentPipelineResult, IngestAcceptResult, accept_ingest, ingest_and_index, process_document

__all__ = [
    "ChunkIndex",
    "DedupStore",
    "DocumentPipelineResult",
    "IngestAcceptResult",
    "IngestGateResult",
    "accept_ingest",
    "check_dedup",
    "compute_content_hash",
    "dedup_key",
    "ingest_and_index",
    "process_document",
    "validate_delete",
    "validate_ingest",
]
