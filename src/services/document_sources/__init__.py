# src/services/document_sources/__init__.py
"""
Enterprise document source implementations.
Provides pluggable connectors for S3, SharePoint, and filesystem sources.
"""

from .base_source import BaseDocumentSource, DocumentMetadata
from .s3_source import S3DocumentSource
from .sharepoint_source import SharePointDocumentSource
from .filesystem_source import FilesystemDocumentSource
from .factory import make_document_source

__all__ = [
    "BaseDocumentSource",
    "DocumentMetadata",
    "S3DocumentSource",
    "SharePointDocumentSource",
    "FilesystemDocumentSource",
    "make_document_source",
]
