"""
Microsoft SharePoint document source implementation.
Supports SharePoint Online with OAuth authentication.
"""

import asyncio
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.client_credential import ClientCredential
from office365.sharepoint.files.file import File
from office365.sharepoint.files.versions.version import FileVersion

from .base_source import BaseDocumentSource, DocumentMetadata

logger = logging.getLogger(__name__)


class SharePointDocumentSource(BaseDocumentSource):
    """
    Document source for Microsoft SharePoint Online.
    Requires Azure App Registration with appropriate permissions.
    """
    
    def __init__(
        self,
        site: str,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        document_library: str = "Documents",
    ):
        self.site = site.rstrip("/")
        self.tenant_id = tenant_id
        self.document_library = document_library
        
        # Authenticate and create client context
        credentials = ClientCredential(client_id, client_secret)
        self.ctx = ClientContext(f"{self.site}").with_credentials(credentials)
        
        # Supported file extensions
        self.supported_extensions = {".pdf", ".docx", ".pptx", ".xlsx", ".txt", ".md"}
        
        logger.info(f"SharePoint source initialized: {self.site}")
    
    async def scan(self, since: Optional[datetime] = None) -> List[DocumentMetadata]:
        """
        Scan SharePoint document library for files.
        Uses CAML query for efficient filtering when possible.
        """
        logger.info(f"Scanning SharePoint library: {self.document_library}")
        
        documents = []
        
        try:
            # Get document library
            library = self.ctx.web.lists.get_by_title(self.document_library)
            
            # Build CAML query for date filtering if since is provided
            if since:
                since_str = since.isoformat()
                caml_query = f"""
                <View>
                    <Query>
                        <Where>
                            <Geq>
                                <FieldRef Name='Modified' />
                                <Value Type='DateTime'>{since_str}</Value>
                            </Geq>
                        </Where>
                        <OrderBy>
                            <FieldRef Name='Modified' Ascending='False' />
                        </OrderBy>
                    </Query>
                </View>
                """
                items = library.get_items(caml_query).execute_query()
            else:
                items = library.get_items().execute_query()
            
            # Process items in batches to avoid memory issues
            for item in items:
                # Skip folders
                if item.file_system_object_type == 1:  # Folder
                    continue
                
                file_path = Path(item.properties["FileRef"])
                
                # Check file extension
                if file_path.suffix.lower() not in self.supported_extensions:
                    continue
                
                # Extract metadata
                last_modified = item.properties.get(
                    "Modified",
                    datetime.now()
                )
                if isinstance(last_modified, str):
                    last_modified = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
                
                # Extract department from folder structure or metadata
                department = item.properties.get(
                    "Department",
                    "general"
                )
                
                documents.append(
                    DocumentMetadata(
                        document_id=f"sp_{self.tenant_id}_{item.properties['GUID']}",
                        title=item.properties.get(
                            "Title",
                            file_path.stem.replace("_", " ").title()
                        ),
                        file_path=file_path.as_posix(),
                        file_size=item.properties.get("File_x0020_Size", 0),
                        last_modified=last_modified,
                        department=department,
                        document_type=self._infer_document_type(file_path.suffix),
                    )
                )
            
            logger.info(f"Found {len(documents)} documents in SharePoint")
            return documents
            
        except Exception as e:
            logger.error(f"SharePoint scan error: {e}")
            raise
    
    async def download(self, document: DocumentMetadata) -> Optional[Path]:
        """
        Download document from SharePoint to local temporary file.
        """
        try:
            # Create temp directory
            temp_dir = Path("/tmp/enterprise_docs")
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            local_path = temp_dir / Path(document.file_path).name
            
            # Get file from SharePoint
            file = self.ctx.web.get_file_by_server_relative_path(document.file_path)
            
            # Download to temp file (run in thread pool)
            loop = asyncio.get_event_loop()
            def _download():
                with open(local_path, "wb") as f:
                    file.download(f).execute_query()
                return local_path
            
            await loop.run_in_executor(None, _download)
            
            logger.info(f"Downloaded SharePoint file: {document.file_path} -> {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"SharePoint download error for {document.file_path}: {e}")
            return None
    
    def validate_source(self) -> bool:
        """
        Validate SharePoint connection and permissions.
        """
        try:
            # Test connection by getting web info
            web = self.ctx.web.get().execute_query()
            
            # Verify we can access the document library
            library = self.ctx.web.lists.get_by_title(self.document_library).get().execute_query()
            
            logger.info(f"SharePoint validation passed: {web.properties['Url']}")
            return True
            
        except Exception as e:
            logger.error(f"SharePoint validation failed: {e}")
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
