"""
Governance API routes - Baseline promotion and approvals.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db.database import get_db
from ..db.models import (
    User, Role, Scenario, PromotionRequest, BaselinePromotion,
    PromotionStatus, PolicyConfig, CriticalityProfile, AuditLog,
)
from ..auth.service import get_current_active_user
from ..auth.middleware import require_role

router = APIRouter(prefix="/governance", tags=["Governance"])


class PromotionRequestCreate(BaseModel):
    """Request to promote a new baseline."""
    scenario_id: str
    new_baseline: dict
    justification: Optional[str] = None


class PromotionDecision(BaseModel):
    """Approval or rejection decision."""
    reason: Optional[str] = None


class PromotionRequestResponse(BaseModel):
    """Promotion request response."""
    id: str
    scenario_id: str
    requester_id: str
    status: str
    new_baseline_hash: str
    prior_baseline_hash: Optional[str]
    justification: Optional[str]
    stable_runs_count: Optional[int]
    qoe_degradation_check: Optional[bool]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class PromotionListResponse(BaseModel):
    """List of promotion requests."""
    requests: List[PromotionRequestResponse]
    total: int


class PolicyConfigResponse(BaseModel):
    """Policy configuration response."""
    id: str
    name: str
    description: Optional[str]
    is_active: bool
    version: str
    brittleness_fail_threshold: float
    brittleness_warn_threshold: float
    qoe_fail_threshold: float
    qoe_warn_threshold: float
    fail_on_critical_type_changes: bool
    fail_on_undocumented_drift: bool
    warn_on_spec_drift: bool
    allowed_drift_paths: Optional[List[str]]
    skip_operations: Optional[List[str]]

    class Config:
        from_attributes = True


class PolicyConfigUpdate(BaseModel):
    """Policy configuration update request."""
    name: Optional[str] = None
    description: Optional[str] = None
    brittleness_fail_threshold: Optional[float] = None
    brittleness_warn_threshold: Optional[float] = None
    qoe_fail_threshold: Optional[float] = None
    qoe_warn_threshold: Optional[float] = None
    fail_on_critical_type_changes: Optional[bool] = None
    fail_on_undocumented_drift: Optional[bool] = None
    warn_on_spec_drift: Optional[bool] = None
    allowed_drift_paths: Optional[List[str]] = None
    skip_operations: Optional[List[str]] = None


class CriticalityProfileResponse(BaseModel):
    """Criticality profile response."""
    id: str
    name: str
    profile_type: str
    weight: float
    description: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class CriticalityProfileCreate(BaseModel):
    """Criticality profile create request."""
    name: str
    profile_type: str  # "tag" or "path"
    weight: float
    description: Optional[str] = None


# -------------------- Promotion Requests --------------------

@router.post("/promotions", response_model=PromotionRequestResponse)
def request_promotion(
    request: PromotionRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Request promotion of a new baseline for a scenario.
    
    The request will be reviewed by an approver before the baseline is updated.
    """
    import hashlib
    import json
    
    # Verify scenario exists
    scenario = db.query(Scenario).filter(Scenario.id == request.scenario_id).first()
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )
    
    # Check for pending requests
    pending = db.query(PromotionRequest).filter(
        PromotionRequest.scenario_id == request.scenario_id,
        PromotionRequest.status == PromotionStatus.PENDING,
    ).first()
    
    if pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A promotion request is already pending for this scenario",
        )
    
    # Compute baseline hash
    new_hash = hashlib.sha256(
        json.dumps(request.new_baseline, sort_keys=True).encode()
    ).hexdigest()
    
    # Create promotion request
    promotion_req = PromotionRequest(
        scenario_id=request.scenario_id,
        requester_id=current_user.id,
        new_baseline=request.new_baseline,
        new_baseline_hash=new_hash,
        prior_baseline_hash=scenario.baseline_response_hash,
        justification=request.justification,
    )
    
    db.add(promotion_req)
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="promotion.request",
        resource_type="scenario",
        resource_id=request.scenario_id,
        details={"new_hash": new_hash, "justification": request.justification},
    )
    db.add(audit)
    
    db.commit()
    db.refresh(promotion_req)
    
    return PromotionRequestResponse(
        id=promotion_req.id,
        scenario_id=promotion_req.scenario_id,
        requester_id=promotion_req.requester_id,
        status=promotion_req.status.value,
        new_baseline_hash=promotion_req.new_baseline_hash,
        prior_baseline_hash=promotion_req.prior_baseline_hash,
        justification=promotion_req.justification,
        stable_runs_count=promotion_req.stable_runs_count,
        qoe_degradation_check=promotion_req.qoe_degradation_check,
        created_at=promotion_req.created_at.isoformat(),
        updated_at=promotion_req.updated_at.isoformat(),
    )


