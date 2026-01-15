"""
Validations API routes - Validation job execution and results.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db.database import get_db
from ..db.models import User, ValidationRun, OperationResult, DecisionType, DriftType
from ..auth.service import get_current_active_user, get_current_user

router = APIRouter(prefix="/validations", tags=["Validations"])


class ValidationJobCreate(BaseModel):
    """Request to create a validation job."""
    spec_id: Optional[str] = None
    selected_operations: List[str]  # List of operation IDs
    environment: str = "default"
    auth_mode: Optional[str] = None
    auth_config: Optional[dict] = None
    concurrency: int = 5
    rate_limit_per_host: int = 10
    safe_methods_only: bool = True


class OperationResultResponse(BaseModel):
    """Single operation result response."""
    id: str
    operation_id: Optional[str]
    request_url: Optional[str]
    request_method: Optional[str]
    status_code: Optional[int]
    response_time_ms: Optional[float]
    conformance_status: Optional[str]
    error_message: Optional[str]
    brittleness_contribution: Optional[float]
    qoe_contribution: Optional[float]

    class Config:
        from_attributes = True


class ValidationRunResponse(BaseModel):
    """Validation run response."""
    id: str
    spec_id: Optional[str]
    environment: str
    brittleness_score: Optional[float]
    qoe_risk_score: Optional[float]
    drift_type: Optional[str]
    decision: Optional[str]
    started_at: str
    completed_at: Optional[str]
    duration_ms: Optional[int]
    operation_count: int

    class Config:
        from_attributes = True


class ValidationRunDetailResponse(ValidationRunResponse):
    """Detailed validation run response."""
    selected_operations: Optional[List[str]]
    policy_version: Optional[str]
    model_version: Optional[str]
    reasons: Optional[dict]
    recommendations: Optional[List[str]]
    operation_results: List[OperationResultResponse]


class ValidationListResponse(BaseModel):
    """List of validation runs response."""
    runs: List[ValidationRunResponse]
    total: int


@router.post("/", response_model=ValidationRunResponse)
async def create_validation(
    request: ValidationJobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Create and start a new validation job.
    
    The validation runs asynchronously. Poll the run status or use webhooks.
    """
    from ..validation.orchestrator import ValidationOrchestrator
    
    # Create validation run record
    run = ValidationRun(
        spec_id=request.spec_id,
        selected_operations=request.selected_operations,
        environment=request.environment,
        auth_mode=request.auth_mode,
        created_by_id=current_user.id if current_user else None,
    )
    
    db.add(run)
    db.commit()
    db.refresh(run)
    
    # Queue background execution
    orchestrator = ValidationOrchestrator(db)
    background_tasks.add_task(
        orchestrator.execute,
        run_id=run.id,
        auth_config=request.auth_config,
        concurrency=request.concurrency,
        rate_limit_per_host=request.rate_limit_per_host,
        safe_methods_only=request.safe_methods_only,
    )
    
    return ValidationRunResponse(
        id=run.id,
        spec_id=run.spec_id,
        environment=run.environment,
        brittleness_score=run.brittleness_score,
        qoe_risk_score=run.qoe_risk_score,
        drift_type=run.drift_type.value if run.drift_type else None,
        decision=run.decision.value if run.decision else None,
        started_at=run.started_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        duration_ms=run.duration_ms,
        operation_count=len(request.selected_operations),
    )


@router.get("/", response_model=ValidationListResponse)
def list_validations(
    spec_id: Optional[str] = None,
    environment: Optional[str] = None,
    decision: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List validation runs with optional filtering."""
    query = db.query(ValidationRun)
    
    if spec_id:
        query = query.filter(ValidationRun.spec_id == spec_id)
    
    if environment:
        query = query.filter(ValidationRun.environment == environment)
    
    if decision:
        try:
            decision_enum = DecisionType(decision)
            query = query.filter(ValidationRun.decision == decision_enum)
        except ValueError:
            pass
    
    runs = query.order_by(ValidationRun.started_at.desc()).offset(skip).limit(limit).all()
    total = query.count()
    
    return ValidationListResponse(
        runs=[
            ValidationRunResponse(
                id=r.id,
                spec_id=r.spec_id,
                environment=r.environment,
                brittleness_score=r.brittleness_score,
                qoe_risk_score=r.qoe_risk_score,
                drift_type=r.drift_type.value if r.drift_type else None,
                decision=r.decision.value if r.decision else None,
                started_at=r.started_at.isoformat(),
                completed_at=r.completed_at.isoformat() if r.completed_at else None,
                duration_ms=r.duration_ms,
                operation_count=len(r.selected_operations or []),
            )
            for r in runs
        ],
        total=total,
    )


@router.get("/{run_id}", response_model=ValidationRunDetailResponse)
def get_validation(
    run_id: str,
    db: Session = Depends(get_db),
):
    """Get a specific validation run with full details."""
    run = db.query(ValidationRun).filter(ValidationRun.id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation run not found",
        )
    
    results = db.query(OperationResult).filter(OperationResult.run_id == run_id).all()
    
    return ValidationRunDetailResponse(
        id=run.id,
        spec_id=run.spec_id,
        environment=run.environment,
        brittleness_score=run.brittleness_score,
        qoe_risk_score=run.qoe_risk_score,
        drift_type=run.drift_type.value if run.drift_type else None,
        decision=run.decision.value if run.decision else None,
        started_at=run.started_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        duration_ms=run.duration_ms,
        operation_count=len(run.selected_operations or []),
        selected_operations=run.selected_operations,
        policy_version=run.policy_version,
        model_version=run.model_version,
        reasons=run.reasons,
        recommendations=run.recommendations,
        operation_results=[
            OperationResultResponse(
                id=r.id,
                operation_id=r.operation_id,
                request_url=r.request_url,
                request_method=r.request_method,
                status_code=r.status_code,
                response_time_ms=r.response_time_ms,
                conformance_status=r.conformance_status,
                error_message=r.error_message,
                brittleness_contribution=r.brittleness_contribution,
                qoe_contribution=r.qoe_contribution,
            )
            for r in results
        ],
    )


@router.get("/{run_id}/artifacts")
def get_validation_artifacts(
    run_id: str,
    db: Session = Depends(get_db),
):
    """Get validation artifacts (curl commands, responses, etc.)."""
    run = db.query(ValidationRun).filter(ValidationRun.id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation run not found",
        )
    
    results = db.query(OperationResult).filter(OperationResult.run_id == run_id).all()
    
    artifacts = {
        "run_id": run_id,
        "curl_commands": [],
        "responses": [],
        "schema_mismatches": [],
    }
    
    for r in results:
        if r.request_url and r.request_method:
            # Build curl command
            curl = f"curl -X {r.request_method} '{r.request_url}'"
            if r.request_headers:
                for k, v in r.request_headers.items():
                    curl += f" -H '{k}: {v}'"
            artifacts["curl_commands"].append({
                "operation_id": r.operation_id,
                "curl": curl,
            })
        
        if r.response_body:
            artifacts["responses"].append({
                "operation_id": r.operation_id,
                "status_code": r.status_code,
                "body": r.response_body,
            })
        
        if r.schema_mismatches:
            artifacts["schema_mismatches"].append({
                "operation_id": r.operation_id,
                "mismatches": r.schema_mismatches,
            })
    
    return artifacts
