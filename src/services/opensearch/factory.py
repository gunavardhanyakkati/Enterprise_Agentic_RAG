from functools import lru_cache
from typing import Optional

from src.config import Settings, get_settings

from .client import OpenSearchClient


@lru_cache(maxsize=1)
def make_opensearch_client(settings: Optional[Settings] = None) -> OpenSearchClient:
    if settings is None:
        settings = get_settings()
    return OpenSearchClient(settings.opensearch)


def make_opensearch_client_fresh(
    settings: Optional[Settings] = None, host: Optional[str] = None
) -> OpenSearchClient:
    if settings is None:
        settings = get_settings()
    if host:
        opensearch_settings = settings.opensearch.model_copy(update={"host": host})
        return OpenSearchClient(opensearch_settings)
    return OpenSearchClient(settings.opensearch)
