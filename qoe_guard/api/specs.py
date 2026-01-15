"""
Specs API routes - OpenAPI discovery and management.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl

from ..db.database import get_db
from ..db.models import User, SpecSnapshot, Operation
from ..auth.service import get_current_active_user, get_current_user
from ..swagger.discovery import discover_openapi_spec
from ..swagger.normalizer import normalize_spec
from ..swagger.inventory import extract_operations

router = APIRouter(prefix="/specs", tags=["Specifications"])


class SpecDiscoverRequest(BaseModel):
    """Request to discover OpenAPI spec from URL."""
    url: str
    headers: Optional[dict] = None


class OperationResponse(BaseModel):
    """Single operation response."""
    id: str
    operation_id: Optional[str]
    method: str
    path: str
    tags: Optional[List[str]]
    summary: Optional[str]
    deprecated: bool

    class Config:
        from_attributes = True


class SpecResponse(BaseModel):
    """Spec snapshot response."""
    id: str
    source_url: str
    discovered_doc_url: Optional[str]
    spec_hash: str
    spec_version: Optional[str]
    title: Optional[str]
    description: Optional[str]
    servers: Optional[List[str]]
    operation_count: int
    created_at: str

    class Config:
        from_attributes = True


class SpecListResponse(BaseModel):
    """List of specs response."""
    specs: List[SpecResponse]
    total: int


class OperationListResponse(BaseModel):
    """List of operations response."""
    operations: List[OperationResponse]
    total: int


@router.post("/discover", response_model=SpecResponse)
def discover_spec(
    request: SpecDiscoverRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Discover and import an OpenAPI spec from a Swagger URL.
    
    Supports:
    - Direct OpenAPI JSON/YAML URLs
    - Swagger UI URLs (will discover underlying spec)
    - File URLs with authentication headers
    """
    try:
        # Discover the OpenAPI document
        discovery_result = discover_openapi_spec(request.url, request.headers)
        
        # Normalize the spec (dereference $refs, etc.)
        normalized = normalize_spec(discovery_result.spec)
        
        # Check if we already have this spec
        existing = db.query(SpecSnapshot).filter(
            SpecSnapshot.spec_hash == normalized.spec_hash
        ).first()
        
        if existing:
            op_count = db.query(Operation).filter(Operation.spec_id == existing.id).count()
            return SpecResponse(
                id=existing.id,
                source_url=existing.source_url,
                discovered_doc_url=existing.discovered_doc_url,
                spec_hash=existing.spec_hash,
                spec_version=existing.spec_version,
                title=existing.title,
                description=existing.description,
                servers=existing.servers,
                operation_count=op_count,
                created_at=existing.created_at.isoformat(),
            )
        
        # Create new spec snapshot
        spec_snapshot = SpecSnapshot(
            source_url=request.url,
            discovered_doc_url=discovery_result.doc_url,
            spec_hash=normalized.spec_hash,
            spec_version=normalized.openapi_version,
            title=normalized.title,
            description=normalized.description,
            normalized_openapi_json=normalized.spec,
            deref_trace=discovery_result.trace,
            servers=normalized.servers,
        )
        db.add(spec_snapshot)
        db.flush()
        
        # Extract and store operations
        operations = extract_operations(normalized.spec, spec_snapshot.id)
        for op in operations:
            db.add(Operation(
                spec_id=spec_snapshot.id,
                operation_id=op.operation_id,
                method=op.method,
                path=op.path,
                tags=op.tags,
                summary=op.summary,
                description=op.description,
                server_url=op.server_url,
                security_profile=op.security,
                parameters=op.parameters,
                request_body_schema=op.request_body_schema,
                response_schemas=op.response_schemas,
                examples=op.examples,
                deprecated=op.deprecated,
            ))
        
        db.commit()
        db.refresh(spec_snapshot)
        
        return SpecResponse(
            id=spec_snapshot.id,
            source_url=spec_snapshot.source_url,
            discovered_doc_url=spec_snapshot.discovered_doc_url,
            spec_hash=spec_snapshot.spec_hash,
            spec_version=spec_snapshot.spec_version,
            title=spec_snapshot.title,
            description=spec_snapshot.description,
            servers=spec_snapshot.servers,
            operation_count=len(operations),
            created_at=spec_snapshot.created_at.isoformat(),
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to discover spec: {str(e)}",
        )


