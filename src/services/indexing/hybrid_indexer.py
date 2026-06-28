import logging
from datetime import datetime, timezone
from typing import Any, Dict, Protocol

from src.schemas.indexing.models import TextChunk
from src.services.opensearch.client import OpenSearchClient

logger = logging.getLogger(__name__)


class EmbeddingsClientProtocol(Protocol):
    async def embed_passages(self, texts: list[str], batch_size: int = 50) -> list[list[float]]: ...


class TextChunkerProtocol(Protocol):
    def chunk_text(self, text: str, document_id: str, version_id: str) -> list[TextChunk]: ...


class HybridIndexingService:
    """Chunk documents, embed passages, and index into OpenSearch."""

    def __init__(
        self,
        chunker: TextChunkerProtocol,
        embeddings_client: EmbeddingsClientProtocol,
        opensearch_client: OpenSearchClient,
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        self.chunker = chunker
        self.embeddings_client = embeddings_client
        self.opensearch_client = opensearch_client
        self.embedding_model_name = embedding_model_name
        logger.info("Hybrid indexing service initialized")

    async def index_document(self, document_data: Dict[str, Any]) -> Dict[str, int]:
        document_id = document_data.get("document_id")
        if not document_id:
            logger.error("Document missing document_id")
            return {"chunks_created": 0, "chunks_indexed": 0, "embeddings_generated": 0, "errors": 1}

        try:
            raw_text = document_data.get("raw_text") or ""
            chunks = self.chunker.chunk_text(
                text=raw_text,
                document_id=document_id,
                version_id=str(document_data.get("id", "")),
            )

            if not chunks:
                logger.warning(f"No chunks created for document {document_id}")
                return {"chunks_created": 0, "chunks_indexed": 0, "embeddings_generated": 0, "errors": 0}

            chunk_texts = [chunk.text for chunk in chunks]
            embeddings = await self.embeddings_client.embed_passages(texts=chunk_texts, batch_size=32)

            if len(embeddings) != len(chunks):
                logger.error(f"Embedding count mismatch: {len(embeddings)} != {len(chunks)}")
                return {
                    "chunks_created": len(chunks),
                    "chunks_indexed": 0,
                    "embeddings_generated": len(embeddings),
                    "errors": 1,
                }

            chunks_with_embeddings = []
            for chunk, embedding in zip(chunks, embeddings):
                chunk_data = {
                    "document_id": document_id,
                    "paper_id": str(document_data.get("id", "")),
                    "chunk_index": chunk.metadata.chunk_index,
                    "chunk_text": chunk.text,
                    "chunk_word_count": chunk.metadata.word_count,
                    "start_char": chunk.metadata.start_char,
                    "end_char": chunk.metadata.end_char,
                    "section_title": chunk.metadata.section_title,
                    "embedding_model": self.embedding_model_name,
                    "title": document_data.get("title", ""),
                    "description": document_data.get("description", ""),
                    "department": document_data.get("department", ""),
                    "access_level": document_data.get("access_level", "internal"),
                    "document_type": document_data.get("document_type", ""),
                    "owner_id": document_data.get("owner_id", ""),
                    "contributors": document_data.get("contributors", []),
                    "version": document_data.get("version", 1),
                    "is_latest": document_data.get("is_latest", True),
                    "file_path": document_data.get("file_path", ""),
                }
                chunks_with_embeddings.append({"chunk_data": chunk_data, "embedding": embedding})

            results = self.opensearch_client.bulk_index_chunks(chunks_with_embeddings)
            logger.info(
                f"Indexed document {document_id}: {results['success']} chunks indexed, "
                f"{results['failed']} failed"
            )

            return {
                "chunks_created": len(chunks),
                "chunks_indexed": results["success"],
                "embeddings_generated": len(embeddings),
                "errors": results["failed"],
            }
        except Exception as e:
            logger.error(f"Error indexing document {document_id}: {e}")
            return {"chunks_created": 0, "chunks_indexed": 0, "embeddings_generated": 0, "errors": 1}

    async def index_documents_batch(self, documents: list[Dict[str, Any]], replace_existing: bool = False) -> Dict[str, int]:
        total_stats = {
            "documents_processed": 0,
            "total_chunks_created": 0,
            "total_chunks_indexed": 0,
            "total_embeddings_generated": 0,
            "total_errors": 0,
        }

        for document in documents:
            document_id = document.get("document_id")
            if replace_existing and document_id:
                self.opensearch_client.delete_document_chunks(document_id)

            stats = await self.index_document(document)
            total_stats["documents_processed"] += 1
            total_stats["total_chunks_created"] += stats["chunks_created"]
            total_stats["total_chunks_indexed"] += stats["chunks_indexed"]
            total_stats["total_embeddings_generated"] += stats["embeddings_generated"]
            total_stats["total_errors"] += stats["errors"]

        return total_stats

    async def reindex_document(self, document_id: str, document_data: Dict[str, Any]) -> Dict[str, int]:
        self.opensearch_client.delete_document_chunks(document_id)
        return await self.index_document(document_data)
