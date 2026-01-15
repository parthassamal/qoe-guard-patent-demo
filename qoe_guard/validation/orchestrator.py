"""
Validation Orchestrator.

Manages validation job execution with:
- Concurrency control
- Rate limiting
- Result aggregation
- Score computation
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict

from sqlalchemy.orm import Session

from ..db.models import (
    ValidationRun, OperationResult, Operation, Scenario,
    DecisionType, DriftType,
)
from .runner import RuntimeRunner, RuntimeResult, redact_headers
from .conformance import validate_response, ConformanceResult
from ..scoring.brittleness import compute_brittleness_score, BrittlenessResult
from ..scoring.qoe_risk import compute_qoe_risk, QoERiskResult
from ..scoring.drift import classify_drift, DriftClassification
from ..scoring.criticality import DEFAULT_CRITICALITY_PROFILES, get_criticality_weight
from ..policy.engine import evaluate_policy, PolicyDecision
from ..policy.config import DEFAULT_POLICY


@dataclass
class ValidationJobConfig:
    """Configuration for a validation job."""
    concurrency: int = 5
    rate_limit_per_host: int = 10  # requests per second
    safe_methods_only: bool = True
    timeout: int = 30
    retry_count: int = 1
    retry_delay: float = 1.0


class RateLimiter:
    """Simple rate limiter per host."""
    
    def __init__(self, rate: int = 10):
        self.rate = rate
        self.tokens = defaultdict(lambda: rate)
        self.last_update = defaultdict(time.time)
    
    async def acquire(self, host: str):
        """Wait until a request can be made to the host."""
        while True:
            now = time.time()
            elapsed = now - self.last_update[host]
            
            # Refill tokens
            self.tokens[host] = min(
                self.rate,
                self.tokens[host] + elapsed * self.rate
            )
            self.last_update[host] = now
            
            if self.tokens[host] >= 1:
                self.tokens[host] -= 1
                return
            
            await asyncio.sleep(0.1)


class ValidationOrchestrator:
    """Orchestrates validation job execution."""
    
    def __init__(
        self,
        db: Session,
        config: Optional[ValidationJobConfig] = None,
    ):
        self.db = db
        self.config = config or ValidationJobConfig()
        self.rate_limiter = RateLimiter(self.config.rate_limit_per_host)
    
    async def execute(
        self,
        run_id: str,
        auth_config: Optional[Dict[str, str]] = None,
        concurrency: Optional[int] = None,
        rate_limit_per_host: Optional[int] = None,
        safe_methods_only: Optional[bool] = None,
    ):
        """
        Execute a validation run.
        
        Args:
            run_id: ID of the ValidationRun to execute
            auth_config: Authentication configuration
            concurrency: Override concurrency
            rate_limit_per_host: Override rate limit
            safe_methods_only: Override safe methods only
        """
        start_time = time.time()
        
        # Get run record
        run = self.db.query(ValidationRun).filter(ValidationRun.id == run_id).first()
        if not run:
            return
        
        # Get operations to validate
        operation_ids = run.selected_operations or []
        operations = self.db.query(Operation).filter(
            Operation.id.in_(operation_ids)
        ).all()
        
        if not operations:
            run.completed_at = datetime.utcnow()
            run.decision = DecisionType.PASS
            run.duration_ms = int((time.time() - start_time) * 1000)
            self.db.commit()
            return
        
        # Apply config overrides
        concurrency = concurrency or self.config.concurrency
        safe_methods = safe_methods_only if safe_methods_only is not None else self.config.safe_methods_only
        
        # Filter to safe methods if required
        if safe_methods:
            operations = [op for op in operations if op.method in ["GET", "HEAD", "OPTIONS"]]
        
        # Execute operations with concurrency control
        semaphore = asyncio.Semaphore(concurrency)
        results = []
        
        async def run_operation(operation: Operation):
            async with semaphore:
                result = await self._execute_operation(
                    operation,
                    auth_config,
                    run.environment,
                )
                results.append((operation, result))
        
        # Run all operations
        tasks = [run_operation(op) for op in operations]
        await asyncio.gather(*tasks)
        
        # Process results
        all_changes = []
        brittleness_scores = []
        runtime_results = []
        
        for operation, result in results:
            # Store operation result
            op_result = self._create_operation_result(run, operation, result)
            self.db.add(op_result)
            
            # Collect data for scoring
            if result.conformance:
                for mismatch in result.conformance.mismatches:
                    all_changes.append({
                        "path": mismatch.path,
                        "change_type": "value_changed",
                        "before": None,
                        "after": mismatch.value,
                    })
            
            runtime_results.append({
                "status_code": result.runtime.status_code if result.runtime else None,
                "response_time_ms": result.runtime.response_time_ms if result.runtime else None,
                "error": result.runtime.error if result.runtime else None,
                "schema_mismatches": result.conformance.mismatches if result.conformance else [],
            })
        
        # Compute aggregate scores
        brittleness = compute_brittleness_score(
            runtime_results=runtime_results,
            tag_criticality=0.5,
            environment=run.environment,
        )
        
        qoe_risk = compute_qoe_risk(
            changes=all_changes,
            profiles=DEFAULT_CRITICALITY_PROFILES,
        )
        
        drift = classify_drift(
            current_spec_hash=run.spec_hash,
            previous_spec_hash=None,  # TODO: Get previous spec hash
            schema_mismatches=[
                {"path": m.path, "message": m.message}
                for r in results
                if r[1].conformance
                for m in r[1].conformance.mismatches
            ],
        )
        
        # Evaluate policy
        policy_decision = evaluate_policy(
            brittleness=brittleness,
            qoe_risk=qoe_risk,
            drift=drift,
            policy=DEFAULT_POLICY,
        )
        
        # Update run record
        run.brittleness_score = brittleness.score
        run.qoe_risk_score = qoe_risk.risk_score
        run.drift_type = DriftType(drift.drift_type.value)
        run.decision = DecisionType(policy_decision.decision.lower())
        run.reasons = {
            "brittleness": brittleness.signals,
            "qoe_risk": qoe_risk.reasons,
            "drift": {
                "type": drift.drift_type.value,
                "severity": drift.severity,
            },
            "policy": policy_decision.details,
        }
        run.recommendations = policy_decision.recommendations
        run.policy_version = DEFAULT_POLICY.version
        run.completed_at = datetime.utcnow()
        run.duration_ms = int((time.time() - start_time) * 1000)
        
        self.db.commit()
    
    async def _execute_operation(
        self,
        operation: Operation,
        auth_config: Optional[Dict[str, str]],
        environment: str,
    ) -> "OperationExecutionResult":
        """Execute a single operation."""
        from urllib.parse import urlparse
        
        # Build request URL
        base_url = operation.server_url or "http://localhost"
        url = f"{base_url.rstrip('/')}{operation.path}"
        
        # Parse host for rate limiting
        host = urlparse(url).netloc
        await self.rate_limiter.acquire(host)
        
        # Build headers
        headers = {}
        if auth_config:
            headers.update(auth_config)
        
        # Execute request
        runner = RuntimeRunner(timeout=self.config.timeout)
        try:
            runtime_result = runner.execute(
                method=operation.method,
                url=url,
                headers=headers,
            )
        finally:
            runner.close()
        
        # Validate response
        conformance_result = None
        if runtime_result.success and runtime_result.body is not None:
            if operation.response_schemas:
                conformance_result = validate_response(
                    response_body=runtime_result.body,
                    schema={},
                    status_code=runtime_result.status_code,
                    response_schemas=operation.response_schemas,
                )
        
        return OperationExecutionResult(
            runtime=runtime_result,
            conformance=conformance_result,
        )
    
    def _create_operation_result(
        self,
        run: ValidationRun,
        operation: Operation,
        result: "OperationExecutionResult",
    ) -> OperationResult:
        """Create an OperationResult record."""
        runtime = result.runtime
        conformance = result.conformance
        
        # Determine conformance status
        conformance_status = "pass"
        if not runtime.success:
            conformance_status = "error"
        elif conformance and not conformance.valid:
            conformance_status = "fail"
        
        return OperationResult(
            run_id=run.id,
            operation_id=operation.id,
            request_url=f"{operation.server_url or ''}{operation.path}",
            request_method=operation.method,
            request_headers=redact_headers({}),  # Already redacted
            status_code=runtime.status_code,
            response_headers=runtime.headers,
            response_body=runtime.body,
            response_time_ms=runtime.response_time_ms,
            conformance_status=conformance_status,
            schema_mismatches=[
                {"path": m.path, "message": m.message}
                for m in (conformance.mismatches if conformance else [])
            ],
            error_message=runtime.error,
        )


@dataclass
class OperationExecutionResult:
    """Result of executing a single operation."""
    runtime: RuntimeResult
    conformance: Optional[ConformanceResult] = None