@router.get("/", response_model=SpecListResponse)
def list_specs(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List all discovered specs."""
    specs = db.query(SpecSnapshot).order_by(SpecSnapshot.created_at.desc()).offset(skip).limit(limit).all()
    total = db.query(SpecSnapshot).count()
    
    result = []
    for spec in specs:
        op_count = db.query(Operation).filter(Operation.spec_id == spec.id).count()
        result.append(SpecResponse(
            id=spec.id,
            source_url=spec.source_url,
            discovered_doc_url=spec.discovered_doc_url,
            spec_hash=spec.spec_hash,
            spec_version=spec.spec_version,
            title=spec.title,
            description=spec.description,
            servers=spec.servers,
            operation_count=op_count,
            created_at=spec.created_at.isoformat(),
        ))
    
    return SpecListResponse(specs=result, total=total)


@router.get("/{spec_id}", response_model=SpecResponse)
def get_spec(
    spec_id: str,
    db: Session = Depends(get_db),
):
    """Get a specific spec by ID."""
    spec = db.query(SpecSnapshot).filter(SpecSnapshot.id == spec_id).first()
    if not spec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spec not found",
        )
    
    op_count = db.query(Operation).filter(Operation.spec_id == spec.id).count()
    return SpecResponse(
        id=spec.id,
        source_url=spec.source_url,
        discovered_doc_url=spec.discovered_doc_url,
        spec_hash=spec.spec_hash,
        spec_version=spec.spec_version,
        title=spec.title,
        description=spec.description,
        servers=spec.servers,
        operation_count=op_count,
        created_at=spec.created_at.isoformat(),
    )


@router.get("/{spec_id}/operations", response_model=OperationListResponse)
def list_spec_operations(
    spec_id: str,
    tag: Optional[str] = None,
    method: Optional[str] = None,
    deprecated: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    List operations for a spec with filtering.
    
    Filters:
    - tag: Filter by tag name
    - method: Filter by HTTP method (GET, POST, etc.)
    - deprecated: Filter by deprecated status
    - search: Search in path, summary, operation_id
    """
    spec = db.query(SpecSnapshot).filter(SpecSnapshot.id == spec_id).first()
    if not spec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spec not found",
        )
    
    query = db.query(Operation).filter(Operation.spec_id == spec_id)
    
    if method:
        query = query.filter(Operation.method == method.upper())
    
    if deprecated is not None:
        query = query.filter(Operation.deprecated == deprecated)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Operation.path.ilike(search_term)) |
            (Operation.summary.ilike(search_term)) |
            (Operation.operation_id.ilike(search_term))
        )
    
    # Tag filtering requires JSON query (handled in Python for SQLite compatibility)
    operations = query.offset(skip).limit(limit).all()
    
    if tag:
        operations = [op for op in operations if op.tags and tag in op.tags]
    
    total = query.count()
    
    return OperationListResponse(
        operations=[
            OperationResponse(
                id=op.id,
                operation_id=op.operation_id,
                method=op.method,
                path=op.path,
                tags=op.tags,
                summary=op.summary,
                deprecated=op.deprecated,
            )
            for op in operations
        ],
        total=total,
    )


@router.delete("/{spec_id}")
def delete_spec(
    spec_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a spec and all its operations."""
    spec = db.query(SpecSnapshot).filter(SpecSnapshot.id == spec_id).first()
    if not spec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Spec not found",
        )
    
    db.delete(spec)
    db.commit()
    
    return {"status": "deleted", "id": spec_id}
