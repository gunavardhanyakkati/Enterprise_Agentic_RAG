import hashlib
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from src.config import Settings, get_settings
from src.models.document import Document
from src.repositories.document import DocumentRepository
from src.schemas.document.document_create import DocumentCreate
from src.services.indexing.factory import make_hybrid_indexing_service
from src.services.agents.enterprise.service import EnterpriseIntelligenceService
from src.services.gemini.factory import make_gemini_client
from src.services.opensearch.factory import make_opensearch_client
from src.services.parsers.document_parser import DocumentParserService

logger = logging.getLogger(__name__)


class UploadPipelineService:
    """Upload → parse → chunk → embed → OpenSearch index → PostgreSQL metadata."""

    def __init__(
        self,
        session: Session,
        settings: Optional[Settings] = None,
        parser: Optional[DocumentParserService] = None,
    ):
        self.session = session
        self.settings = settings or get_settings()
        self.parser = parser or DocumentParserService()
        self.repository = DocumentRepository(session)
        self.indexer = make_hybrid_indexing_service(self.settings)

    async def process_upload(
        self,
        file_path: Path,
        original_filename: str,
        title: str,
        description: str,
        department: str,
        access_level: str,
        document_type: str,
        owner_id: str,
        expiry_date: Optional[datetime] = None,
    ) -> Document:
        parsed = self.parser.parse(file_path, filename=original_filename)
        file_hash = self._hash_file(file_path)
        document_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        document_create = DocumentCreate(
            document_id=document_id,
            title=title,
            description=description,
            department=department,
            access_level=access_level,  # type: ignore[arg-type]
            document_type=document_type,
            owner_id=owner_id,
            contributors=[owner_id],
            file_path=str(file_path),
            file_hash=file_hash,
            created_by=owner_id,
            last_modified_by=owner_id,
            expiry_date=expiry_date,
            raw_text=parsed.content,
            sections=[{"title": f"Page {i + 1}", "content": text} for i, text in enumerate(parsed.page_texts or [])]
            if parsed.page_texts
            else None,
            parser_used=parsed.parser_used.value,
            parser_metadata={
                "filename": parsed.filename,
                "pages": parsed.pages,
                "file_size_bytes": parsed.file_size_bytes,
                **parsed.metadata,
            },
            content_processed=False,
        )

        document = self.repository.create(document_create)

        index_stats = await self.indexer.index_document(self._document_payload(document))
        document.content_processed = index_stats["chunks_indexed"] > 0
        document.content_processing_date = now
        document.parser_metadata = {
            **(document.parser_metadata or {}),
            "indexing": index_stats,
            "embedding_model": self.settings.embeddings.local_model
            if self.settings.embeddings.provider == "local"
            else "jina-embeddings-v3",
        }
        document = self.repository.update(document)

        if self.settings.gemini.enabled and self.settings.gemini.auto_run_on_upload:
            gemini = make_gemini_client()
            if gemini.is_available:
                try:
                    intelligence = EnterpriseIntelligenceService(
                        session=self.session,
                        gemini=gemini,
                        opensearch=make_opensearch_client(self.settings),
                        settings=self.settings,
                    )
                    await intelligence.run_pipeline(document)
                    document = self.repository.get_by_document_id(document.document_id) or document
                except Exception as exc:
                    logger.warning(f"Intelligence pipeline skipped after upload: {exc}")

        return document

    @staticmethod
    def _hash_file(file_path: Path) -> str:
        digest = hashlib.sha256()
        with open(file_path, "rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _document_payload(document: Document) -> dict[str, Any]:
        return {
            "id": str(document.id),
            "document_id": document.document_id,
            "title": document.title,
            "description": document.description,
            "department": document.department,
            "access_level": document.access_level,
            "document_type": document.document_type,
            "owner_id": document.owner_id,
            "contributors": document.contributors or [],
            "version": document.version,
            "is_latest": document.is_latest,
            "file_path": document.file_path,
            "raw_text": document.raw_text or "",
        }
