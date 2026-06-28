"""
Enterprise document source implementations.
Provides pluggable connectors for S3, SharePoint, and filesystem sources.
"""

from .base_source import BaseDocumentSource, DocumentMetadata
from .factory import make_document_source
from .filesystem_source import FilesystemDocumentSource

__all__ = [
    "BaseDocumentSource",
    "DocumentMetadata",
    "FilesystemDocumentSource",
    "make_document_source",
]
