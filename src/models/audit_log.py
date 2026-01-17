import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from src.db.interfaces.postgresql import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    action = Column(String, nullable=False, index=True)  # e.g., "VIEW", "DOWNLOAD", "SEARCH", "UPLOAD", "DELETE"
    document_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Nullable for actions not related to specific documents
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    query_params = Column(JSON, nullable=True)  # For searches: {query, filters}
    response_status = Column(String, nullable=True)  # success, denied, error

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<AuditLog {self.id}>"
