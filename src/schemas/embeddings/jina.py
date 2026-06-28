from typing import List, Literal, Union

from pydantic import BaseModel, Field


class JinaEmbeddingRequest(BaseModel):
    model: str = "jina-embeddings-v3"
    task: Literal["retrieval.passage", "retrieval.query"] = "retrieval.passage"
    dimensions: int = 1024
    input: List[str] = Field(default_factory=list)


class JinaEmbeddingDataItem(BaseModel):
    embedding: List[float]
    index: int = 0


class JinaEmbeddingResponse(BaseModel):
    model: str = ""
    data: List[dict] = Field(default_factory=list)
