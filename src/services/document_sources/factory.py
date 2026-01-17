import logging
from functools import lru_cache

from src.config import get_settings
from src.services.document_sources.base_source import BaseDocumentSource

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def make_document_source() -> BaseDocumentSource:
    """Factory function to create a cached document source instance based on configuration.
    
    :returns: An instance of the configured document source
    :rtype: BaseDocumentSource
    :raises ValueError: If the configured source type is not supported
    :raises NotImplementedError: If the source type is not yet implemented
    """
    settings = get_settings()
    source_type = settings.enterprise_source.source_type
    
    if source_type == "filesystem":
        from src.services.document_sources.filesystem_source import FilesystemSource
        source = FilesystemSource(settings)
        source.connect()
        logger.info(f"Created filesystem document source at: {settings.enterprise_source.filesystem_path}")
        return source
    elif source_type == "s3":
        # TODO: Implement S3Source
        raise NotImplementedError("S3 document source not yet implemented")
    elif source_type == "sharepoint":
        # TODO: Implement SharePointSource
        raise NotImplementedError(
            "SharePoint document source not yet implemented. "
            "Requires msgraph-sdk and Azure AD configuration."
        )
    else:
        raise ValueError(f"Unsupported document source type: {source_type}. "
                        f"Supported types: filesystem, s3, sharepoint")
