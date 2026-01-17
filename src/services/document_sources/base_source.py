"""
Abstract base classes for enterprise document sources.
Replaces arXiv-specific source with pluggable enterprise sources (S3, SharePoint, filesystem).
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel


class DocumentMetadata(BaseModel):
    """
    Metadata for a document found in an enterprise source.
    Replaces ArxivPaper with enterprise-specific fields.
    """
    document_id: str
    title: str
    file_path: str
    file_size: int
    last_modified: datetime
    department: Optional[str] = None
    document_type: Optional[str] = None


class BaseDocumentSource(ABC):
    """
    Abstract base class for all enterprise document sources.
    
    Implementations must provide:
    - S3DocumentSource: for AWS S3 buckets
    - SharePointSource: for Microsoft SharePoint
    - FilesystemSource: for local/network file systems
    """
    
    @abstractmethod
    async def scan(self, since: Optional[datetime] = None) -> List[DocumentMetadata]:
        """
        Scan the source for documents modified since the given timestamp.
        
        :param since: Optional datetime to filter for recently modified documents.
                      If None, returns all documents.
        :returns: List of document metadata objects ready for ingestion.
        """
        pass
    
    @abstractmethod
    async def download(self, document: DocumentMetadata) -> Optional[Path]:
        """
        Download a document to a local temporary file.
        
        :param document: DocumentMetadata object from scan() results.
        :returns: Path to downloaded file, or None if download failed.
                 Caller is responsible for cleanup.
        """
        pass
    
    @abstractmethod
    def validate_source(self) -> bool:
        """
        Validate that the source is configured correctly and is accessible.
        Called during service initialization.
        
        :returns: True if source configuration is valid and accessible.
        :raises: ConfigurationError if source is misconfigured.
        """
        pass

