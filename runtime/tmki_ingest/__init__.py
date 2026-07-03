"""Ingest gate — проверка upload/delete до pipeline (Document Intelligence)."""

from tmki_ingest.dedup import DedupStore, check_dedup, compute_content_hash, dedup_key
from tmki_ingest.gate import IngestGateResult, validate_delete, validate_ingest
from tmki_rag.index import ChunkIndex
from tmki_ingest.pipeline import DocumentPipelineResult, IngestAcceptResult, accept_ingest, ingest_and_index, process_document
from tmki_ingest.regulations import (
    build_ingest_request,
    import_regulations_batch,
    import_regulations_full,
    reindex_regulations_full,
    reindex_regulations_incremental,
    scan_regulations_archive,
)

__all__ = [
    "ChunkIndex",
    "DedupStore",
    "DocumentPipelineResult",
    "IngestAcceptResult",
    "IngestGateResult",
    "accept_ingest",
    "build_ingest_request",
    "check_dedup",
    "compute_content_hash",
    "dedup_key",
    "import_regulations_batch",
    "import_regulations_full",
    "reindex_regulations_full",
    "reindex_regulations_incremental",
    "ingest_and_index",
    "process_document",
    "scan_regulations_archive",
    "validate_delete",
    "validate_ingest",
]
