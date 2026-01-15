"""
Baseline Governance Manager.

Handles baseline promotion workflow:
- Request promotion with justification
- Check eligibility (stable runs, QoE non-degradation)
- Approve/reject with audit trail
- Rollback capabilities
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session

from ..db.models import (
    User, Scenario, ValidationRun, PromotionRequest, BaselinePromotion,
    PromotionStatus, DecisionType,
)
from ..policy.config import PolicyConfig, DEFAULT_POLICY


@dataclass
class EligibilityResult:
    """Result of promotion eligibility check."""
    eligible: bool
    stable_runs_count: int
    required_stable_runs: int
    qoe_degradation: Optional[float]
    max_degradation: float
    reasons: List[str]


@dataclass
class PromotionResult:
    """Result of a promotion action."""
    success: bool
    action: str  # approve, reject, rollback
    scenario_id: str
    new_version: Optional[int]
    message: str


class BaselineManager:
    """Manages baseline promotion workflow."""
    
    def __init__(self, db: Session, policy: Optional[PolicyConfig] = None):
        self.db = db
        self.policy = policy or DEFAULT_POLICY
    
    def check_eligibility(
        self,
        scenario_id: str,
        new_baseline: Dict[str, Any],
    ) -> EligibilityResult:
        """
        Check if a new baseline is eligible for promotion.
        
        Requirements:
        1. Minimum number of stable validation runs
        2. No QoE degradation (or within threshold)
        3. No pending promotion requests
        """
        reasons = []
        
        # Get scenario
        scenario = self.db.query(Scenario).filter(Scenario.id == scenario_id).first()
        if not scenario:
            return EligibilityResult(
                eligible=False,
                stable_runs_count=0,
                required_stable_runs=self.policy.min_stable_runs_for_promotion,
                qoe_degradation=None,
                max_degradation=self.policy.max_qoe_degradation_for_promotion,
                reasons=["Scenario not found"],
            )
        
        # Check for pending requests
        pending = self.db.query(PromotionRequest).filter(
            PromotionRequest.scenario_id == scenario_id,
            PromotionRequest.status == PromotionStatus.PENDING,
        ).first()
        
        if pending:
            reasons.append(f"Pending promotion request exists (ID: {pending.id})")
        
        # Count stable runs with PASS decision
        stable_runs = self.db.query(ValidationRun).filter(
            ValidationRun.decision == DecisionType.PASS,
        ).order_by(ValidationRun.started_at.desc()).limit(
            self.policy.min_stable_runs_for_promotion * 2
        ).all()
        
        stable_count = len(stable_runs)
        
        if stable_count < self.policy.min_stable_runs_for_promotion:
            reasons.append(
                f"Insufficient stable runs: {stable_count}/{self.policy.min_stable_runs_for_promotion}"
            )
        
        # Check QoE degradation
        qoe_degradation = None
        if stable_runs:
            recent_scores = [r.qoe_risk_score for r in stable_runs if r.qoe_risk_score is not None]
            if recent_scores:
                avg_recent = sum(recent_scores) / len(recent_scores)
                
                # Compare with older runs
                older_runs = self.db.query(ValidationRun).filter(
                    ValidationRun.decision == DecisionType.PASS,
                ).order_by(ValidationRun.started_at.asc()).limit(5).all()
                
                older_scores = [r.qoe_risk_score for r in older_runs if r.qoe_risk_score is not None]
                if older_scores:
                    avg_older = sum(older_scores) / len(older_scores)
                    qoe_degradation = avg_recent - avg_older
                    
                    if qoe_degradation > self.policy.max_qoe_degradation_for_promotion:
                        reasons.append(
                            f"QoE degradation {qoe_degradation:.4f} exceeds threshold {self.policy.max_qoe_degradation_for_promotion}"
                        )
        
        eligible = len(reasons) == 0 or (len(reasons) == 1 and pending is None)
        
        return EligibilityResult(
            eligible=eligible and pending is None,
            stable_runs_count=stable_count,
            required_stable_runs=self.policy.min_stable_runs_for_promotion,
            qoe_degradation=qoe_degradation,
            max_degradation=self.policy.max_qoe_degradation_for_promotion,
            reasons=reasons if reasons else ["All eligibility checks passed"],
        )
    
    def request_promotion(
        self,
        scenario_id: str,
        new_baseline: Dict[str, Any],
        requester: User,
        justification: Optional[str] = None,
    ) -> PromotionRequest:
        """
        Create a promotion request.
        
        Args:
            scenario_id: Scenario to update
            new_baseline: New baseline response JSON
            requester: User requesting promotion
            justification: Reason for promotion
        
        Returns:
            Created PromotionRequest
        """
        # Get scenario
        scenario = self.db.query(Scenario).filter(Scenario.id == scenario_id).first()
        if not scenario:
            raise ValueError("Scenario not found")
        
        # Check eligibility
        eligibility = self.check_eligibility(scenario_id, new_baseline)
        
        # Compute baseline hash
        baseline_hash = hashlib.sha256(
            json.dumps(new_baseline, sort_keys=True).encode()
        ).hexdigest()
        
        # Create request
        request = PromotionRequest(
            scenario_id=scenario_id,
            requester_id=requester.id,
            new_baseline=new_baseline,
            new_baseline_hash=baseline_hash,
            prior_baseline_hash=scenario.baseline_response_hash,
            justification=justification,
            stable_runs_count=eligibility.stable_runs_count,
            qoe_degradation_check=eligibility.qoe_degradation is None or eligibility.qoe_degradation <= self.policy.max_qoe_degradation_for_promotion,
            eligibility_details={
                "eligible": eligibility.eligible,
                "reasons": eligibility.reasons,
                "qoe_degradation": eligibility.qoe_degradation,
            },
        )
        
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        
        return request
    
    def approve_promotion(
        self,
        request_id: str,
        approver: User,
        reason: Optional[str] = None,
    ) -> PromotionResult:
        """
        Approve a promotion request.
        
        Updates the scenario baseline and creates audit record.
        """
        request = self.db.query(PromotionRequest).filter(
            PromotionRequest.id == request_id
        ).first()
        
        if not request:
            return PromotionResult(
                success=False,
                action="approve",
                scenario_id="",
                new_version=None,
                message="Promotion request not found",
            )
        
        if request.status != PromotionStatus.PENDING:
            return PromotionResult(
                success=False,
                action="approve",
                scenario_id=request.scenario_id,
                new_version=None,
                message=f"Request is already {request.status.value}",
            )
        
        if request.requester_id == approver.id:
            return PromotionResult(
                success=False,
                action="approve",
                scenario_id=request.scenario_id,
                new_version=None,
                message="Cannot approve your own request",
            )
        
        # Update scenario
        scenario = self.db.query(Scenario).filter(
            Scenario.id == request.scenario_id
        ).first()
        
        scenario.baseline_response = request.new_baseline
        scenario.baseline_response_hash = request.new_baseline_hash
        scenario.version += 1
        
        # Update request status
        request.status = PromotionStatus.APPROVED
        
        # Create promotion record
        promotion = BaselinePromotion(
            request_id=request.id,
            scenario_id=request.scenario_id,
            approver_id=approver.id,
            action_type="approve",
            prior_hash=request.prior_baseline_hash,
            new_hash=request.new_baseline_hash,
            policy_version=self.policy.version,
            scenario_version=scenario.version,
            reason=reason,
        )
        self.db.add(promotion)
        
        self.db.commit()
        
        return PromotionResult(
            success=True,
            action="approve",
            scenario_id=request.scenario_id,
            new_version=scenario.version,
            message=f"Baseline promoted to version {scenario.version}",
        )
    
    def reject_promotion(
        self,
        request_id: str,
        approver: User,
        reason: Optional[str] = None,
    ) -> PromotionResult:
        """Reject a promotion request."""
        request = self.db.query(PromotionRequest).filter(
            PromotionRequest.id == request_id
        ).first()
        
        if not request:
            return PromotionResult(
                success=False,
                action="reject",
                scenario_id="",
                new_version=None,
                message="Promotion request not found",
            )
        
        if request.status != PromotionStatus.PENDING:
            return PromotionResult(
                success=False,
                action="reject",
                scenario_id=request.scenario_id,
                new_version=None,
                message=f"Request is already {request.status.value}",
            )
        
        # Update request status
        request.status = PromotionStatus.REJECTED
        
        self.db.commit()
        
        return PromotionResult(
            success=True,
            action="reject",
            scenario_id=request.scenario_id,
            new_version=None,
            message=f"Promotion request rejected: {reason or 'No reason provided'}",
        )
    
    def rollback_baseline(
        self,
        scenario_id: str,
        target_version: int,
        actor: User,
        reason: Optional[str] = None,
    ) -> PromotionResult:
        """
        Rollback a scenario to a previous version.
        
        This creates a new promotion record with action_type "rollback".
        """
        # Find the promotion record for the target version
        target_promotion = self.db.query(BaselinePromotion).filter(
            BaselinePromotion.scenario_id == scenario_id,
            BaselinePromotion.scenario_version == target_version,
        ).first()
        
        if not target_promotion:
            return PromotionResult(
                success=False,
                action="rollback",
                scenario_id=scenario_id,
                new_version=None,
                message=f"Version {target_version} not found in history",
            )
        
        # Get current scenario
        scenario = self.db.query(Scenario).filter(Scenario.id == scenario_id).first()
        if not scenario:
            return PromotionResult(
                success=False,
                action="rollback",
                scenario_id=scenario_id,
                new_version=None,
                message="Scenario not found",
            )
        
        # Get the baseline from that version's request
        target_request = self.db.query(PromotionRequest).filter(
            PromotionRequest.id == target_promotion.request_id
        ).first()
        
        if not target_request:
            return PromotionResult(
                success=False,
                action="rollback",
                scenario_id=scenario_id,
                new_version=None,
                message="Cannot find baseline for target version",
            )
        
        # Update scenario
        prior_hash = scenario.baseline_response_hash
        scenario.baseline_response = target_request.new_baseline
        scenario.baseline_response_hash = target_request.new_baseline_hash
        scenario.version += 1
        
        # Create rollback promotion record
        rollback = BaselinePromotion(
            request_id=target_request.id,
            scenario_id=scenario_id,
            approver_id=actor.id,
            action_type="rollback",
            prior_hash=prior_hash,
            new_hash=target_request.new_baseline_hash,
            policy_version=self.policy.version,
            scenario_version=scenario.version,
            reason=reason or f"Rollback to version {target_version}",
        )
        self.db.add(rollback)
        
        self.db.commit()
        
        return PromotionResult(
            success=True,
            action="rollback",
            scenario_id=scenario_id,
            new_version=scenario.version,
            message=f"Rolled back to version {target_version} (new version: {scenario.version})",
        )
    
    def get_promotion_history(
        self,
        scenario_id: str,
        limit: int = 20,
    ) -> List[BaselinePromotion]:
        """Get promotion history for a scenario."""
        return self.db.query(BaselinePromotion).filter(
            BaselinePromotion.scenario_id == scenario_id
        ).order_by(BaselinePromotion.created_at.desc()).limit(limit).all()
