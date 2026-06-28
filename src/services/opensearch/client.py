import logging
import uuid
from typing import Any, Dict, List, Optional

from opensearchpy import OpenSearch, helpers
from opensearchpy.exceptions import NotFoundError

from src.config import OpenSearchSettings

logger = logging.getLogger(__name__)


class OpenSearchClient:
    """OpenSearch client for hybrid document chunk indexing and search."""

    def __init__(self, settings: OpenSearchSettings):
        self.settings = settings
        self.index_name = settings.index_name
        host = settings.host.replace("http://", "").replace("https://", "")
        use_ssl = settings.host.startswith("https://")

        self.client = OpenSearch(
            hosts=[{"host": host.split(":")[0], "port": int(host.split(":")[1]) if ":" in host else 9200}],
            http_compress=True,
            use_ssl=use_ssl,
            verify_certs=False,
            ssl_show_warn=False,
        )
        logger.info(f"OpenSearch client initialized for index '{self.index_name}'")

    def health_check(self) -> bool:
        try:
            health = self.client.cluster.health()
            return health.get("status") in ("green", "yellow", "red")
        except Exception as e:
            logger.warning(f"OpenSearch health check failed: {e}")
            return False

    def setup_indices(self, force: bool = False) -> Dict[str, bool]:
        results: Dict[str, bool] = {}
        try:
            if force and self.client.indices.exists(index=self.index_name):
                self.client.indices.delete(index=self.index_name)

            if not self.client.indices.exists(index=self.index_name):
                body = {
                    "settings": {"index": {"knn": True, "number_of_shards": 1, "number_of_replicas": 0}},
                    "mappings": {
                        "properties": {
                            "chunk_id": {"type": "keyword"},
                            "document_id": {"type": "keyword"},
                            "paper_id": {"type": "keyword"},
                            "chunk_index": {"type": "integer"},
                            "chunk_text": {"type": "text"},
                            "chunk_word_count": {"type": "integer"},
                            "start_char": {"type": "integer"},
                            "end_char": {"type": "integer"},
                            "section_title": {"type": "text"},
                            "section_name": {"type": "keyword"},
                            "title": {"type": "text"},
                            "description": {"type": "text"},
                            "department": {"type": "keyword"},
                            "access_level": {"type": "keyword"},
                            "document_type": {"type": "keyword"},
                            "owner_id": {"type": "keyword"},
                            "contributors": {"type": "keyword"},
                            "version": {"type": "integer"},
                            "is_latest": {"type": "boolean"},
                            "embedding_model": {"type": "keyword"},
                            "created_at": {"type": "date"},
                            "embedding": {
                                "type": "knn_vector",
                                "dimension": self.settings.vector_dimension,
                                "method": {
                                    "name": "hnsw",
                                    "space_type": self.settings.vector_space_type,
                                    "engine": "nmslib",
                                },
                            },
                        }
                    },
                }
                self.client.indices.create(index=self.index_name, body=body)
                logger.info(f"Created OpenSearch index: {self.index_name}")
                results["hybrid_index"] = True
            else:
                results["hybrid_index"] = False
        except Exception as e:
            logger.error(f"Failed to setup OpenSearch indices: {e}")
            results["hybrid_index"] = False
        return results

    def get_index_stats(self) -> Dict[str, Any]:
        try:
            count = self.client.count(index=self.index_name)
            return {"index_name": self.index_name, "document_count": count.get("count", 0)}
        except Exception as e:
            logger.warning(f"Failed to get index stats: {e}")
            return {"index_name": self.index_name, "document_count": 0}

    def bulk_index_chunks(self, chunks_with_embeddings: List[Dict[str, Any]]) -> Dict[str, int]:
        actions = []
        for item in chunks_with_embeddings:
            chunk_data = item["chunk_data"]
            embedding = item["embedding"]
            doc_id = chunk_data.get("chunk_id") or f"{chunk_data['document_id']}_{chunk_data['chunk_index']}"
            doc = {**chunk_data, "chunk_id": doc_id, "embedding": embedding}
            actions.append({"_index": self.index_name, "_id": doc_id, "_source": doc})

        if not actions:
            return {"success": 0, "failed": 0}

        success, failed = helpers.bulk(self.client, actions, raise_on_error=False, stats_only=True)
        return {"success": success, "failed": failed}

    def delete_document_chunks(self, document_id: str) -> int:
        try:
            response = self.client.delete_by_query(
                index=self.index_name,
                body={"query": {"term": {"document_id": document_id}}},
                refresh=True,
            )
            return int(response.get("deleted", 0))
        except Exception as e:
            logger.error(f"Failed to delete chunks for {document_id}: {e}")
            return 0

    def update_document_access(self, document_id: str, access_level: str) -> int:
        try:
            response = self.client.update_by_query(
                index=self.index_name,
                body={
                    "script": {
                        "source": "ctx._source.access_level = params.access_level",
                        "lang": "painless",
                        "params": {"access_level": access_level},
                    },
                    "query": {"term": {"document_id": document_id}},
                },
                refresh=True,
            )
            return int(response.get("updated", 0))
        except Exception as e:
            logger.error(f"Failed to update access for {document_id}: {e}")
            return 0

    def search_unified(
        self,
        query: str,
        query_embedding: Optional[List[float]] = None,
        size: int = 10,
        from_: int = 0,
        categories: Optional[List[str]] = None,
        latest: bool = True,
        use_hybrid: bool = True,
        min_score: float = 0.0,
        additional_filters: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        filters: List[Dict[str, Any]] = list(additional_filters or [])
        if categories:
            filters.append({"terms": {"department": categories}})
        if latest:
            filters.append({"term": {"is_latest": True}})

        if use_hybrid and query_embedding:
            search_body: Dict[str, Any] = {
                "size": size,
                "from": from_,
                "query": {
                    "bool": {
                        "should": [
                            {"match": {"chunk_text": {"query": query, "boost": 1.0}}},
                            {
                                "knn": {
                                    "embedding": {
                                        "vector": query_embedding,
                                        "k": max(size * 2, 10),
                                    }
                                }
                            },
                        ],
                        "minimum_should_match": 1,
                    }
                },
            }
        else:
            search_body = {
                "size": size,
                "from": from_,
                "query": {"bool": {"must": [{"match": {"chunk_text": query}}]}},
            }

        if filters:
            search_body["query"]["bool"]["filter"] = filters

        if min_score > 0:
            search_body["min_score"] = min_score

        try:
            response = self.client.search(index=self.index_name, body=search_body)
        except Exception as e:
            logger.error(f"OpenSearch search failed: {e}")
            return {"hits": [], "total": 0}

        hits = []
        for hit in response.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            hits.append(
                {
                    "document_id": source.get("document_id", ""),
                    "external_id": source.get("document_id", ""),
                    "chunk_id": source.get("chunk_id", hit.get("_id", "")),
                    "chunk_text": source.get("chunk_text", ""),
                    "title": source.get("title", ""),
                    "description": source.get("description", ""),
                    "contributors": source.get("contributors", []),
                    "department": source.get("department", ""),
                    "access_level": source.get("access_level", "internal"),
                    "document_type": source.get("document_type", ""),
                    "section_name": source.get("section_title", source.get("section_name", "")),
                    "file_path": source.get("file_path", ""),
                    "source_url": source.get("file_path", ""),
                    "source_type": source.get("document_type", ""),
                    "created_at": source.get("created_at"),
                    "score": hit.get("_score", 0.0),
                    "highlights": None,
                }
            )

        total = response.get("hits", {}).get("total", {})
        total_count = total.get("value", len(hits)) if isinstance(total, dict) else len(hits)
        return {"hits": hits, "total": total_count}
