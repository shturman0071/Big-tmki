"""RAG с server-side RLS (до ранжирования)."""

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
    "EmbeddingProvider",
    "FolderAclContext",
    "LocalHashEmbeddingProvider",
    "OllamaEmbeddingProvider",
    "OpenAiEmbeddingProvider",
    "VectorChunkIndex",
    "get_chunk_index",
    "get_embedding_provider",
    "hybrid_score_fn",
    "load_folder_catalog",
    "load_folder_grants",
    "resolve_folder_id",
    "rag_search",
]
