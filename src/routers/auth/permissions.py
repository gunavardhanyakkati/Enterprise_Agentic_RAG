from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.dependencies import get_db_session
from src.models.permission import Permission
from src.repositories.permission import PermissionRepository
from src.schemas.permission import PermissionCreate, PermissionResponse, PermissionUpdate

router = APIRouter(prefix="/auth/permissions", tags=["auth", "permissions"])

@router.post("/", response_model=PermissionResponse)
async def create_permission(permission: PermissionCreate, db: Session = Depends(get_db_session)) -> PermissionResponse:
    """Create a new permission."""
    permission_repo = PermissionRepository(db)
    db_permission = permission_repo.create(permission)
    return db_permission

@router.get("/{permission_id}", response_model=PermissionResponse)
async def get_permission(permission_id: int, db: Session = Depends(get_db_session)) -> PermissionResponse:
    """Get a permission by ID."""
    permission_repo = PermissionRepository(db)
    permission = permission_repo.get_by_id(permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    return permission

@router.get("/", response_model=list[PermissionResponse])
async def get_permissions(limit: int = 100, offset: int = 0, db: Session = Depends(get_db_session)) -> list[PermissionResponse]:
    """Get a list of permissions."""
    permission_repo = PermissionRepository(db)
    permissions = permission_repo.get_all(limit, offset)
    return permissions

@router.put("/{permission_id}", response_model=PermissionResponse)
async def update_permission(permission_id: int, permission_update: PermissionUpdate, db: Session = Depends(get_db_session)) -> PermissionResponse:
    """Update a permission."""
    permission_repo = PermissionRepository(db)
    permission = permission_repo.get_by_id(permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    updated_permission = permission_repo.update(permission_update)
    return updated_permission

@router.delete("/{permission_id}", response_model=PermissionResponse)
async def delete_permission(permission_id: int, db: Session = Depends(get_db_session)) -> PermissionResponse:
    """Delete a permission."""
    permission_repo = PermissionRepository(db)
    permission = permission_repo.get_by_id(permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    permission_repo.delete(permission_id)
    return permission
