"""
Scenarios API routes - Test scenario management.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db.database import get_db
from ..db.models import User, Scenario, Operation
from ..auth.service import get_current_active_user, get_current_user

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


class ScenarioCreate(BaseModel):
    """Request to create a scenario."""
    operation_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    request_template: dict
    headers_template: Optional[dict] = None
    body_template: Optional[dict] = None
    auth_requirements: Optional[dict] = None
    environment: str = "default"


class ScenarioUpdate(BaseModel):
    """Request to update a scenario."""
    name: Optional[str] = None
    description: Optional[str] = None
    request_template: Optional[dict] = None
    headers_template: Optional[dict] = None
    body_template: Optional[dict] = None
    baseline_response: Optional[dict] = None


class ScenarioResponse(BaseModel):
    """Scenario response."""
    id: str
    operation_id: str
    name: Optional[str]
    description: Optional[str]
    environment: str
    version: int
    is_active: bool
    has_baseline: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ScenarioDetailResponse(ScenarioResponse):
    """Detailed scenario response."""
    request_template: dict
    headers_template: Optional[dict]
    body_template: Optional[dict]
    auth_requirements: Optional[dict]
    baseline_response: Optional[dict]
    baseline_response_hash: Optional[str]


class ScenarioListResponse(BaseModel):
    """List of scenarios response."""
    scenarios: List[ScenarioResponse]
    total: int


@router.post("/", response_model=ScenarioResponse)
def create_scenario(
    request: ScenarioCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Create a new test scenario for an operation."""
    # Verify operation exists
    operation = db.query(Operation).filter(Operation.id == request.operation_id).first()
    if not operation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operation not found",
        )
    
    scenario = Scenario(
        operation_id=request.operation_id,
        name=request.name or f"{operation.method} {operation.path}",
        description=request.description,
        request_template=request.request_template,
        headers_template=request.headers_template,
        body_template=request.body_template,
        auth_requirements=request.auth_requirements,
        environment=request.environment,
    )
    
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    
    return ScenarioResponse(
        id=scenario.id,
        operation_id=scenario.operation_id,
        name=scenario.name,
        description=scenario.description,
        environment=scenario.environment,
        version=scenario.version,
        is_active=scenario.is_active,
        has_baseline=scenario.baseline_response is not None,
        created_at=scenario.created_at.isoformat(),
        updated_at=scenario.updated_at.isoformat(),
    )


@router.get("/", response_model=ScenarioListResponse)
def list_scenarios(
    operation_id: Optional[str] = None,
    environment: Optional[str] = None,
    has_baseline: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List all scenarios with optional filtering."""
    query = db.query(Scenario).filter(Scenario.is_active == True)
    
    if operation_id:
        query = query.filter(Scenario.operation_id == operation_id)
    
    if environment:
        query = query.filter(Scenario.environment == environment)
    
    scenarios = query.order_by(Scenario.created_at.desc()).offset(skip).limit(limit).all()
    
    if has_baseline is not None:
        if has_baseline:
            scenarios = [s for s in scenarios if s.baseline_response is not None]
        else:
            scenarios = [s for s in scenarios if s.baseline_response is None]
    
    total = query.count()
    
    return ScenarioListResponse(
        scenarios=[
            ScenarioResponse(
                id=s.id,
                operation_id=s.operation_id,
                name=s.name,
                description=s.description,
                environment=s.environment,
                version=s.version,
                is_active=s.is_active,
                has_baseline=s.baseline_response is not None,
                created_at=s.created_at.isoformat(),
                updated_at=s.updated_at.isoformat(),
            )
            for s in scenarios
        ],
        total=total,
    )


@router.get("/{scenario_id}", response_model=ScenarioDetailResponse)
def get_scenario(
    scenario_id: str,
    db: Session = Depends(get_db),
):
    """Get a specific scenario by ID."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )
    
    return ScenarioDetailResponse(
        id=scenario.id,
        operation_id=scenario.operation_id,
        name=scenario.name,
        description=scenario.description,
        environment=scenario.environment,
        version=scenario.version,
        is_active=scenario.is_active,
        has_baseline=scenario.baseline_response is not None,
        request_template=scenario.request_template,
        headers_template=scenario.headers_template,
        body_template=scenario.body_template,
        auth_requirements=scenario.auth_requirements,
        baseline_response=scenario.baseline_response,
        baseline_response_hash=scenario.baseline_response_hash,
        created_at=scenario.created_at.isoformat(),
        updated_at=scenario.updated_at.isoformat(),
    )


@router.put("/{scenario_id}", response_model=ScenarioResponse)
def update_scenario(
    scenario_id: str,
    request: ScenarioUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a scenario."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )
    
    if request.name is not None:
        scenario.name = request.name
    if request.description is not None:
        scenario.description = request.description
    if request.request_template is not None:
        scenario.request_template = request.request_template
    if request.headers_template is not None:
        scenario.headers_template = request.headers_template
    if request.body_template is not None:
        scenario.body_template = request.body_template
    if request.baseline_response is not None:
        import hashlib
        import json
        scenario.baseline_response = request.baseline_response
        scenario.baseline_response_hash = hashlib.sha256(
            json.dumps(request.baseline_response, sort_keys=True).encode()
        ).hexdigest()
        scenario.version += 1
    
    db.commit()
    db.refresh(scenario)
    
    return ScenarioResponse(
        id=scenario.id,
        operation_id=scenario.operation_id,
        name=scenario.name,
        description=scenario.description,
        environment=scenario.environment,
        version=scenario.version,
        is_active=scenario.is_active,
        has_baseline=scenario.baseline_response is not None,
        created_at=scenario.created_at.isoformat(),
        updated_at=scenario.updated_at.isoformat(),
    )


@router.delete("/{scenario_id}")
def delete_scenario(
    scenario_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Soft delete a scenario."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )
    
    scenario.is_active = False
    db.commit()
    
    return {"status": "deleted", "id": scenario_id}
