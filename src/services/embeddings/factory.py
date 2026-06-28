from typing import Optional, Union

from src.config import Settings, get_settings

from .jina_client import JinaEmbeddingsClient
from .local_client import LocalEmbeddingsClient

EmbeddingsClient = Union[JinaEmbeddingsClient, LocalEmbeddingsClient]


def make_embeddings_service(settings: Optional[Settings] = None) -> EmbeddingsClient:
    """Create embeddings client based on configured provider."""
    if settings is None:
        settings = get_settings()

    if settings.embeddings.provider == "local":
        return LocalEmbeddingsClient(model_name=settings.embeddings.local_model)

    return JinaEmbeddingsClient(api_key=settings.jina_api_key)


def make_embeddings_client(settings: Optional[Settings] = None) -> EmbeddingsClient:
    return make_embeddings_service(settings)
