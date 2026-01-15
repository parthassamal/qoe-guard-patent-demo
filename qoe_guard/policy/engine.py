"""
Policy Evaluation Engine.

Evaluates validation results against policy rules to produce
PASS/WARN/FAIL decisions with explanations and recommendations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from .config import PolicyConfig, DEFAULT_POLICY
from ..scoring.brittleness import BrittlenessResult
from ..scoring.qoe_risk import QoERiskResult
from ..scoring.drift import DriftClassification, DriftType


@dataclass
class PolicyViolation:
    """A policy rule violation."""
    rule: str
    severity: str  # info, warning, error, critical
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class PolicyDecision:
    """Result of policy evaluation."""
    decision: str  # PASS, WARN, FAIL
    ci_gate_block: bool  # Whether to block CI/CD
    violations: List[PolicyViolation]
    recommendations: List[str]
    scores: Dict[str, float]
    policy_version: str
    details: Dict[str, Any]


def evaluate_policy(
    brittleness: Optional[BrittlenessResult] = None,
    qoe_risk: Optional[QoERiskResult] = None,
    drift: Optional[DriftClassification] = None,
    policy: Optional[PolicyConfig] = None,
    operation_id: Optional[str] = None,
    changed_paths: Optional[List[str]] = None,
) -> PolicyDecision:
    """
    Evaluate validation results against policy rules.
    
    Args:
        brittleness: Brittleness scoring result
        qoe_risk: QoE risk scoring result
        drift: Drift classification result
        policy: Policy configuration (uses default if None)
        operation_id: Operation ID (for skip checks)
        changed_paths: List of changed JSON paths (for allow-list checks)
    
    Returns:
        PolicyDecision with PASS/WARN/FAIL and explanations
    """
    if policy is None:
        policy = DEFAULT_POLICY
    
    violations: List[PolicyViolation] = []
    recommendations: List[str] = []
    scores: Dict[str, float] = {}
    
    # Check if operation should be skipped
    if operation_id and operation_id in policy.skip_operations:
        return PolicyDecision(
            decision="PASS",
            ci_gate_block=False,
            violations=[],
            recommendations=["Operation is in skip list"],
            scores={},
            policy_version=policy.version,
            details={"skipped": True, "reason": "operation_in_skip_list"},
        )
    
    # Filter allowed drift paths
    filtered_paths = changed_paths or []
    if policy.allowed_drift_paths:
        filtered_paths = [
            p for p in filtered_paths
            if not _path_in_allow_list(p, policy.allowed_drift_paths)
        ]
    
    # 1. Evaluate Brittleness
    if brittleness:
        scores["brittleness"] = brittleness.score
        
        if brittleness.score >= policy.brittleness_fail_threshold:
            violations.append(PolicyViolation(
                rule="brittleness_threshold",
                severity="error",
                message=f"Brittleness score {brittleness.score:.1f} exceeds fail threshold {policy.brittleness_fail_threshold}",
                details={
                    "score": brittleness.score,
                    "threshold": policy.brittleness_fail_threshold,
                    "contributors": [
                        {"path": c.path, "reason": c.reason, "impact": c.impact}
                        for c in brittleness.top_contributors[:3]
                    ],
                },
            ))
            recommendations.append("Reduce schema complexity or address top brittleness contributors")
        
        elif brittleness.score >= policy.brittleness_warn_threshold:
            violations.append(PolicyViolation(
                rule="brittleness_threshold",
                severity="warning",
                message=f"Brittleness score {brittleness.score:.1f} exceeds warn threshold {policy.brittleness_warn_threshold}",
                details={"score": brittleness.score, "threshold": policy.brittleness_warn_threshold},
            ))
            recommendations.append("Consider simplifying API contract")
    
    # 2. Evaluate QoE Risk
    if qoe_risk:
        scores["qoe_risk"] = qoe_risk.risk_score
        
        if qoe_risk.risk_score >= policy.qoe_fail_threshold:
            violations.append(PolicyViolation(
                rule="qoe_risk_threshold",
                severity="error",
                message=f"QoE risk score {qoe_risk.risk_score:.4f} exceeds fail threshold {policy.qoe_fail_threshold}",
                details={
                    "score": qoe_risk.risk_score,
                    "threshold": policy.qoe_fail_threshold,
                    "top_signals": [
                        {"path": s.path, "type": s.signal_type, "criticality": s.criticality}
                        for s in qoe_risk.top_signals[:3]
                    ],
                },
            ))
            recommendations.append("Review changes to critical paths")
        
        elif qoe_risk.risk_score >= policy.qoe_warn_threshold:
            violations.append(PolicyViolation(
                rule="qoe_risk_threshold",
                severity="warning",
                message=f"QoE risk score {qoe_risk.risk_score:.4f} exceeds warn threshold {policy.qoe_warn_threshold}",
                details={"score": qoe_risk.risk_score, "threshold": policy.qoe_warn_threshold},
            ))
            recommendations.append("Verify QoE-impacting changes are intentional")
        
        # Check critical type changes override
        if (policy.fail_on_critical_type_changes and 
            qoe_risk.critical_type_changes >= policy.critical_type_change_threshold):
            violations.append(PolicyViolation(
                rule="critical_type_changes",
                severity="critical",
                message=f"Detected {qoe_risk.critical_type_changes} type changes on critical paths",
                details={"count": qoe_risk.critical_type_changes},
            ))
            recommendations.append("Type changes on critical paths are high-risk; ensure backward compatibility")
    
    # 3. Evaluate Drift
    if drift:
        scores["drift_severity"] = {"critical": 1.0, "high": 0.75, "medium": 0.5, "low": 0.25}.get(drift.severity, 0)
        
        if drift.drift_type == DriftType.UNDOCUMENTED and policy.fail_on_undocumented_drift:
            violations.append(PolicyViolation(
                rule="undocumented_drift",
                severity="critical",
                message="Undocumented runtime drift detected on critical paths",
                details={
                    "critical_mismatches": drift.critical_mismatches,
                    "total_mismatches": drift.runtime_mismatches,
                },
            ))
            recommendations.extend(drift.recommendations)
        
        elif drift.drift_type == DriftType.SPEC_DRIFT and policy.warn_on_spec_drift:
            violations.append(PolicyViolation(
                rule="spec_drift",
                severity="warning",
                message="OpenAPI specification has changed",
                details={"spec_changed": drift.spec_changed},
            ))
            recommendations.append("Update baselines to reflect spec changes")
        
        elif drift.drift_type == DriftType.RUNTIME_DRIFT:
            violations.append(PolicyViolation(
                rule="runtime_drift",
                severity="warning",
                message=f"Runtime drift detected: {drift.runtime_mismatches} schema mismatches",
                details={"runtime_mismatches": drift.runtime_mismatches},
            ))
            recommendations.append("Investigate runtime behavior changes")
    
    # Determine final decision
    decision = _compute_decision(violations)
    
    # Determine CI gate behavior
    ci_gate_block = False
    if decision == "FAIL" and policy.ci_hard_gate:
        ci_gate_block = True
    elif decision == "WARN" and policy.require_approval_on_warn:
        ci_gate_block = True
    
    return PolicyDecision(
        decision=decision,
        ci_gate_block=ci_gate_block,
        violations=violations,
        recommendations=list(set(recommendations)),  # Dedupe
        scores=scores,
        policy_version=policy.version,
        details={
            "brittleness": brittleness.signals if brittleness else None,
            "qoe_risk": qoe_risk.reasons if qoe_risk else None,
            "drift": {
                "type": drift.drift_type.value if drift else None,
                "evidence_count": len(drift.evidence) if drift else 0,
            } if drift else None,
            "policy_applied": {
                "name": policy.name,
                "version": policy.version,
                "hard_gate": policy.ci_hard_gate,
            },
        },
    )


def _compute_decision(violations: List[PolicyViolation]) -> str:
    """Compute final decision based on violation severities."""
    if any(v.severity in ("critical", "error") for v in violations):
        return "FAIL"
    elif any(v.severity == "warning" for v in violations):
        return "WARN"
    else:
        return "PASS"


def _path_in_allow_list(path: str, allow_list: List[str]) -> bool:
    """Check if a path matches any pattern in the allow list."""
    for pattern in allow_list:
        if pattern == path:
            return True
        if pattern.endswith("*") and path.startswith(pattern[:-1]):
            return True
        if pattern.startswith("*") and path.endswith(pattern[1:]):
            return True
    return False


def format_decision_for_ci(decision: PolicyDecision) -> str:
    """Format decision for CI output (e.g., GitHub Actions)."""
    lines = []
    
    if decision.decision == "PASS":
        lines.append("✅ QoE-Guard: PASS")
    elif decision.decision == "WARN":
        lines.append("⚠️ QoE-Guard: WARN")
    else:
        lines.append("❌ QoE-Guard: FAIL")
    
    lines.append("")
    
    # Scores
    lines.append("**Scores:**")
    for name, value in decision.scores.items():
        lines.append(f"- {name}: {value:.4f}" if isinstance(value, float) else f"- {name}: {value}")
    
    # Violations
    if decision.violations:
        lines.append("")
        lines.append("**Violations:**")
        for v in decision.violations:
            icon = {"critical": "🚨", "error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(v.severity, "•")
            lines.append(f"{icon} [{v.rule}] {v.message}")
    
    # Recommendations
    if decision.recommendations:
        lines.append("")
        lines.append("**Recommendations:**")
        for rec in decision.recommendations[:5]:
            lines.append(f"- {rec}")
    
    return "\n".join(lines)
