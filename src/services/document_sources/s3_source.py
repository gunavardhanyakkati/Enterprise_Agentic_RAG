"""
AWS S3 document source implementation.
Scans S3 buckets for documents and provides download capability.
"""

import asyncio
import logging
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import boto3
import botocore.exceptions
from boto3.s3.transfer import S3Transfer


from .base_source import BaseDocumentSource, DocumentMetadata

logger = logging.getLogger(__name__)


class S3DocumentSource(BaseDocumentSource):
    """
    Document source for AWS S3 buckets.
    Supports scanning with prefix filtering and pagination for large buckets.
    """
    
    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        region: str = "us-east-1",
        aws_access_key_id: str = "",
        aws_secret_access_key: str = "",
    ):
        self.bucket = bucket
        self.prefix = prefix.rstrip("/") + "/" if prefix else ""
        self.region = region
        
        # Initialize boto3 client (sync - will wrap async calls)
        self.s3_client = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )
        
        # Supported file extensions (can be extended)
        self.supported_extensions = {".pdf", ".docx", ".pptx", ".xlsx", ".txt", ".md"}
        
        logger.info(f"S3 source initialized: s3://{bucket}/{prefix}")
    
    async def scan(self, since: Optional[datetime] = None) -> List[DocumentMetadata]:
        """
        Scan S3 bucket for documents modified since the given timestamp.
        Uses pagination to handle large buckets efficiently.
        """
        logger.info(f"Scanning S3 bucket: s3://{self.bucket}/{self.prefix}")
        
        documents = []
        paginator = self.s3_client.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(
            Bucket=self.bucket,
            Prefix=self.prefix,
        )
        
        try:
            for page in page_iterator:
                if "Contents" not in page:
                    continue
                
                for obj in page["Contents"]:
                    key = obj["Key"]
                    last_modified = obj["LastModified"]
                    
                    # Skip directories
                    if key.endswith("/"):
                        continue
                    
                    # Check file extension
                    file_path = Path(key)
                    if file_path.suffix.lower() not in self.supported_extensions:
                        continue
                    
                    # Apply time filter if specified
                    if since and last_modified <= since:
                        continue
                    
                    # Extract department from path structure
                    # Assumes: {department}/documents/{file}
                    path_parts = key.split("/")
                    department = path_parts[0] if len(path_parts) > 1 else "general"
                    
                    # Extract title from filename
                    title = file_path.stem.replace("_", " ").replace("-", " ").title()
                    
                    documents.append(
                        DocumentMetadata(
                            document_id=f"s3_{self.bucket}_{key.replace('/', '_')}",
                            title=title,
                            file_path=f"s3://{self.bucket}/{key}",
                            file_size=obj["Size"],
                            last_modified=last_modified,
                            department=department,
                            document_type=self._infer_document_type(file_path.suffix),
                        )
                    )
            
            logger.info(f"Found {len(documents)} documents in S3")
            return documents
            
        except botocore.exceptions.ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchBucket":
                logger.error(f"S3 bucket not found: {self.bucket}")
                raise ValueError(f"S3 bucket '{self.bucket}' does not exist")
            elif error_code == "AccessDenied":
                logger.error(f"Access denied to S3 bucket: {self.bucket}")
                raise PermissionError(f"Cannot access S3 bucket '{self.bucket}'")
            else:
                logger.error(f"S3 scan error: {e}")
                raise
    
    async def download(self, document: DocumentMetadata) -> Optional[Path]:
        """
        Download document from S3 to local temporary file.
        Returns Path to downloaded file or None if failed.
        """
        if not document.file_path.startswith("s3://"):
            logger.error(f"Invalid S3 path: {document.file_path}")
            return None
        
        # Parse S3 path
        s3_path = document.file_path.replace("s3://", "")
        bucket, key = s3_path.split("/", 1)
        
        # Create temp directory
        temp_dir = Path("/tmp/enterprise_docs")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        local_path = temp_dir / Path(key).name
        
        try:
            # Download file (run in thread pool to avoid blocking)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.s3_client.download_file,
                bucket,
                key,
                str(local_path)
            )
            
            logger.info(f"Downloaded S3 file: {key} -> {local_path}")
            return local_path
            
        except botocore.exceptions.ClientError as e:
            logger.error(f"S3 download error for {key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading {key}: {e}")
            return None
    
    def validate_source(self) -> bool:
        """
        Validate S3 bucket exists and is accessible.
        """
        try:
            # Check bucket exists and we have access
            self.s3_client.head_bucket(Bucket=self.bucket)
            
            # Try a test list operation
            self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=self.prefix,
                MaxKeys=1
            )
            
            logger.info(f"S3 source validation passed: s3://{self.bucket}")
            return True
            
        except botocore.exceptions.ClientError as e:
            error_code = e.response["Error"]["Code"]
            logger.error(f"S3 validation failed ({error_code}): {e}")
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
