"""
Data Models for QoE-Guard.

Contains all core data classes and types used throughout the application.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


# =============================================================================
# CHANGE TRACKING
# =============================================================================

@dataclass
class Change:
    """Represents a single change detected in JSON comparison."""
    path: str
    change_type: str  # "added", "removed", "value_changed", "type_changed"
    old_value: Any = None
    new_value: Any = None
    old_type: str = None
    new_type: str = None
    is_breaking: bool = False
    is_critical: bool = False
    criticality_score: float = 0.0


@dataclass
class SchemaMismatch:
    """Represents a schema validation mismatch."""
    path: str
    message: str
    expected_type: str = None
    actual_type: str = None
    expected_value: Any = None
    actual_value: Any = None


# =============================================================================
# DIFF RESULTS
# =============================================================================

@dataclass
class DiffResult:
    """Result of comparing two JSON objects."""
    changes: List[Change] = field(default_factory=list)
    decision: str = "PASS"  # PASS, WARN, FAIL
    qoe_risk_score: float = 0.0
    brittleness_score: float = 0.0
    summary: str = ""
    

# =============================================================================
# FEATURE VECTORS
# =============================================================================

@dataclass
class FeatureVector:
    """Numeric feature vector extracted from diff results."""
    total_changes: int = 0
    added_fields: int = 0
    removed_fields: int = 0
    value_changes: int = 0
    type_changes: int = 0
    critical_changes: int = 0
    breaking_changes: int = 0
    array_length_changes: int = 0
    max_numeric_delta: float = 0.0
    numeric_delta_sum: float = 0.0


# Alias for backward compatibility
@dataclass
class Features:
    """Feature set for scoring (legacy compatibility)."""
    critical_changes: int = 0
    type_changes: int = 0
    removed_fields: int = 0
    added_fields: int = 0
    array_len_changes: int = 0
    numeric_delta_max: float = 0.0
    numeric_delta_sum: float = 0.0
    value_changes: int = 0


# =============================================================================
# RISK ASSESSMENT
# =============================================================================

@dataclass
class RiskAssessment:
    """Risk assessment result."""
    qoe_risk_score: float
    brittleness_score: float
    decision: str  # PASS, WARN, FAIL
    top_contributors: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class Decision:
    """Scoring decision result."""
    risk_score: float  # 0..1
    action: str        # PASS/WARN/FAIL
    reasons: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# SCORING LOGIC
# =============================================================================

# Interpretable "QoE-aware" weights
WEIGHTS = {
    "critical_changes": 0.18,
    "type_changes": 0.14,
    "removed_fields": 0.10,
    "added_fields": 0.05,
    "array_len_changes": 0.07,
    "numeric_delta_max": 0.16,
    "numeric_delta_sum": 0.06,
    "value_changes": 0.04,
}


def _sigmoid(x: float) -> float:
    """Sigmoid activation function."""
    import math
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


def score(features: Features) -> Decision:
    """
    Calculate risk score from features.
    
    Args:
        features: Extracted feature set
        
    Returns:
        Decision with risk score and action
    """
    # Simple linear + sigmoid
    x = 0.0
    x += WEIGHTS["critical_changes"] * features.critical_changes
    x += WEIGHTS["type_changes"] * features.type_changes
    x += WEIGHTS["removed_fields"] * features.removed_fields
    x += WEIGHTS["added_fields"] * features.added_fields
    x += WEIGHTS["array_len_changes"] * features.array_len_changes
    x += WEIGHTS["numeric_delta_max"] * min(features.numeric_delta_max / 5.0, 10.0)
    x += WEIGHTS["numeric_delta_sum"] * min(features.numeric_delta_sum / 10.0, 10.0)
    x += WEIGHTS["value_changes"] * min(features.value_changes / 10.0, 10.0)

    # bias: default low risk unless evidence
    x -= 1.2

    risk = _sigmoid(x)

    # Policy thresholds
    if risk >= 0.72 or (features.critical_changes >= 3 and features.type_changes >= 1):
        action = "FAIL"
    elif risk >= 0.45 or features.critical_changes >= 2:
        action = "WARN"
    else:
        action = "PASS"

    reasons = {
        "policy": {
            "fail_threshold": 0.72,
            "warn_threshold": 0.45,
            "critical_override": ">=3 critical + >=1 type change => FAIL",
        },
        "top_signals": [
            {"signal": "critical_changes", "value": features.critical_changes},
            {"signal": "type_changes", "value": features.type_changes},
            {"signal": "removed_fields", "value": features.removed_fields},
            {"signal": "numeric_delta_max", "value": features.numeric_delta_max},
        ],
    }
    return Decision(risk_score=round(float(risk), 4), action=action, reasons=reasons)
