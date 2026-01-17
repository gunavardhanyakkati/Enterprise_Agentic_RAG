import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Text, Integer, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from src.db.interfaces.postgresql import Base

class Policy(Base):
    __tablename__ = "policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    policy_type = Column(String, nullable=False)  # retention, access, security, etc.
    config = Column(JSON, nullable=False, default={})  # Policy-specific configuration
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Policy {self.name} ({self.policy_type})>"
