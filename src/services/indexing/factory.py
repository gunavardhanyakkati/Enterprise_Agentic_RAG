from typing import Optional

from src.config import Settings, get_settings
from src.services.embeddings.factory import make_embeddings_client
from src.services.opensearch.factory import make_opensearch_client_fresh

from .hybrid_indexer import HybridIndexingService
from .recursive_chunker import RecursiveTextChunker


def make_hybrid_indexing_service(
    settings: Optional[Settings] = None, opensearch_host: Optional[str] = None
) -> HybridIndexingService:
    if settings is None:
        settings = get_settings()

    chunker = RecursiveTextChunker(
        chunk_size=settings.chunking.chunk_size,
        chunk_overlap=settings.chunking.overlap_size,
    )
    embeddings_client = make_embeddings_client(settings)
    opensearch_client = make_opensearch_client_fresh(settings, host=opensearch_host)

    return HybridIndexingService(
        chunker=chunker,
        embeddings_client=embeddings_client,
        opensearch_client=opensearch_client,
        embedding_model_name=settings.embeddings.local_model
        if settings.embeddings.provider == "local"
        else "jina-embeddings-v3",
    )
