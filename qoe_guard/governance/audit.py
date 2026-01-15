"""
Audit Trail Service.

Records all significant actions for compliance and debugging.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..db.models import AuditLog, User


class AuditAction(Enum):
    """Types of auditable actions."""
    # Auth
    USER_LOGIN = "user.login"
    USER_REGISTER = "user.register"
    USER_LOGOUT = "user.logout"
    USER_ROLE_CHANGE = "user.role_change"
    
    # Specs
    SPEC_DISCOVER = "spec.discover"
    SPEC_DELETE = "spec.delete"
    
    # Scenarios
    SCENARIO_CREATE = "scenario.create"
    SCENARIO_UPDATE = "scenario.update"
    SCENARIO_DELETE = "scenario.delete"
    
    # Validation
    VALIDATION_START = "validation.start"
    VALIDATION_COMPLETE = "validation.complete"
    
    # Baseline governance
    PROMOTION_REQUEST = "promotion.request"
    PROMOTION_APPROVE = "promotion.approve"
    PROMOTION_REJECT = "promotion.reject"
    BASELINE_ROLLBACK = "baseline.rollback"
    
    # Policy
    POLICY_UPDATE = "policy.update"
    CRITICALITY_UPDATE = "criticality.update"


class AuditService:
    """Service for recording and querying audit logs."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log(
        self,
        action: AuditAction,
        resource_type: str,
        resource_id: Optional[str] = None,
        user: Optional[User] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Record an audit log entry.
        
        Args:
            action: The action being performed
            resource_type: Type of resource (e.g., "scenario", "policy")
            resource_id: ID of the affected resource
            user: User performing the action
            details: Additional details as JSON
            ip_address: Client IP address
            user_agent: Client user agent
        
        Returns:
            Created AuditLog entry
        """
        log_entry = AuditLog(
            user_id=user.id if user else None,
            action=action.value,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)
        
        return log_entry
    
    def query(
        self,
        action: Optional[AuditAction] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """
        Query audit logs with filtering.
        
        Args:
            action: Filter by action type
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            user_id: Filter by user
            since: Filter by start time
            until: Filter by end time
            limit: Maximum records to return
            offset: Pagination offset
        
        Returns:
            List of matching AuditLog entries
        """
        query = self.db.query(AuditLog)
        
        if action:
            query = query.filter(AuditLog.action == action.value)
        
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        
        if resource_id:
            query = query.filter(AuditLog.resource_id == resource_id)
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        
        if since:
            query = query.filter(AuditLog.created_at >= since)
        
        if until:
            query = query.filter(AuditLog.created_at <= until)
        
        return query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()
    
    def get_resource_history(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 50,
    ) -> List[AuditLog]:
        """Get audit history for a specific resource."""
        return self.query(
            resource_type=resource_type,
            resource_id=resource_id,
            limit=limit,
        )
    
    def get_user_activity(
        self,
        user_id: str,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get audit history for a specific user."""
        if since is None:
            since = datetime.utcnow() - timedelta(days=30)
        
        return self.query(
            user_id=user_id,
            since=since,
            limit=limit,
        )
    
    def get_recent_promotions(
        self,
        limit: int = 20,
    ) -> List[AuditLog]:
        """Get recent baseline promotion activity."""
        return self.db.query(AuditLog).filter(
            AuditLog.action.in_([
                AuditAction.PROMOTION_REQUEST.value,
                AuditAction.PROMOTION_APPROVE.value,
                AuditAction.PROMOTION_REJECT.value,
                AuditAction.BASELINE_ROLLBACK.value,
            ])
        ).order_by(desc(AuditLog.created_at)).limit(limit).all()
    
    def count_by_action(
        self,
        since: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """Get count of logs by action type."""
        from sqlalchemy import func
        
        query = self.db.query(
            AuditLog.action,
            func.count(AuditLog.id).label("count")
        )
        
        if since:
            query = query.filter(AuditLog.created_at >= since)
        
        results = query.group_by(AuditLog.action).all()
        
        return {r.action: r.count for r in results}


def audit_action(
    db: Session,
    action: AuditAction,
    resource_type: str,
    resource_id: Optional[str] = None,
    user: Optional[User] = None,
    details: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """Convenience function to log an audit entry."""
    service = AuditService(db)
    return service.log(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user=user,
        details=details,
    )
