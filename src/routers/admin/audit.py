import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from src.dependencies import AccessControlDep, AuditLoggerDep, UserDep
from src.schemas.common.security import User
from src.services.security.access_control_service import AccessControlService
from src.services.security.audit_logger import AuditLogger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/audit", tags=["admin-audit"])


@router.get("/logs")
async def get_audit_logs(
    user: UserDep,
    access_control: AccessControlDep,
    audit_logger: AuditLoggerDep,
    start_date: Optional[datetime] = Query(None, description="Start date for log filtering (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date for log filtering (ISO format)"),
    user_id: Optional[str] = Query(None, description="Filter logs by user ID"),
    event_type: Optional[str] = Query(None, description="Filter logs by event type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """Get audit logs for administrative review.
    
    This endpoint allows administrators to query audit logs with various filters.
    Access is restricted to users with admin or superuser roles.
    
    Args:
        start_date: Optional start date filter
        end_date: Optional end date filter
        user_id: Optional user ID filter
        event_type: Optional event type filter
        limit: Maximum number of logs
        offset: Pagination offset
        user: Authenticated admin user
        access_control: Access control service
        audit_logger: Audit logger
        
    Returns:
        List of audit log entries
        
    Raises:
        HTTPException: If user is not an administrator
    """
    logger.info(f"Audit log query by user: {user.username}")
    
    # Verify admin permissions
    if not any(role in ["admin", "superuser"] for role in user.roles):
        audit_logger.log_security_event(
            user=user,
            event="unauthorized_audit_access",
            reason=f"Non-admin user attempted to access audit logs",
            severity="medium",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to access audit logs",
        )
    
    # Fetch logs (this would query the audit_logs table in production)
    # For now, returning empty list as placeholder
    logs = await audit_logger.get_audit_logs(
        user_id=user_id,
        event_type=event_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    
    logger.debug(f"Retrieved {len(logs)} audit logs for admin query")
    
    return {
        "logs": logs,
        "total": len(logs),
        "limit": limit,
        "offset": offset,
    }


@router.get("/export")
async def export_audit_logs(
    user: UserDep,
    access_control: AccessControlDep,
    audit_logger: AuditLoggerDep,
    start_date: datetime = Query(..., description="Start date for export"),
    end_date: datetime = Query(..., description="End date for export"),
    format: str = Query("json", regex="^(json|csv)$", description="Export format"),
):
    """Export audit logs for compliance reporting or GDPR requests.
    
    This endpoint exports audit logs in JSON or CSV format for compliance
    purposes. Access is restricted to administrators only.
    
    Args:
        start_date: Start date for export range
        end_date: End date for export range
        format: Export format (json or csv)
        user: Authenticated admin user
        access_control: Access control service
        audit_logger: Audit logger
        
    Returns:
        Streaming response with exported logs
        
    Raises:
        HTTPException: If user is not an administrator
    """
    logger.info(f"Audit log export requested by user: {user.username}")
    
    # Verify admin permissions
    if not any(role in ["admin", "superuser"] for role in user.roles):
        audit_logger.log_security_event(
            user=user,
            event="unauthorized_export_attempt",
            reason=f"Non-admin user attempted to export audit logs",
            severity="high",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to export audit logs",
        )
    
    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date",
        )
    
    # Fetch logs for export
    logs = await audit_logger.get_audit_logs(
        start_date=start_date,
        end_date=end_date,
        limit=10000,  # Large limit for export
    )
    
    logger.info(f"Exporting {len(logs)} audit logs from {start_date} to {end_date} as {format}")
    
    if format == "json":
        import json
        
        def generate_json():
            yield "[\n"
            for i, log in enumerate(logs):
                if i > 0:
                    yield ",\n"
                yield json.dumps(log, indent=2)
            yield "\n]"
        
        return StreamingResponse(
            generate_json(),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=audit_logs_{start_date.date()}_{end_date.date()}.json"
            },
        )
    
    elif format == "csv":
        import csv
        import io
        
        def generate_csv():
            if not logs:
                return
            
            # Get all unique keys for headers
            all_keys = set()
            for log in logs:
                all_keys.update(log.keys())
            
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=sorted(all_keys))
            writer.writeheader()
            
            for log in logs:
                writer.writerow(log)
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)
        
        return StreamingResponse(
            generate_csv(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=audit_logs_{start_date.date()}_{end_date.date()}.csv"
            },
        )


@router.post("/retention/apply")
async def apply_retention_policies(
    user: UserDep,
    access_control: AccessControlDep,
    audit_logger: AuditLoggerDep,
    dry_run: bool = Query(False, description="Preview retention actions without executing"),
):
    """Manually trigger retention policy enforcement.
    
    This endpoint allows administrators to manually run the retention policy
    enforcement process. It can operate in dry-run mode to preview actions.
    
    Args:
        dry_run: If True, only preview actions without executing
        user: Authenticated admin user
        access_control: Access control service
        audit_logger: Audit logger
        
    Returns:
        Statistics about retention actions performed or previewed
        
    Raises:
        HTTPException: If user is not an administrator
    """
    logger.info(f"Retention policy enforcement triggered by user: {user.username} (dry_run: {dry_run})")
    
    # Verify admin permissions
    if not any(role in ["admin", "superuser"] for role in user.roles):
        audit_logger.log_security_event(
            user=user,
            event="unauthorized_retention_trigger",
            reason=f"Non-admin user attempted to apply retention policies",
            severity="medium",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to apply retention policies",
        )
    
    # Get retention service
    from src.database import get_db_session
    from src.repositories.document import DocumentRepository
    
    with get_db_session() as session:
        repository = DocumentRepository(session)
        retention_service = RetentionService(repository=repository, audit_logger=audit_logger)
        
        if dry_run:
            # Preview mode - return what WOULD be done
            stats = retention_service.preview_retention_actions()
            logger.info(f"Retention preview: {stats}")
            return {
                "mode": "dry_run",
                "message": "Retention actions previewed (no changes made)",
                "stats": stats,
            }
        else:
            # Execute retention enforcement
            stats = retention_service.enforce_retention_policy()
            logger.info(f"Retention enforcement completed: {stats}")
            
            # Log system action
            audit_logger.log_retention_action(
                document_id="all",
                action="manual_enforcement",
                reason=f"Triggered by admin user {user.username}",
                user_id=user.id,
            )
            
            return {
                "mode": "execution",
                "message": "Retention policies applied successfully",
                "stats": stats,
            }


@router.get("/stats")
async def get_audit_stats(
    user: UserDep,
    access_control: AccessControlDep,
    audit_logger: AuditLoggerDep,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
):
    """Get audit statistics for compliance reporting.
    
    This endpoint provides aggregated statistics about system usage,
    document access patterns, and security events.
    
    Args:
        days: Number of days to analyze
        user: Authenticated admin user
        access_control: Access control service
        audit_logger: Audit logger
        
    Returns:
        Aggregated audit statistics
        
    Raises:
        HTTPException: If user is not an administrator
    """
    logger.info(f"Audit stats requested by user: {user.username} for {days} days")
    
    # Verify admin permissions
    if not any(role in ["admin", "superuser"] for role in user.roles):
        audit_logger.log_security_event(
            user=user,
            event="unauthorized_stats_access",
            reason=f"Non-admin user attempted to access audit stats",
            severity="medium",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to access audit statistics",
        )
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Fetch logs for analysis
    logs = await audit_logger.get_audit_logs(
        start_date=start_date,
        end_date=end_date,
        limit=10000,
    )
    
    # Analyze logs to generate statistics
    stats = {
        "period_days": days,
        "total_events": len(logs),
        "events_by_type": {},
        "unique_users": set(),
        "document_access_count": 0,
        "failed_authentication_count": 0,
        "security_events": 0,
    }
    
    for log in logs:
        # Count events by type
        event_type = log.get("event_type", "unknown")
        stats["events_by_type"][event_type] = stats["events_by_type"].get(event_type, 0) + 1
        
        # Track unique users
        user_id = log.get("user_id")
        if user_id:
            stats["unique_users"].add(user_id)
        
        # Count specific event types
        if event_type == "document_access":
            stats["document_access_count"] += 1
        elif event_type in ["login_failure", "unauthorized_access"]:
            stats["failed_authentication_count"] += 1
        elif event_type == "security_event":
            stats["security_events"] += 1
    
    # Convert sets to counts
    stats["unique_users"] = len(stats["unique_users"])
    
    logger.debug(f"Generated audit stats for {stats['total_events']} events")
    
    return stats


@router.get("/gdpr/export")
async def gdpr_data_export(
    requesting_user: UserDep,
    access_control: AccessControlDep,
    audit_logger: AuditLoggerDep,
    user_id: str = Query(..., description="User ID for GDPR data export request"),
):
    """Export all data related to a specific user for GDPR compliance.
    
    This endpoint allows administrators to export all data associated with
    a specific user to comply with GDPR data portability requirements.
    
    Args:
        user_id: ID of the user whose data to export
        requesting_user: The admin user making the request
        access_control: Access control service
        audit_logger: Audit logger
        
    Returns:
        JSON export of all user data
        
    Raises:
        HTTPException: If user is not an administrator
    """
    logger.info(f"GDPR export requested for user {user_id} by admin: {requesting_user.username}")
    
    # Verify admin permissions
    if not any(role in ["admin", "superuser"] for role in requesting_user.roles):
        audit_logger.log_security_event(
            user=requesting_user,
            event="unauthorized_gdpr_export_attempt",
            reason=f"Non-admin attempted GDPR export for user {user_id}",
            severity="high",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for GDPR data export",
        )
    
    # Log the GDPR export request (important for compliance)
    audit_logger.log_security_event(
        user=requesting_user,
        event="gdpr_data_export",
        reason=f"Exported all data for user {user_id}",
        severity="medium",
    )
    
    # TODO: Implement actual GDPR data export
    # This would collect:
    # - User profile information
    # - Documents created/uploaded by the user
    # - Audit logs related to the user
    # - Search history
    # - Any other user-associated data
    
    # For now, return mock data structure
    export_data = {
        "user_id": user_id,
        "export_timestamp": datetime.utcnow().isoformat(),
        "data": {
            "profile": {},  # User profile data
            "documents": [],  # Documents owned by user
            "audit_logs": [],  # User's audit trail
            "search_history": [],  # Search queries
        },
        "note": "This is a mock export. Real implementation would collect all user data.",
    }
    
    logger.info(f"GDPR export completed for user: {user_id}")
    
    return export_data
