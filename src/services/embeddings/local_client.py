import asyncio
import logging
from typing import List

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class LocalEmbeddingsClient:
    """Local sentence-transformers embeddings (all-MiniLM-L6-v2 by default)."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model: SentenceTransformer | None = None
        logger.info(f"Local embeddings client configured: {model_name}")

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    async def embed_passages(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        loop = asyncio.get_running_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            ).tolist(),
        )
        logger.info(f"Embedded {len(texts)} passages locally")
        return embeddings

    async def embed_query(self, query: str) -> List[float]:
        loop = asyncio.get_running_loop()
        embedding = await loop.run_in_executor(
            None,
            lambda: self.model.encode(query, show_progress_bar=False, convert_to_numpy=True).tolist(),
        )
        return embedding
