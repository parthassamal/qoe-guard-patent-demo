"""
QoE Risk Scoring Module.

Computes Quality of Experience risk score (0.0-1.0) based on
changes to critical API paths and runtime degradation signals.
"""
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
import math


@dataclass
class QoERiskResult:
    """Result of QoE risk calculation."""
    score: float
    action: str  # PASS, WARN, FAIL
    top_signals: List[Tuple[str, float]] = field(default_factory=list)


# Default thresholds
QOE_THRESHOLDS = {
    "fail": 0.72,
    "warn": 0.45,
}


def compute_qoe_risk(
    changes_count: int = 0,
    critical_changes: int = 0,
    type_changes: int = 0,
    removed_fields: int = 0,
    criticality_weighted_sum: float = 0.0,
    latency_degradation: float = 0.0,
    error_rate_increase: float = 0.0,
) -> float:
    """
    Compute QoE risk score from change and runtime signals.
    
    Args:
        changes_count: Total number of changes detected
        critical_changes: Number of changes to critical paths
        type_changes: Number of type changes (breaking)
        removed_fields: Number of removed fields
        criticality_weighted_sum: Sum of (change_weight * path_criticality)
        latency_degradation: Percentage increase in latency
        error_rate_increase: Percentage increase in error rate
        
    Returns:
        QoE risk score from 0.0 to 1.0
    """
    # Base score from change signals
    change_score = 0.0
    
    # Critical changes have highest impact
    change_score += min(critical_changes * 0.15, 0.45)
    
    # Type changes are breaking
    change_score += min(type_changes * 0.12, 0.25)
    
    # Removed fields break consumers
    change_score += min(removed_fields * 0.08, 0.20)
    
    # General changes (less impactful)
    non_critical = max(0, changes_count - critical_changes - type_changes - removed_fields)
    change_score += min(non_critical * 0.02, 0.10)
    
    # Add criticality-weighted component
    change_score += min(criticality_weighted_sum * 0.3, 0.30)
    
    # Runtime degradation signals
    runtime_score = 0.0
    runtime_score += min(latency_degradation / 100, 0.15)  # 100% increase = 0.15
    runtime_score += min(error_rate_increase / 50, 0.20)    # 50% increase = 0.20
    
    # Combine scores with diminishing returns
    total_score = change_score + runtime_score * (1 - change_score * 0.5)
    
    return min(max(total_score, 0.0), 1.0)


def compute_qoe_action(score: float, thresholds: Optional[Dict[str, float]] = None) -> str:
    """
    Determine action based on QoE risk score.
    
    Args:
        score: QoE risk score (0.0-1.0)
        thresholds: Optional custom thresholds
        
    Returns:
        "PASS", "WARN", or "FAIL"
    """
    t = thresholds or QOE_THRESHOLDS
    
    if score >= t.get("fail", 0.72):
        return "FAIL"
    elif score >= t.get("warn", 0.45):
        return "WARN"
    else:
        return "PASS"


def assess_qoe_risk(
    changes_count: int = 0,
    critical_changes: int = 0,
    type_changes: int = 0,
    removed_fields: int = 0,
    criticality_weighted_sum: float = 0.0,
    latency_degradation: float = 0.0,
    error_rate_increase: float = 0.0,
) -> QoERiskResult:
    """
    Full QoE risk assessment with score and action.
    
    Returns:
        QoERiskResult with score, action, and top contributing signals
    """
    score = compute_qoe_risk(
        changes_count=changes_count,
        critical_changes=critical_changes,
        type_changes=type_changes,
        removed_fields=removed_fields,
        criticality_weighted_sum=criticality_weighted_sum,
        latency_degradation=latency_degradation,
        error_rate_increase=error_rate_increase,
    )
    
    action = compute_qoe_action(score)
    
    # Build signal contributions
    top_signals = []
    if critical_changes > 0:
        top_signals.append(("critical_changes", critical_changes * 0.15))
    if type_changes > 0:
        top_signals.append(("type_changes", type_changes * 0.12))
    if removed_fields > 0:
        top_signals.append(("removed_fields", removed_fields * 0.08))
    if latency_degradation > 0:
        top_signals.append(("latency_degradation", latency_degradation / 100))
    if error_rate_increase > 0:
        top_signals.append(("error_rate_increase", error_rate_increase / 50))
    
    # Sort by contribution
    top_signals.sort(key=lambda x: x[1], reverse=True)
    
    return QoERiskResult(
        score=round(score, 4),
        action=action,
        top_signals=top_signals[:5]
    )
