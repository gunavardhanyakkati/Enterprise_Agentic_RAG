import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from src.db.interfaces.postgresql import Base


class Document(Base):
    __tablename__ = "documents"

    # Primary identifier
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(String, unique=True, nullable=False, index=True)

    # Core metadata
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    document_type = Column(String, nullable=False)
    department = Column(String, nullable=False, index=True)

    # Security & ownership
    owner_id = Column(String, nullable=False, index=True)
    contributors = Column(JSON, nullable=False)
    access_level = Column(String, nullable=False, index=True)
    created_by = Column(String, nullable=False)
    last_modified_by = Column(String, nullable=False)

    # File info
    file_path = Column(String, nullable=False)
    file_hash = Column(String, nullable=False, unique=True)

    # Versioning
    version = Column(Integer, nullable=False, default=1)
    is_latest = Column(Boolean, nullable=False, default=True)
    parent_version_id = Column(String, nullable=True)
    expiry_date = Column(DateTime, nullable=True)

    # Parsed content
    raw_text = Column(Text, nullable=True)
    sections = Column(JSON, nullable=True)
    references = Column(JSON, nullable=True)

    # Processing metadata
    parser_used = Column(String, nullable=True)
    parser_metadata = Column(JSON, nullable=True)
    content_processed = Column(Boolean, default=False, nullable=False)
    content_processing_date = Column(DateTime, nullable=True)

    # Enterprise intelligence (STEP 2)
    summary = Column(Text, nullable=True)
    classification_confidence = Column(Float, nullable=True)
    extracted_metadata = Column(JSON, nullable=True)
    compliance_report = Column(JSON, nullable=True)
    agent_executions = Column(JSON, nullable=True)
    
    # Explainability & Caching (STEP 3)
    classification_reasoning = Column(JSON, nullable=True)
    compliance_reasoning = Column(JSON, nullable=True)
    agent_execution_metadata = Column(JSON, nullable=True)
    confidence_reasoning = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
