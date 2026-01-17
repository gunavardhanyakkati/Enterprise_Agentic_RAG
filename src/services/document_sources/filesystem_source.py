"""
Local filesystem document source implementation.
Scans directories for documents without network overhead.
"""

import asyncio
import logging
import mimetypes
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .base_source import BaseDocumentSource, DocumentMetadata

logger = logging.getLogger(__name__)


class FilesystemDocumentSource(BaseDocumentSource):
    """
    Document source for local or mounted filesystems.
    Best for testing and on-premise deployments.
    """
    
    def __init__(self, base_path: str, supported_extensions: List[str]):
        self.base_path = Path(base_path)
        self.supported_extensions = {ext.lower() for ext in supported_extensions}
        
        # Ensure base path exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Filesystem source initialized: {self.base_path}")
    
    async def scan(self, since: Optional[datetime] = None) -> List[DocumentMetadata]:
        """
        Scan filesystem directories recursively for documents.
        Skips hidden files and respects .gitignore patterns.
        """
        logger.info(f"Scanning filesystem path: {self.base_path}")
        
        documents = []
        
        try:
            # Walk directory tree asynchronously
            loop = asyncio.get_event_loop()
            files = await loop.run_in_executor(
                None,
                self._walk_filesystem,
                since
            )
            
            for file_path, stat in files:
                # Skip hidden files
                if any(part.startswith(".") for part in file_path.parts):
                    continue
                
                # Extract department from relative path (first directory)
                try:
                    relative_path = file_path.relative_to(self.base_path)
                    department = relative_path.parts[0] if relative_path.parts else "general"
                except ValueError:
                    department = "general"
                
                documents.append(
                    DocumentMetadata(
                        document_id=f"fs_{file_path.as_posix().replace('/', '_')}",
                        title=file_path.stem.replace("_", " ").replace("-", " ").title(),
                        file_path=str(file_path),
                        file_size=stat.st_size,
                        last_modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                        department=department,
                        document_type=self._infer_document_type(file_path.suffix),
                    )
                )
            
            logger.info(f"Found {len(documents)} documents in filesystem")
            return documents
            
        except Exception as e:
            logger.error(f"Filesystem scan error: {e}")
            raise
    
    def _walk_filesystem(self, since: Optional[datetime]) -> List[tuple[Path, os.stat_result]]:
        """
        Synchronous filesystem walk for executor.
        """
        files = []
        
        for root, dirs, filenames in os.walk(self.base_path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            
            for filename in filenames:
                file_path = Path(root) / filename
                
                # Check extension
                if file_path.suffix.lower() not in self.supported_extensions:
                    continue
                
                try:
                    stat = file_path.stat()
                    
                    # Apply time filter
                    if since:
                        file_mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                        if file_mtime <= since:
                            continue
                    
                    files.append((file_path, stat))
                    
                except OSError as e:
                    logger.warning(f"Could not stat file {file_path}: {e}")
                    continue
        
        return files
    
    async def download(self, document: DocumentMetadata) -> Optional[Path]:
        """
        For filesystem source, the file is already local.
        Just verify it exists and return the path.
        """
        file_path = Path(document.file_path)
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
        
        if not file_path.is_file():
            logger.error(f"Path is not a file: {file_path}")
            return None
        
        # Copy to temp directory to maintain consistent interface
        temp_dir = Path("/tmp/enterprise_docs")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        temp_path = temp_dir / file_path.name
        
        try:
            # Copy file to temp location (run in thread pool)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._copy_file,
                file_path,
                temp_path
            )
            
            logger.info(f"Prepared filesystem file: {file_path} -> {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Failed to copy file {file_path}: {e}")
            return None
    
    def _copy_file(self, src: Path, dst: Path) -> None:
        """
        Synchronous file copy for executor.
        """
        import shutil
        shutil.copy2(src, dst)
    
    def validate_source(self) -> bool:
        """
        Validate filesystem path exists and is readable.
        """
        try:
            if not self.base_path.exists():
                raise ValueError(f"Path does not exist: {self.base_path}")
            
            if not self.base_path.is_dir():
                raise ValueError(f"Path is not a directory: {self.base_path}")
            
            # Test read access
            test_file = self.base_path / ".access_test"
            try:
                test_file.touch()
                test_file.unlink()
            except PermissionError:
                raise PermissionError(f"Read/write access denied: {self.base_path}")
            
            logger.info(f"Filesystem source validation passed: {self.base_path}")
            return True
            
        except Exception as e:
            logger.error(f"Filesystem validation failed: {e}")
            return False
    
    def _infer_document_type(self, extension: str) -> str:
        """
        Map file extension to document type.
        """
        type_map = {
            ".pdf": "report",
            ".docx": "document",
            ".pptx": "presentation",
            ".xlsx": "spreadsheet",
            ".txt": "note",
            ".md": "documentation",
        }
        return type_map.get(extension.lower(), "unknown")

