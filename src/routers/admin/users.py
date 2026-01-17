from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.dependencies import get_db_session
from src.models.user import User
from src.repositories.user import UserRepository
from src.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/admin/users", tags=["admin", "users"])

@router.post("/", response_model=UserResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db_session)) -> UserResponse:
    """Create a new user."""
    user_repo = UserRepository(db)
    existing_user = user_repo.get_by_username(user.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    db_user = user_repo.create(user)
    return db_user

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: Session = Depends(get_db_session)) -> UserResponse:
    """Get a user by ID."""
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/", response_model=list[UserResponse])
async def get_users(limit: int = 100, offset: int = 0, db: Session = Depends(get_db_session)) -> list[UserResponse]:
    """Get a list of users."""
    user_repo = UserRepository(db)
    users = user_repo.get_all(limit, offset)
    return users

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, user_update: UserUpdate, db: Session = Depends(get_db_session)) -> UserResponse:
    """Update a user."""
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    updated_user = user_repo.update(user_update)
    return updated_user

@router.delete("/{user_id}", response_model=UserResponse)
async def delete_user(user_id: str, db: Session = Depends(get_db_session)) -> UserResponse:
    """Delete a user."""
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user_repo.delete(user_id)
    return user
