"""RAG с server-side RLS (до ранжирования)."""

from tmki_rag.chunks_io import DEFAULT_REGULATIONS_CHUNKS, load_chunks_file, load_regulations_chunks
from tmki_rag.folders import FolderAclContext, load_folder_catalog, load_folder_grants, resolve_folder_id
from tmki_rag.embedding_providers import (
    EmbeddingProvider,
    LocalHashEmbeddingProvider,
    OllamaEmbeddingProvider,
    OpenAiEmbeddingProvider,
    get_embedding_provider,
)
from tmki_rag.index import ChunkIndex
from tmki_rag.search import rag_search
from tmki_rag.vector import VectorChunkIndex, get_chunk_index, hybrid_score_fn

__all__ = [
    "ChunkIndex",
    "DEFAULT_REGULATIONS_CHUNKS",
    "EmbeddingProvider",
    "FolderAclContext",
    "LocalHashEmbeddingProvider",
    "OllamaEmbeddingProvider",
    "OpenAiEmbeddingProvider",
    "VectorChunkIndex",
    "get_chunk_index",
    "get_embedding_provider",
    "hybrid_score_fn",
    "load_chunks_file",
    "load_regulations_chunks",
    "load_folder_catalog",
    "load_folder_grants",
    "resolve_folder_id",
    "rag_search",
]
