from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from src.models.audit_log import AuditLog
from src.schemas.audit_log import AuditLogCreate

class AuditLogRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, audit_log: AuditLogCreate) -> AuditLog:
        db_log = AuditLog(**audit_log.model_dump())
        self.session.add(db_log)
        self.session.commit()
        self.session.refresh(db_log)
        return db_log

    def get_by_id(self, log_id: UUID) -> Optional[AuditLog]:
        stmt = select(AuditLog).where(AuditLog.id == log_id)
        return self.session.scalar(stmt)

    def get_by_user_id(self, user_id: UUID, limit: int = 100, offset: int = 0) -> List[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))

    def get_by_document_id(self, document_id: UUID, limit: int = 100, offset: int = 0) -> List[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.document_id == document_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))

    def get_by_action(self, action: str, limit: int = 100, offset: int = 0) -> List[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.action == action)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))

    def get_all(self, limit: int = 100, offset: int = 0) -> List[AuditLog]:
        stmt = (
            select(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))

    def get_count(self) -> int:
        stmt = select(func.count(AuditLog.id))
        return self.session.scalar(stmt) or 0

    def get_logs_by_date_range(self, start_date: datetime, end_date: datetime, limit: int = 100, offset: int = 0) -> List[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.created_at >= start_date)
            .where(AuditLog.created_at <= end_date)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))
