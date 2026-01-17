import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse

from src.dependencies import (
    AccessControlDep,
    AuditLoggerDep,
    SessionDep,
    UserDep,
    VersionControlDep,
)
from src.models.document import Document
from src.repositories.document import DocumentRepository
from src.schemas.document.document import DocumentResponse, DocumentVersion
from src.schemas.document.document_create import DocumentCreate
from src.schemas.common.security import User
from src.services.document_ingestion.ingestion_service import IngestionService
from src.services.security.access_control_service import AccessControlService
from src.services.security.audit_logger import AuditLogger
from src.services.document_lifecycle.version_control_service import VersionControlService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["document-management"])


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(..., description="Document file to upload"),
    title: str = Form(..., description="Document title"),
    description: str = Form(..., description="Document description"),
    department: str = Form(..., description="Owning department"),
    access_level: str = Form(..., description="Access level classification"),
    document_type: str = Form(..., description="Document type"),
    expiry_date: Optional[str] = Form(None, description="Optional expiration date (ISO format)"),
    user: User = UserDep,
    audit_logger: AuditLogger = AuditLoggerDep,
):
    """Upload and ingest a new document.
    
    Args:
        file: The uploaded document file
        title: Document title
        description: Document description
        department: Owning department
        access_level: Access classification level
        document_type: Type of document
        expiry_date: Optional expiration date
        user: Authenticated user
        audit_logger: Audit logger
        
    Returns:
        Created document response
        
    Raises:
        HTTPException: If upload or processing fails
    """
    try:
        logger.info(f"Document upload initiated by user: {user.username}")
        
        # Validate access level
        if not audit_logger.settings.security.rbac_enabled:
            # RBAC disabled - allow any access level
            pass
        elif access_level not in user.access_levels:
            logger.warning(
                f"User {user.username} attempted to upload document with access level "
                f"{access_level}, but only has: {user.access_levels}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot create document with access level '{access_level}'. "
                f"Your allowed levels: {', '.join(user.access_levels)}",
            )

        # Save uploaded file to temporary location
        upload_dir = Path("./data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / f"{uuid.uuid4()}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.debug(f"Saved uploaded file to: {file_path}")

        # Process and ingest the document
        from src.database import get_db_session
        
        with get_db_session() as session:
            repository = DocumentRepository(session)
            ingestion_service = IngestionService(
                settings=user.settings,
                document_repository=repository,
                version_control_service=VersionControlService(repository=repository),
                audit_logger=audit_logger,
            )
            
            document_id = await ingestion_service.ingest_single_document(
                file_path=file_path,
                user_id=user.id,
                document_metadata={
                    "title": title,
                    "description": description,
                    "department": department,
                    "access_level": access_level,
                    "document_type": document_type,
                    "expiry_date": expiry_date,
                },
            )
            
            # Fetch the created document
            document = repository.get_by_document_id(document_id)
            if not document:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Document created but could not be retrieved",
                )
            
            # Log successful upload
            audit_logger.log_document_modification(
                user=user,
                document_id=document_id,
                action="upload",
                changes={
                    "title": title,
                    "department": department,
                    "access_level": access_level,
                    "file_size": file_path.stat().st_size,
                },
            )
            
            logger.info(f"Document uploaded successfully: {document_id}")
            return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}",
        )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    user: User = UserDep,
    session: SessionDep,
    access_control: AccessControlService = AccessControlDep,
    audit_logger: AuditLogger = AuditLoggerDep,
):
    """Get a specific document by ID.
    
    Args:
        document_id: The document ID
        user: Authenticated user
        session: Database session
        access_control: Access control service
        audit_logger: Audit logger
        
    Returns:
        Document response
        
    Raises:
        HTTPException: If document not found or access denied
    """
    try:
        logger.debug(f"Fetching document: {document_id}")
        
        repository = DocumentRepository(session)
        document = repository.get_by_document_id(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document not found: {document_id}",
            )
        
        # Check access permissions
        if not access_control.can_access_document(user, document):
            audit_logger.log_security_event(
                user=user,
                event="access_denied",
                reason=f"User attempted to access document {document_id} without permission",
                severity="medium",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this document",
            )
        
        # Log access
        audit_logger.log_document_access(user, document_id, "read")
        
        return document
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching document {document_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch document",
        )