@router.get("/promotions", response_model=PromotionListResponse)
def list_promotions(
    status_filter: Optional[str] = None,
    scenario_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List promotion requests with optional filtering."""
    query = db.query(PromotionRequest)
    
    if status_filter:
        try:
            status_enum = PromotionStatus(status_filter)
            query = query.filter(PromotionRequest.status == status_enum)
        except ValueError:
            pass
    
    if scenario_id:
        query = query.filter(PromotionRequest.scenario_id == scenario_id)
    
    requests = query.order_by(PromotionRequest.created_at.desc()).offset(skip).limit(limit).all()
    total = query.count()
    
    return PromotionListResponse(
        requests=[
            PromotionRequestResponse(
                id=r.id,
                scenario_id=r.scenario_id,
                requester_id=r.requester_id,
                status=r.status.value,
                new_baseline_hash=r.new_baseline_hash,
                prior_baseline_hash=r.prior_baseline_hash,
                justification=r.justification,
                stable_runs_count=r.stable_runs_count,
                qoe_degradation_check=r.qoe_degradation_check,
                created_at=r.created_at.isoformat(),
                updated_at=r.updated_at.isoformat(),
            )
            for r in requests
        ],
        total=total,
    )


@router.get("/promotions/pending", response_model=PromotionListResponse)
def list_pending_promotions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([Role.ADMIN, Role.APPROVER])),
):
    """List pending promotion requests (approvers only)."""
    requests = db.query(PromotionRequest).filter(
        PromotionRequest.status == PromotionStatus.PENDING
    ).order_by(PromotionRequest.created_at.asc()).all()
    
    return PromotionListResponse(
        requests=[
            PromotionRequestResponse(
                id=r.id,
                scenario_id=r.scenario_id,
                requester_id=r.requester_id,
                status=r.status.value,
                new_baseline_hash=r.new_baseline_hash,
                prior_baseline_hash=r.prior_baseline_hash,
                justification=r.justification,
                stable_runs_count=r.stable_runs_count,
                qoe_degradation_check=r.qoe_degradation_check,
                created_at=r.created_at.isoformat(),
                updated_at=r.updated_at.isoformat(),
            )
            for r in requests
        ],
        total=len(requests),
    )


@router.post("/promotions/{request_id}/approve")
def approve_promotion(
    request_id: str,
    decision: PromotionDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([Role.ADMIN, Role.APPROVER])),
):
    """Approve a promotion request (approvers only)."""
    promotion_req = db.query(PromotionRequest).filter(PromotionRequest.id == request_id).first()
    if not promotion_req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promotion request not found",
        )
    
    if promotion_req.status != PromotionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request is already {promotion_req.status.value}",
        )
    
    if promotion_req.requester_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot approve your own request",
        )
    
    # Update scenario baseline
    scenario = db.query(Scenario).filter(Scenario.id == promotion_req.scenario_id).first()
    scenario.baseline_response = promotion_req.new_baseline
    scenario.baseline_response_hash = promotion_req.new_baseline_hash
    scenario.version += 1
    
    # Update promotion request
    promotion_req.status = PromotionStatus.APPROVED
    
    # Create promotion record
    promotion = BaselinePromotion(
        request_id=promotion_req.id,
        scenario_id=promotion_req.scenario_id,
        approver_id=current_user.id,
        action_type="approve",
        prior_hash=promotion_req.prior_baseline_hash,
        new_hash=promotion_req.new_baseline_hash,
        scenario_version=scenario.version,
        reason=decision.reason,
    )
    db.add(promotion)
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="promotion.approve",
        resource_type="scenario",
        resource_id=promotion_req.scenario_id,
        details={"request_id": request_id, "reason": decision.reason},
    )
    db.add(audit)
    
    db.commit()
    
    return {"status": "approved", "request_id": request_id, "new_version": scenario.version}


@router.post("/promotions/{request_id}/reject")
def reject_promotion(
    request_id: str,
    decision: PromotionDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([Role.ADMIN, Role.APPROVER])),
):
    """Reject a promotion request (approvers only)."""
    promotion_req = db.query(PromotionRequest).filter(PromotionRequest.id == request_id).first()
    if not promotion_req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promotion request not found",
        )
    
    if promotion_req.status != PromotionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request is already {promotion_req.status.value}",
        )
    
    # Update promotion request
    promotion_req.status = PromotionStatus.REJECTED
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="promotion.reject",
        resource_type="scenario",
        resource_id=promotion_req.scenario_id,
        details={"request_id": request_id, "reason": decision.reason},
    )
    db.add(audit)
    
    db.commit()
    
    return {"status": "rejected", "request_id": request_id, "reason": decision.reason}


# -------------------- Policy Configuration --------------------

@router.get("/policy", response_model=PolicyConfigResponse)
def get_active_policy(
    db: Session = Depends(get_db),
):
    """Get the active policy configuration."""
    policy = db.query(PolicyConfig).filter(PolicyConfig.is_active == True).first()
    
    if not policy:
        # Return default policy
        return PolicyConfigResponse(
            id="default",
            name="Default Policy",
            description="Default QoE-Guard policy",
            is_active=True,
            version="1.0.0",
            brittleness_fail_threshold=75.0,
            brittleness_warn_threshold=50.0,
            qoe_fail_threshold=0.72,
            qoe_warn_threshold=0.45,
            fail_on_critical_type_changes=True,
            fail_on_undocumented_drift=True,
            warn_on_spec_drift=True,
            allowed_drift_paths=[],
            skip_operations=[],
        )
    
    return PolicyConfigResponse(
        id=policy.id,
        name=policy.name,
        description=policy.description,
        is_active=policy.is_active,
        version=policy.version,
        brittleness_fail_threshold=policy.brittleness_fail_threshold,
        brittleness_warn_threshold=policy.brittleness_warn_threshold,
        qoe_fail_threshold=policy.qoe_fail_threshold,
        qoe_warn_threshold=policy.qoe_warn_threshold,
        fail_on_critical_type_changes=policy.fail_on_critical_type_changes,
        fail_on_undocumented_drift=policy.fail_on_undocumented_drift,
        warn_on_spec_drift=policy.warn_on_spec_drift,
        allowed_drift_paths=policy.allowed_drift_paths,
        skip_operations=policy.skip_operations,
    )


@router.put("/policy", response_model=PolicyConfigResponse)
def update_policy(
    update: PolicyConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([Role.ADMIN])),
):
    """Update the active policy configuration (admin only)."""
    policy = db.query(PolicyConfig).filter(PolicyConfig.is_active == True).first()
    
    if not policy:
        # Create new policy
        policy = PolicyConfig(
            name=update.name or "Default Policy",
            description=update.description,
            is_active=True,
            version="1.0.0",
        )
        db.add(policy)
    
    # Update fields
    if update.name is not None:
        policy.name = update.name
    if update.description is not None:
        policy.description = update.description
    if update.brittleness_fail_threshold is not None:
        policy.brittleness_fail_threshold = update.brittleness_fail_threshold
    if update.brittleness_warn_threshold is not None:
        policy.brittleness_warn_threshold = update.brittleness_warn_threshold
    if update.qoe_fail_threshold is not None:
        policy.qoe_fail_threshold = update.qoe_fail_threshold
    if update.qoe_warn_threshold is not None:
        policy.qoe_warn_threshold = update.qoe_warn_threshold
    if update.fail_on_critical_type_changes is not None:
        policy.fail_on_critical_type_changes = update.fail_on_critical_type_changes
    if update.fail_on_undocumented_drift is not None:
        policy.fail_on_undocumented_drift = update.fail_on_undocumented_drift
    if update.warn_on_spec_drift is not None:
        policy.warn_on_spec_drift = update.warn_on_spec_drift
    if update.allowed_drift_paths is not None:
        policy.allowed_drift_paths = update.allowed_drift_paths
    if update.skip_operations is not None:
        policy.skip_operations = update.skip_operations
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="policy.update",
        resource_type="policy",
        resource_id=policy.id,
        details=update.model_dump(exclude_none=True),
    )
    db.add(audit)
    
    db.commit()
    db.refresh(policy)
    
    return PolicyConfigResponse(
        id=policy.id,
        name=policy.name,
        description=policy.description,
        is_active=policy.is_active,
        version=policy.version,
        brittleness_fail_threshold=policy.brittleness_fail_threshold,
        brittleness_warn_threshold=policy.brittleness_warn_threshold,
        qoe_fail_threshold=policy.qoe_fail_threshold,
        qoe_warn_threshold=policy.qoe_warn_threshold,
        fail_on_critical_type_changes=policy.fail_on_critical_type_changes,
        fail_on_undocumented_drift=policy.fail_on_undocumented_drift,
        warn_on_spec_drift=policy.warn_on_spec_drift,
        allowed_drift_paths=policy.allowed_drift_paths,
        skip_operations=policy.skip_operations,
    )


# -------------------- Criticality Profiles --------------------

@router.get("/criticality", response_model=List[CriticalityProfileResponse])
def list_criticality_profiles(
    profile_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all criticality profiles."""
    query = db.query(CriticalityProfile).filter(CriticalityProfile.is_active == True)
    
    if profile_type:
        query = query.filter(CriticalityProfile.profile_type == profile_type)
    
    profiles = query.order_by(CriticalityProfile.weight.desc()).all()
    
    return [
        CriticalityProfileResponse(
            id=p.id,
            name=p.name,
            profile_type=p.profile_type,
            weight=p.weight,
            description=p.description,
            is_active=p.is_active,
        )
        for p in profiles
    ]


@router.post("/criticality", response_model=CriticalityProfileResponse)
def create_criticality_profile(
    request: CriticalityProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([Role.ADMIN])),
):
    """Create a new criticality profile (admin only)."""
    if request.profile_type not in ["tag", "path"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="profile_type must be 'tag' or 'path'",
        )
    
    if not 0.0 <= request.weight <= 1.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="weight must be between 0.0 and 1.0",
        )
    
    profile = CriticalityProfile(
        name=request.name,
        profile_type=request.profile_type,
        weight=request.weight,
        description=request.description,
    )
    
    db.add(profile)
    db.commit()
    db.refresh(profile)
    
    return CriticalityProfileResponse(
        id=profile.id,
        name=profile.name,
        profile_type=profile.profile_type,
        weight=profile.weight,
        description=profile.description,
        is_active=profile.is_active,
    )


@router.delete("/criticality/{profile_id}")
def delete_criticality_profile(
    profile_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([Role.ADMIN])),
):
    """Delete a criticality profile (admin only)."""
    profile = db.query(CriticalityProfile).filter(CriticalityProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    
    profile.is_active = False
    db.commit()
    
    return {"status": "deleted", "id": profile_id}
