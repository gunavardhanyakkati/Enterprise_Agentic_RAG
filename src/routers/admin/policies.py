from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.dependencies import get_db_session
from src.models.policy import Policy
from src.repositories.policy import PolicyRepository
from src.schemas.policy import PolicyCreate, PolicyResponse, PolicyUpdate

router = APIRouter(prefix="/admin/policies", tags=["admin", "policies"])

@router.post("/", response_model=PolicyResponse)
async def create_policy(policy: PolicyCreate, db: Session = Depends(get_db_session)) -> PolicyResponse:
    """Create a new policy."""
    policy_repo = PolicyRepository(db)
    db_policy = policy_repo.create(policy)
    return db_policy

@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(policy_id: int, db: Session = Depends(get_db_session)) -> PolicyResponse:
    """Get a policy by ID."""
    policy_repo = PolicyRepository(db)
    policy = policy_repo.get_by_id(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy

@router.get("/", response_model=list[PolicyResponse])
async def get_policies(limit: int = 100, offset: int = 0, db: Session = Depends(get_db_session)) -> list[PolicyResponse]:
    """Get a list of policies."""
    policy_repo = PolicyRepository(db)
    policies = policy_repo.get_all(limit, offset)
    return policies

@router.put("/{policy_id}", response_model=PolicyResponse)
async def update_policy(policy_id: int, policy_update: PolicyUpdate, db: Session = Depends(get_db_session)) -> PolicyResponse:
    """Update a policy."""
    policy_repo = PolicyRepository(db)
    policy = policy_repo.get_by_id(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    updated_policy = policy_repo.update(policy_update)
    return updated_policy

@router.delete("/{policy_id}", response_model=PolicyResponse)
async def delete_policy(policy_id: int, db: Session = Depends(get_db_session)) -> PolicyResponse:
    """Delete a policy."""
    policy_repo = PolicyRepository(db)
    policy = policy_repo.get_by_id(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    policy_repo.delete(policy_id)
    return policy