@router.get("/", response_model=List[DocumentResponse])
def list_documents(
    department: Optional[str] = Query(None, description="Filter by department"),
    access_level: Optional[str] = Query(None, description="Filter by access level"),
    document_type: Optional[str] = Query(None, description="Filter by document type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of documents"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    user: User = UserDep,
    session: SessionDep,
    access_control: AccessControlService = AccessControlDep,
):
    """List documents with optional filtering.
    
    Args:
        department: Optional department filter
        access_level: Optional access level filter
        document_type: Optional document type filter
        limit: Maximum number of documents
        offset: Pagination offset
        user: Authenticated user
        session: Database session
        access_control: Access control service
        
    Returns:
        List of document responses (filtered by user permissions)
    """
    try:
        logger.debug(f"Listing documents for user: {user.username}")
        
        repository = DocumentRepository(session)
        
        # Get user-accessible access levels
        user_access_levels = access_control.get_user_access_levels(user)
        
        # Query documents with filters
        documents = repository.get_all(limit=limit, offset=offset)
        
        # Filter by access level if specified and allowed
        if access_level and access_level in user_access_levels:
            documents = [doc for doc in documents if doc.access_level == access_level]
        elif access_level:
            # User doesn't have permission for requested level
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have access to documents with level '{access_level}'",
            )
        
        # Apply additional filters
        if department:
            documents = [doc for doc in documents if doc.department == department]
        
        if document_type:
            documents = [doc for doc in documents if doc.document_type == document_type]
        
        # Filter by user access permissions
        accessible_docs = access_control.filter_by_access(user, documents)
        
        logger.info(
            f"Found {len(accessible_docs)} accessible documents for user {user.username} "
            f"(out of {len(documents)} total)"
        )
        
        return accessible_docs
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list documents",
        )


