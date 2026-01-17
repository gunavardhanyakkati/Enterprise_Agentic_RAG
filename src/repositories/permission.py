from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import Session
from src.models.permission import Permission
from src.schemas.permission import PermissionCreate, PermissionUpdate

class PermissionRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, permission: PermissionCreate) -> Permission:
        db_permission = Permission(**permission.model_dump())
        self.session.add(db_permission)
        self.session.commit()
        self.session.refresh(db_permission)
        return db_permission

    def get_by_id(self, permission_id: UUID) -> Optional[Permission]:
        stmt = select(Permission).where(Permission.id == permission_id)
        return self.session.scalar(stmt)

    def get_by_name(self, name: str) -> Optional[Permission]:
        stmt = select(Permission).where(Permission.name == name)
        return self.session.scalar(stmt)

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Permission]:
        stmt = select(Permission).order_by(Permission.created_at.desc()).limit(limit).offset(offset)
        return list(self.session.scalars(stmt))

    def get_active_permissions(self, limit: int = 100, offset: int = 0) -> List[Permission]:
        stmt = (
            select(Permission)
            .where(Permission.is_active == True)
            .order_by(Permission.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))

    def get_count(self) -> int:
        stmt = select(func.count(Permission.id))
        return self.session.scalar(stmt) or 0

    def update(self, permission_id: UUID, permission_update: PermissionUpdate) -> Optional[Permission]:
        permission = self.get_by_id(permission_id)
        if not permission:
            return None
        for key, value in permission_update.model_dump(exclude_unset=True).items():
            setattr(permission, key, value)
        self.session.commit()
        self.session.refresh(permission)
        return permission

    def delete(self, permission_id: UUID) -> bool:
        permission = self.get_by_id(permission_id)
        if not permission:
            return False
        self.session.delete(permission)
        self.session.commit()
        return True
