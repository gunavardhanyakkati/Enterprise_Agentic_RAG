import logging
from typing import Dict, List, Optional

from src.services.embeddings.jina_client import JinaEmbeddingsClient
from src.services.opensearch.client import OpenSearchClient

from .text_chunker import TextChunker

logger = logging.getLogger(__name__)


class HybridIndexingService:
    """Service for indexing documents with chunking and embeddings for hybrid search.

    Orchestrates the process of:
    1. Chunking documents into overlapping segments
    2. Generating embeddings for each chunk
    3. Indexing chunks with embeddings into OpenSearch
    """

    def __init__(self, chunker: TextChunker, embeddings_client: JinaEmbeddingsClient, opensearch_client: OpenSearchClient):
        """Initialize hybrid indexing service.

        :param chunker: Text chunking service
        :param embeddings_client: Embeddings generation client
        :param opensearch_client: OpenSearch client
        """
        self.chunker = chunker
        self.embeddings_client = embeddings_client
        self.opensearch_client = opensearch_client

        logger.info("Hybrid indexing service initialized")

    async def index_document(self, document_data: Dict) -> Dict[str, int]:
        """Index a single document with chunking and embeddings.

        :param document_data: Document data from database
        :returns: Dictionary with indexing statistics
        """
        document_id = document_data.get("document_id")
        
        if not document_id:
            logger.error("Document missing document_id")
            return {"chunks_created": 0, "chunks_indexed": 0, "embeddings_generated": 0, "errors": 1}

        try:
            # Step 1: Chunk the document using hybrid section-based approach
            chunks = self.chunker.chunk_text(
                full_text=document_data.get("raw_text", ""),
                arxiv_id=document_id,
                paper_id=str(document_data.get("id", "")),
            )

            if not chunks:
                logger.warning(f"No chunks created for document {document_id}")
                return {"chunks_created": 0, "chunks_indexed": 0, "embeddings_generated": 0, "errors": 0}

            logger.info(f"Created {len(chunks)} chunks for document {document_id}")

            # Step 2: Generate embeddings for chunks
            chunk_texts = [chunk.text for chunk in chunks]
            embeddings = await self.embeddings_client.embed_passages(
                texts=chunk_texts,
                batch_size=50,
            )

            if len(embeddings) != len(chunks):
                logger.error(f"Embedding count mismatch: {len(embeddings)} != {len(chunks)}")
                return {"chunks_created": len(chunks), "chunks_indexed": 0, "embeddings_generated": len(embeddings), "errors": 1}

            # Step 3: Prepare chunks with embeddings for indexing
            chunks_with_embeddings = []

            for chunk, embedding in zip(chunks, embeddings):
                # Prepare chunk data for OpenSearch
                chunk_data = {
                    "document_id": document_id,
                    "paper_id": str(document_data.get("id", "")),
                    "chunk_index": chunk.metadata.chunk_index,
                    "chunk_text": chunk.text,
                    "chunk_word_count": chunk.metadata.word_count,
                    "start_char": chunk.metadata.start_char,
                    "end_char": chunk.metadata.end_char,
                    "section_title": chunk.metadata.section_title,
                    "embedding_model": "jina-embeddings-v3",
                    # Denormalized enterprise metadata for efficient search and filtering
                    "title": document_data.get("title", ""),
                    "description": document_data.get("description", ""),
                    "department": document_data.get("department", ""),
                    "access_level": document_data.get("access_level", "internal"),
                    "document_type": document_data.get("document_type", ""),
                    "owner_id": document_data.get("owner_id", ""),
                    "contributors": document_data.get("contributors", []),
                    "version": document_data.get("version", 1),
                    "is_latest": document_data.get("is_latest", True),
                }

                chunks_with_embeddings.append({"chunk_data": chunk_data, "embedding": embedding})

            # Step 4: Index chunks into OpenSearch
            results = self.opensearch_client.bulk_index_chunks(chunks_with_embeddings)

            logger.info(f"Indexed document {document_id}: {results['success']} chunks successful, {results['failed']} failed")

            return {
                "chunks_created": len(chunks),
                "chunks_indexed": results["success"],
                "embeddings_generated": len(embeddings),
                "errors": results["failed"],
            }

        except Exception as e:
            logger.error(f"Error indexing document {document_id}: {e}")
            return {"chunks_created": 0, "chunks_indexed": 0, "embeddings_generated": 0, "errors": 1}

    async def index_documents_batch(self, documents: List[Dict], replace_existing: bool = False) -> Dict[str, int]:
        """Index multiple documents in batch.

        :param documents: List of document data
        :param replace_existing: If True, delete existing chunks before indexing
        :returns: Aggregated statistics
        """
        total_stats = {
            "documents_processed": 0,
            "total_chunks_created": 0,
            "total_chunks_indexed": 0,
            "total_embeddings_generated": 0,
            "total_errors": 0,
        }

        for document in documents:
            document_id = document.get("document_id")

            # Optionally delete existing chunks
            if replace_existing and document_id:
                self.opensearch_client.delete_document_chunks(document_id)

            # Index the document
            stats = await self.index_document(document)

            # Update totals
            total_stats["documents_processed"] += 1
            total_stats["total_chunks_created"] += stats["chunks_created"]
            total_stats["total_chunks_indexed"] += stats["chunks_indexed"]
            total_stats["total_embeddings_generated"] += stats["embeddings_generated"]
            total_stats["total_errors"] += stats["errors"]

        logger.info(
            f"Batch indexing complete: {total_stats['documents_processed']} documents, "
            f"{total_stats['total_chunks_indexed']} chunks indexed"
        )

        return total_stats

    async def reindex_document(self, document_id: str, document_data: Dict) -> Dict[str, int]:
        """Reindex a document by deleting old chunks and creating new ones.

        :param document_id: ID of the document
        :param document_data: Updated document data
        :returns: Indexing statistics
        """
        # Delete existing chunks
        deleted = self.opensearch_client.delete_document_chunks(document_id)
        if deleted:
            logger.info(f"Deleted existing chunks for document {document_id}")

        # Index with new data
        return await self.index_document(document_data)
