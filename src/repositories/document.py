from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.document import Document
from src.schemas.document.document_create import DocumentCreate


class DocumentRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, document: DocumentCreate) -> Document:
        data = document.model_dump(exclude={"file_content"})
        db_document = Document(**data)
        self.session.add(db_document)
        self.session.commit()
        self.session.refresh(db_document)
        return db_document

    def get_by_document_id(self, document_id: str) -> Optional[Document]:
        stmt = select(Document).where(Document.document_id == document_id)
        return self.session.scalar(stmt)

    def get_by_id(self, document_id: UUID) -> Optional[Document]:
        stmt = select(Document).where(Document.id == document_id)
        return self.session.scalar(stmt)

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Document]:
        stmt = select(Document).order_by(Document.updated_at.desc()).limit(limit).offset(offset)
        return list(self.session.scalars(stmt))

    def get_count(self) -> int:
        stmt = select(func.count(Document.id))
        return self.session.scalar(stmt) or 0

    def get_by_department(self, department: str, limit: int = 100, offset: int = 0) -> List[Document]:
        """Get documents by department."""
        stmt = (
            select(Document)
            .where(Document.department == department)
            .order_by(Document.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))

    def get_by_access_level(self, access_level: str, limit: int = 100, offset: int = 0) -> List[Document]:
        """Get documents by access level."""
        stmt = (
            select(Document)
            .where(Document.access_level == access_level)
            .order_by(Document.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))

    def get_by_owner(self, owner_id: str, limit: int = 100, offset: int = 0) -> List[Document]:
        """Get documents owned by a user."""
        stmt = (
            select(Document)
            .where(Document.owner_id == owner_id)
            .order_by(Document.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))

    def get_expired_documents(self, limit: int = 100) -> List[Document]:
        """Get documents past their expiry date."""
        current_time = datetime.now()
        stmt = (
            select(Document)
            .where(Document.expiry_date < current_time)
            .order_by(Document.expiry_date)
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    def get_latest_version(self, document_id: str) -> Optional[Document]:
        """Get the latest version of a document."""
        stmt = (
            select(Document)
            .where(Document.document_id == document_id)
            .where(Document.is_latest == True)
            .order_by(Document.version.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def get_versions(self, document_id: str, limit: int = 10, offset: int = 0) -> List[Document]:
        """Get all versions of a document."""
        stmt = (
            select(Document)
            .where(Document.document_id == document_id)
            .order_by(Document.version.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))

    def get_processed_documents(self, limit: int = 100, offset: int = 0) -> List[Document]:
        """Get documents that have been successfully processed."""
        stmt = (
            select(Document)
            .where(Document.content_processed == True)
            .order_by(Document.content_processing_date.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))

    def get_unprocessed_documents(self, limit: int = 100, offset: int = 0) -> List[Document]:
        """Get documents that haven't been processed yet."""
        stmt = (
            select(Document)
            .where(Document.content_processed == False)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))

    def get_documents_with_raw_text(self, limit: int = 100, offset: int = 0) -> List[Document]:
        """Get documents that have raw text content stored."""
        stmt = (
            select(Document)
            .where(Document.raw_text != None)
            .order_by(Document.content_processing_date.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))

    def get_processing_stats(self) -> dict:
        """Get statistics about document processing status."""
        total_documents = self.get_count()

        processed_stmt = select(func.count(Document.id)).where(Document.content_processed == True)
        processed_documents = self.session.scalar(processed_stmt) or 0

        text_stmt = select(func.count(Document.id)).where(Document.raw_text != None)
        documents_with_text = self.session.scalar(text_stmt) or 0

        return {
            "total_documents": total_documents,
            "processed_documents": processed_documents,
            "documents_with_text": documents_with_text,
            "processing_rate": (processed_documents / total_documents * 100) if total_documents > 0 else 0,
            "text_extraction_rate": (documents_with_text / processed_documents * 100) if processed_documents > 0 else 0,
        }

    def update(self, document: Document) -> Document:
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document

    def upsert(self, document_create: DocumentCreate, versioning: bool = True) -> Document:
        """Upsert document with optional versioning."""
        existing_document = self.get_by_document_id(document_create.document_id)
        
        if existing_document:
            for key, value in document_create.model_dump(exclude_unset=True, exclude={"file_content"}).items():
                setattr(existing_document, key, value)
            return self.update(existing_document)
        else:
            # Create new document
            return self.create(document_create)

    def soft_delete(self, document_id: str) -> bool:
        """Soft delete a document (mark as deleted instead of removing)."""
        document = self.get_by_document_id(document_id)
        if document:
            document.is_latest = False
            self.session.commit()
            return True
        return False
