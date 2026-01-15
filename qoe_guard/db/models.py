"""
SQLAlchemy models for QoE-Guard Enterprise.

Core entities:
- User, Role: Authentication and authorization
- SpecSnapshot: OpenAPI spec versions
- Operation: Extracted API operations
- Scenario: Generated test scenarios
- ValidationRun, OperationResult: Validation execution
- BaselinePromotion, PromotionRequest: Governance workflow
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    Enum,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship

from .database import Base


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class Role(enum.Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    APPROVER = "approver"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class DecisionType(enum.Enum):
    """Validation decision types."""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class DriftType(enum.Enum):
    """Drift classification types."""
    NONE = "none"
    SPEC_DRIFT = "spec_drift"
    RUNTIME_DRIFT = "runtime_drift"
    UNDOCUMENTED = "undocumented"


class PromotionStatus(enum.Enum):
    """Baseline promotion request status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class User(Base):
    """User account for authentication and authorization."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    role = Column(Enum(Role), default=Role.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    validation_runs = relationship("ValidationRun", back_populates="created_by_user")
    promotion_requests = relationship("PromotionRequest", back_populates="requester", foreign_keys="PromotionRequest.requester_id")
    approved_promotions = relationship("BaselinePromotion", back_populates="approver")


class SpecSnapshot(Base):
    """Snapshot of an OpenAPI/Swagger specification."""
    __tablename__ = "spec_snapshots"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_url = Column(String(2048), nullable=False)
    discovered_doc_url = Column(String(2048), nullable=True)
    spec_hash = Column(String(64), nullable=False, index=True)
    spec_version = Column(String(50), nullable=True)  # OpenAPI version
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    normalized_openapi_json = Column(JSON, nullable=False)
    deref_trace = Column(JSON, nullable=True)  # $ref resolution trace
    servers = Column(JSON, nullable=True)  # List of server URLs
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    operations = relationship("Operation", back_populates="spec", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_spec_snapshots_source_hash", "source_url", "spec_hash"),
    )


class Operation(Base):
    """Extracted API operation from a spec."""
    __tablename__ = "operations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    spec_id = Column(String(36), ForeignKey("spec_snapshots.id", ondelete="CASCADE"), nullable=False, index=True)
    operation_id = Column(String(255), nullable=True)  # operationId from spec
    method = Column(String(10), nullable=False)  # GET, POST, etc.
    path = Column(String(2048), nullable=False)
    tags = Column(JSON, nullable=True)  # List of tags
    summary = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    server_url = Column(String(2048), nullable=True)
    security_profile = Column(JSON, nullable=True)
    parameters = Column(JSON, nullable=True)  # List of parameters
    request_body_schema = Column(JSON, nullable=True)
    response_schemas = Column(JSON, nullable=True)  # Dict of status_code -> schema
    examples = Column(JSON, nullable=True)
    deprecated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    spec = relationship("SpecSnapshot", back_populates="operations")
    scenarios = relationship("Scenario", back_populates="operation", cascade="all, delete-orphan")
    results = relationship("OperationResult", back_populates="operation")

    __table_args__ = (
        Index("ix_operations_spec_method_path", "spec_id", "method", "path"),
    )


class Scenario(Base):
    """Generated test scenario for an operation."""
    __tablename__ = "scenarios"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    operation_id = Column(String(36), ForeignKey("operations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    request_template = Column(JSON, nullable=False)  # URL, method, params
    headers_template = Column(JSON, nullable=True)
    body_template = Column(JSON, nullable=True)
    auth_requirements = Column(JSON, nullable=True)
    environment = Column(String(50), default="default")  # dev/stage/prod
    baseline_response = Column(JSON, nullable=True)
    baseline_response_hash = Column(String(64), nullable=True)
    baseline_schema_hash = Column(String(64), nullable=True)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    operation = relationship("Operation", back_populates="scenarios")
    promotion_requests = relationship("PromotionRequest", back_populates="scenario")


class ValidationRun(Base):
    """A validation run execution."""
    __tablename__ = "validation_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    spec_id = Column(String(36), ForeignKey("spec_snapshots.id"), nullable=True, index=True)
    spec_hash = Column(String(64), nullable=True)
    selected_operations = Column(JSON, nullable=True)  # List of operation IDs
    environment = Column(String(50), default="default")
    auth_mode = Column(String(50), nullable=True)
    
    # Aggregate scores
    brittleness_score = Column(Float, nullable=True)
    qoe_risk_score = Column(Float, nullable=True)
    drift_type = Column(Enum(DriftType), default=DriftType.NONE)
    decision = Column(Enum(DecisionType), nullable=True)
    
    # Details
    policy_version = Column(String(50), nullable=True)
    model_version = Column(String(50), nullable=True)
    reasons = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    
    # Metadata
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # Relationships
    created_by_user = relationship("User", back_populates="validation_runs")
    operation_results = relationship("OperationResult", back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_validation_runs_created", "created_by_id", "started_at"),
    )


class OperationResult(Base):
    """Result of validating a single operation within a run."""
    __tablename__ = "operation_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_id = Column(String(36), ForeignKey("validation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    operation_id = Column(String(36), ForeignKey("operations.id"), nullable=True)
    scenario_id = Column(String(36), ForeignKey("scenarios.id"), nullable=True)
    
    # Request/Response
    request_url = Column(String(2048), nullable=True)
    request_method = Column(String(10), nullable=True)
    request_headers = Column(JSON, nullable=True)  # Redacted
    request_body = Column(JSON, nullable=True)
    status_code = Column(Integer, nullable=True)
    response_headers = Column(JSON, nullable=True)
    response_body = Column(JSON, nullable=True)
    
    # Timings
    response_time_ms = Column(Float, nullable=True)
    connect_time_ms = Column(Float, nullable=True)
    tls_time_ms = Column(Float, nullable=True)
    
    # Validation results
    conformance_status = Column(String(20), nullable=True)  # pass/fail/error
    schema_mismatches = Column(JSON, nullable=True)  # List of mismatch paths
    error_message = Column(Text, nullable=True)
    
    # Scores contribution
    brittleness_contribution = Column(Float, nullable=True)
    qoe_contribution = Column(Float, nullable=True)
    drift_signals = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    run = relationship("ValidationRun", back_populates="operation_results")
    operation = relationship("Operation", back_populates="results")


class PromotionRequest(Base):
    """Request to promote a new baseline."""
    __tablename__ = "promotion_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    scenario_id = Column(String(36), ForeignKey("scenarios.id"), nullable=False, index=True)
    requester_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Baseline details
    new_baseline = Column(JSON, nullable=False)
    new_baseline_hash = Column(String(64), nullable=False)
    prior_baseline_hash = Column(String(64), nullable=True)
    
    # Request details
    justification = Column(Text, nullable=True)
    status = Column(Enum(PromotionStatus), default=PromotionStatus.PENDING)
    
    # Eligibility check results
    stable_runs_count = Column(Integer, nullable=True)
    qoe_degradation_check = Column(Boolean, nullable=True)
    eligibility_details = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    scenario = relationship("Scenario", back_populates="promotion_requests")
    requester = relationship("User", back_populates="promotion_requests", foreign_keys=[requester_id])
    promotion = relationship("BaselinePromotion", back_populates="request", uselist=False)


class BaselinePromotion(Base):
    """Approved baseline promotion record."""
    __tablename__ = "baseline_promotions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    request_id = Column(String(36), ForeignKey("promotion_requests.id"), nullable=False, unique=True)
    scenario_id = Column(String(36), ForeignKey("scenarios.id"), nullable=False, index=True)
    approver_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    # Action details
    action_type = Column(String(20), nullable=False)  # approve/reject/rollback
    prior_hash = Column(String(64), nullable=True)
    new_hash = Column(String(64), nullable=False)
    
    # Versioning
    policy_version = Column(String(50), nullable=True)
    model_version = Column(String(50), nullable=True)
    scenario_version = Column(Integer, nullable=False)
    
    # Audit
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    request = relationship("PromotionRequest", back_populates="promotion")
    approver = relationship("User", back_populates="approved_promotions")


class PolicyConfig(Base):
    """Policy configuration for validation gating."""
    __tablename__ = "policy_configs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False)
    version = Column(String(50), nullable=False)
    
    # Thresholds
    brittleness_fail_threshold = Column(Float, default=75.0)
    brittleness_warn_threshold = Column(Float, default=50.0)
    qoe_fail_threshold = Column(Float, default=0.72)
    qoe_warn_threshold = Column(Float, default=0.45)
    
    # Override rules
    fail_on_critical_type_changes = Column(Boolean, default=True)
    fail_on_undocumented_drift = Column(Boolean, default=True)
    warn_on_spec_drift = Column(Boolean, default=True)
    
    # Allow-lists
    allowed_drift_paths = Column(JSON, nullable=True)
    skip_operations = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CriticalityProfile(Base):
    """Criticality weights for QoE-aware scoring."""
    __tablename__ = "criticality_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)  # Tag or path pattern
    profile_type = Column(String(20), nullable=False)  # "tag" or "path"
    weight = Column(Float, nullable=False, default=0.5)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_criticality_profiles_type_name", "profile_type", "name"),
    )


class AuditLog(Base):
    """Audit trail for all significant actions."""
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)  # e.g., "baseline.promote", "policy.update"
    resource_type = Column(String(50), nullable=False)  # e.g., "scenario", "policy"
    resource_id = Column(String(36), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("ix_audit_logs_action_resource", "action", "resource_type", "resource_id"),
    )
