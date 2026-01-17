from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import Session
from src.models.policy import Policy
from src.schemas.policy import PolicyCreate, PolicyUpdate

class PolicyRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, policy: PolicyCreate) -> Policy:
        db_policy = Policy(**policy.model_dump())
        self.session.add(db_policy)
        self.session.commit()
        self.session.refresh(db_policy)
        return db_policy

    def get_by_id(self, policy_id: UUID) -> Optional[Policy]:
        stmt = select(Policy).where(Policy.id == policy_id)
        return self.session.scalar(stmt)

    def get_by_name(self, name: str) -> Optional[Policy]:
        stmt = select(Policy).where(Policy.name == name)
        return self.session.scalar(stmt)

    def get_by_type(self, policy_type: str, limit: int = 100, offset: int = 0) -> List[Policy]:
        stmt = (
            select(Policy)
            .where(Policy.policy_type == policy_type)
            .order_by(Policy.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Policy]:
        stmt = select(Policy).order_by(Policy.created_at.desc()).limit(limit).offset(offset)
        return list(self.session.scalars(stmt))

    def get_count(self) -> int:
        stmt = select(func.count(Policy.id))
        return self.session.scalar(stmt) or 0

    def update(self, policy_id: UUID, policy_update: PolicyUpdate) -> Optional[Policy]:
        policy = self.get_by_id(policy_id)
        if not policy:
            return None
        for key, value in policy_update.model_dump(exclude_unset=True).items():
            setattr(policy, key, value)
        self.session.commit()
        self.session.refresh(policy)
        return policy

    def delete(self, policy_id: UUID) -> bool:
        policy = self.get_by_id(policy_id)
        if not policy:
            return False
        self.session.delete(policy)
        self.session.commit()
        return True
