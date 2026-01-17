"""
Document validation service for enterprise ingestion.
Validates file types, sizes, and integrity before processing.
"""

import hashlib
import logging
import mimetypes
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class DocumentValidator:
    """
    Validates documents before ingestion.
    Checks file size, MIME type, and calculates hash for deduplication.
    """
    
    def __init__(self, supported_mime_types: list, max_file_size_mb: int):
        """
        Initialize validator with configuration.
        
        :param supported_mime_types: List of allowed MIME types
        :param max_file_size_mb: Maximum file size in megabytes
        """
        self.supported_mime_types = set(supported_mime_types)
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        
        logger.info(
            f"Document validator initialized: {len(self.supported_mime_types)} MIME types, "
            f"max size {max_file_size_mb}MB"
        )
    
    def validate_file(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate a file for ingestion.
        
        :param file_path: Path to the file to validate
        :returns: Tuple of (is_valid, error_message)
        """
        try:
            # Check file exists and is readable
            if not file_path.exists():
                return False, f"File does not exist: {file_path}"
            
            if not file_path.is_file():
                return False, f"Path is not a file: {file_path}"
            
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size_bytes:
                return False, (
                    f"File size {file_size / 1024 / 1024:.1f}MB exceeds "
                    f"limit of {self.max_file_size_bytes / 1024 / 1024:.1f}MB"
                )
            
            if file_size == 0:
                return False, "File is empty"
            
            # Check MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type not in self.supported_mime_types:
                return False, f"Unsupported MIME type: {mime_type}"
            
            logger.debug(f"File validation passed: {file_path} ({mime_type}, {file_size} bytes)")
            return True, None
            
        except OSError as e:
            logger.error(f"OS error validating file {file_path}: {e}")
            return False, f"File access error: {e}"
        except Exception as e:
            logger.error(f"Unexpected error validating file {file_path}: {e}")
            return False, f"Validation failed: {e}"
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA256 hash of a file for deduplication.
        
        :param file_path: Path to the file
        :returns: Hexadecimal hash string
        """
        hasher = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            
            file_hash = hasher.hexdigest()
            logger.debug(f"Calculated hash for {file_path}: {file_hash[:16]}...")
            return file_hash
            
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            raise
    
    def extract_basic_metadata(self, file_path: Path) -> dict:
        """
        Extract basic metadata from file system.
        
        :param file_path: Path to the file
        :returns: Dictionary with metadata
        """
        stat = file_path.stat()
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        return {
            "file_size": stat.st_size,
            "mime_type": mime_type,
            "created_at": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "hash": self.calculate_file_hash(file_path),
        }
