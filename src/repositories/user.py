from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from src.models.user import User
from src.schemas.user import UserCreate, UserResponse

class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, user: UserCreate) -> User:
        db_user = User(**user.model_dump())
        self.session.add(db_user)
        self.session.commit()
        self.session.refresh(db_user)
        return db_user

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        return self.session.scalar(stmt)

    def get_by_username(self, username: str) -> Optional[User]:
        stmt = select(User).where(User.username == username)
        return self.session.scalar(stmt)

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        return self.session.scalar(stmt)

    def get_all(self, limit: int = 100, offset: int = 0) -> List[User]:
        stmt = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
        return list(self.session.scalars(stmt))

    def get_count(self) -> int:
        stmt = select(func.count(User.id))
        return self.session.scalar(stmt) or 0

    def update(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def upsert(self, user_create: UserCreate) -> User:
        existing_user = self.get_by_username(user_create.username)
        if existing_user:
            for key, value in user_create.model_dump(exclude_unset=True).items():
                setattr(existing_user, key, value)
            return self.update(existing_user)
        else:
            return self.create(user_create)

    def get_active_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        stmt = (
            select(User)
            .where(User.is_active == True)
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))

    def get_users_by_department(self, department: str, limit: int = 100, offset: int = 0) -> List[User]:
        stmt = (
            select(User)
            .where(User.department == department)
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))

    def get_users_by_role(self, role: str, limit: int = 100, offset: int = 0) -> List[User]:
        stmt = (
            select(User)
            .where(User.roles.contains([role]))
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))

    def get_users_by_access_level(self, access_level: str, limit: int = 100, offset: int = 0) -> List[User]:
        stmt = (
            select(User)
            .where(User.access_level == access_level)
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))
