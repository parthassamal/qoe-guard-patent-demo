"""
QoE-Aware Risk Scoring Engine.

Computes QoE impact risk (0.0-1.0) based on:
- Changes on critical paths (weighted by criticality)
- Type changes on critical paths
- Numeric delta magnitude on QoE-sensitive fields
- Runtime signals (latency, errors)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from .criticality import (
    CriticalityProfiles,
    DEFAULT_CRITICALITY_PROFILES,
    get_path_criticality,
    is_critical_path,
)


@dataclass
class QoESignal:
    """A signal contributing to QoE risk."""
    path: str
    signal_type: str
    value: Any
    weight: float
    criticality: float


@dataclass
class QoERiskResult:
    """Result of QoE risk scoring."""
    risk_score: float  # 0.0-1.0
    action: str  # PASS, WARN, FAIL
    top_signals: List[QoESignal]
    weighted_changes: float
    critical_type_changes: int
    numeric_delta_max: float
    reasons: Dict[str, Any]


# Feature weights for QoE risk model
QOE_FEATURE_WEIGHTS = {
    "critical_changes": 0.22,
    "critical_type_changes": 0.20,
    "numeric_delta_critical": 0.18,
    "removed_critical": 0.15,
    "value_changes": 0.10,
    "added_fields": 0.05,
    "latency_factor": 0.05,
    "error_factor": 0.05,
}

# Decision thresholds
QOE_FAIL_THRESHOLD = 0.72
QOE_WARN_THRESHOLD = 0.45


def compute_qoe_risk(
    changes: List[Dict[str, Any]],
    profiles: Optional[CriticalityProfiles] = None,
    runtime_signals: Optional[Dict[str, Any]] = None,
    fail_threshold: float = QOE_FAIL_THRESHOLD,
    warn_threshold: float = QOE_WARN_THRESHOLD,
) -> QoERiskResult:
    """
    Compute QoE impact risk score.
    
    Args:
        changes: List of JSON diff changes with path, change_type, before, after
        profiles: Criticality profiles for weighting
        runtime_signals: Optional runtime signals (latency_ms, error_rate)
        fail_threshold: Risk threshold for FAIL decision
        warn_threshold: Risk threshold for WARN decision
    
    Returns:
        QoERiskResult with risk score, action, and explanations
    """
    if profiles is None:
        profiles = DEFAULT_CRITICALITY_PROFILES
    
    signals: List[QoESignal] = []
    
    # Compute features
    weighted_changes = 0.0
    critical_type_changes = 0
    numeric_delta_max = 0.0
    removed_critical = 0
    value_changes = 0
    added_fields = 0
    
    for change in changes:
        path = change.get("path", "$")
        change_type = change.get("change_type", "")
        before = change.get("before")
        after = change.get("after")
        
        # Get criticality weight for this path
        criticality = get_path_criticality(profiles, path)
        
        # Count by type
        if change_type == "removed":
            if criticality >= 0.7:
                removed_critical += 1
                signals.append(QoESignal(
                    path=path,
                    signal_type="removed_critical",
                    value=before,
                    weight=0.15,
                    criticality=criticality,
                ))
        
        elif change_type == "type_changed":
            if criticality >= 0.5:
                critical_type_changes += 1
                signals.append(QoESignal(
                    path=path,
                    signal_type="type_change",
                    value=f"{type(before).__name__} → {type(after).__name__}",
                    weight=0.20,
                    criticality=criticality,
                ))
        
        elif change_type == "value_changed":
            value_changes += 1
            
            # Check for numeric delta
            if isinstance(before, (int, float)) and isinstance(after, (int, float)):
                delta = abs(after - before)
                # Normalize by magnitude
                magnitude = max(abs(before), 1)
                relative_delta = delta / magnitude
                
                if relative_delta > 0.1 and criticality >= 0.5:
                    numeric_delta_max = max(numeric_delta_max, delta)
                    signals.append(QoESignal(
                        path=path,
                        signal_type="numeric_delta",
                        value=f"{before} → {after} (Δ{delta:.2f})",
                        weight=0.18 * criticality,
                        criticality=criticality,
                    ))
            
            elif criticality >= 0.7:
                signals.append(QoESignal(
                    path=path,
                    signal_type="critical_value_change",
                    value=f"{before} → {after}",
                    weight=0.10,
                    criticality=criticality,
                ))
        
        elif change_type == "added":
            added_fields += 1
        
        # Accumulate weighted changes
        weighted_changes += criticality
    
    # Runtime signals
    latency_factor = 0.0
    error_factor = 0.0
    
    if runtime_signals:
        latency_ms = runtime_signals.get("latency_ms", 0)
        error_rate = runtime_signals.get("error_rate", 0)
        
        # Normalize latency (100ms = 0.1, 1000ms = 1.0)
        latency_factor = min(latency_ms / 1000, 1.0)
        error_factor = error_rate
        
        if latency_factor > 0.3:
            signals.append(QoESignal(
                path="runtime",
                signal_type="latency",
                value=f"{latency_ms}ms",
                weight=0.05,
                criticality=latency_factor,
            ))
        
        if error_factor > 0.05:
            signals.append(QoESignal(
                path="runtime",
                signal_type="error_rate",
                value=f"{error_rate:.1%}",
                weight=0.05,
                criticality=error_factor,
            ))
    
    # Compute risk score using weighted features
    features = {
        "critical_changes": min(weighted_changes / 5, 1.0),  # Normalize by 5
        "critical_type_changes": min(critical_type_changes / 2, 1.0),
        "numeric_delta_critical": min(numeric_delta_max / 100, 1.0),  # Normalize by 100
        "removed_critical": min(removed_critical / 2, 1.0),
        "value_changes": min(value_changes / 10, 1.0),
        "added_fields": min(added_fields / 10, 1.0),
        "latency_factor": latency_factor,
        "error_factor": error_factor,
    }
    
    # Weighted sum
    raw_score = sum(
        QOE_FEATURE_WEIGHTS.get(k, 0) * v
        for k, v in features.items()
    )
    
    # Apply sigmoid for smoother curve
    # Shift and scale to make 0.5 input -> ~0.5 output
    risk_score = 1 / (1 + math.exp(-(raw_score * 6 - 2)))
    
    # Apply override rules
    if critical_type_changes >= 2:
        risk_score = max(risk_score, 0.75)
    if removed_critical >= 2:
        risk_score = max(risk_score, 0.70)
    
    # Determine action
    if risk_score >= fail_threshold:
        action = "FAIL"
    elif risk_score >= warn_threshold:
        action = "WARN"
    else:
        action = "PASS"
    
    # Sort signals by weight * criticality
    signals.sort(key=lambda s: s.weight * s.criticality, reverse=True)
    
    return QoERiskResult(
        risk_score=round(risk_score, 4),
        action=action,
        top_signals=signals[:5],
        weighted_changes=round(weighted_changes, 2),
        critical_type_changes=critical_type_changes,
        numeric_delta_max=round(numeric_delta_max, 2),
        reasons={
            "features": features,
            "thresholds": {
                "fail": fail_threshold,
                "warn": warn_threshold,
            },
            "override_applied": critical_type_changes >= 2 or removed_critical >= 2,
            "top_signals": [
                {
                    "path": s.path,
                    "signal": s.signal_type,
                    "value": str(s.value),
                    "weight": round(s.weight, 3),
                    "criticality": round(s.criticality, 3),
                }
                for s in signals[:5]
            ],
        },
    )


def compute_qoe_risk_from_diff(
    baseline: Dict[str, Any],
    candidate: Dict[str, Any],
    profiles: Optional[CriticalityProfiles] = None,
) -> QoERiskResult:
    """
    Compute QoE risk by diffing two JSON objects.
    
    Convenience wrapper that computes the diff first.
    """
    from ..diff import diff_json
    
    changes_raw = diff_json(baseline, candidate)
    changes = [
        {
            "path": c.path,
            "change_type": c.change_type,
            "before": c.before,
            "after": c.after,
        }
        for c in changes_raw
    ]
    
    return compute_qoe_risk(changes, profiles)