@router.put("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: str,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    access_level: Optional[str] = Form(None),
    user: User = UserDep,
    session: SessionDep,
    access_control: AccessControlService = AccessControlDep,
    audit_logger: AuditLogger = AuditLoggerDep,
):
    """Update an existing document.
    
    Args:
        document_id: The document ID
        title: Optional new title
        description: Optional new description
        access_level: Optional new access level
        user: Authenticated user
        session: Database session
        access_control: Access control service
        audit_logger: Audit logger
        
    Returns:
        Updated document response
        
    Raises:
        HTTPException: If document not found or access denied
    """
    try:
        logger.info(f"Update requested for document: {document_id} by user: {user.username}")
        
        repository = DocumentRepository(session)
        document = repository.get_by_document_id(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document not found: {document_id}",
            )
        
        # Check if user can modify (must be owner or admin)
        if document.owner_id != user.id and not any(role in ["admin", "superuser"] for role in user.roles):
            audit_logger.log_security_event(
                user=user,
                event="unauthorized_modification_attempt",
                reason=f"User {user.id} attempted to modify document {document_id} without permission",
                severity="medium",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the document owner or administrators can modify this document",
            )
        
        # Check access level permission
        if access_level and access_level not in access_control.get_user_access_levels(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You cannot set access level to '{access_level}'",
            )
        
        # Track changes for audit log
        changes = {}
        
        # Update fields
        if title is not None:
            document.title = title
            changes["title"] = title
        
        if description is not None:
            document.description = description
            changes["description"] = description
        
        if access_level is not None:
            document.access_level = access_level
            changes["access_level"] = access_level
        
        # Update timestamps
        document.updated_at = datetime.utcnow()
        document.last_modified_by = user.id
        
        # Save changes
        updated = repository.update(document)
        
        # Log modification
        audit_logger.log_document_modification(
            user=user,
            document_id=document_id,
            action="update",
            changes=changes,
        )
        
        logger.info(f"Document updated: {document_id}")
        
        return updated
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating document {document_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update document",
        )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    user: User = UserDep,
    session: SessionDep,
    access_control: AccessControlService = AccessControlDep,
    audit_logger: AuditLogger = AuditLoggerDep,
):
    """Delete (soft delete) a document.
    
    Args:
        document_id: The document ID
        user: Authenticated user
        session: Database session
        access_control: Access control service
        audit_logger: Audit logger
        
    Raises:
        HTTPException: If document not found or access denied
    """
    try:
        logger.info(f"Delete requested for document: {document_id} by user: {user.username}")
        
        repository = DocumentRepository(session)
        document = repository.get_by_document_id(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document not found: {document_id}",
            )
        
        # Check if user can delete (must be owner or admin)
        if document.owner_id != user.id and not any(role in ["admin", "superuser"] for role in user.roles):
            audit_logger.log_security_event(
                user=user,
                event="unauthorized_deletion_attempt",
                reason=f"User {user.id} attempted to delete document {document_id} without permission",
                severity="high",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the document owner or administrators can delete this document",
            )
        
        # Perform soft delete
        repository.soft_delete(document_id)
        
        # Log deletion (soft delete)
        audit_logger.log_document_modification(
            user=user,
            document_id=document_id,
            action="delete",
            changes={"deleted": True, "soft_delete": True},
        )
        
        logger.info(f"Document soft deleted: {document_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document",
        )


@router.get("/{document_id}/versions", response_model=List[DocumentVersion])
def get_document_versions(
    document_id: str,
    limit: int = Query(10, ge=1, le=100, description="Maximum versions to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    user: User = UserDep,
    session: SessionDep,
    access_control: AccessControlService = AccessControlDep,
    version_control: VersionControlService = VersionControlDep,
):
    """Get version history for a document.
    
    Args:
        document_id: The document ID
        limit: Maximum number of versions
        offset: Pagination offset
        user: Authenticated user
        session: Database session
        access_control: Access control service
        version_control: Version control service
        
    Returns:
        List of document versions
        
    Raises:
        HTTPException: If document not found or access denied
    """
    try:
        logger.debug(f"Fetching versions for document: {document_id}")
        
        repository = DocumentRepository(session)
        document = repository.get_by_document_id(document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document not found: {document_id}",
            )
        
        # Check access to the document
        if not access_control.can_access_level(user, document.access_level):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view versions of this document",
            )
        
        versions = version_control.get_versions(document_id, limit=limit, offset=offset)
        
        logger.info(f"Retrieved {len(versions)} versions for document {document_id}")
        
        return versions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching versions for document {document_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch document versions",
        )


@router.post("/{document_id}/versions/revert", response_model=DocumentResponse)
def revert_document_version(
    document_id: str,
    version: int = Form(..., description="Version number to revert to"),
    user: User = UserDep,
    session: SessionDep,
    access_control: AccessControlService = AccessControlDep,
    version_control: VersionControlService = VersionControlDep,
    audit_logger: AuditLogger = AuditLoggerDep,
):
    """Revert a document to a previous version.
    
    Args:
        document_id: The document ID
        version: Version number to revert to
        user: Authenticated user
        session: Database session
        access_control: Access control service
        version_control: Version control service
        audit_logger: Audit logger
        
    Returns:
        The new version created by the revert
        
    Raises:
        HTTPException: If document not found or access denied
    """
    try:
        logger.info(f"Revert requested for document {document_id} to version {version} by user {user.username}")
        
        repository = DocumentRepository(session)
        document = repository.get_by_document_id(document_id)
        
        if not document:
           