"""
Drift Classification Engine.

Classifies drift into categories:
- NONE: No drift detected
- SPEC_DRIFT: OpenAPI specification changed
- RUNTIME_DRIFT: Runtime behavior changed without spec change
- UNDOCUMENTED: Runtime drift affecting critical paths (dangerous)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set

from .criticality import (
    CriticalityProfiles,
    DEFAULT_CRITICALITY_PROFILES,
    is_critical_path,
    get_critical_paths,
)


class DriftType(Enum):
    """Types of drift classification."""
    NONE = "none"
    SPEC_DRIFT = "spec_drift"
    RUNTIME_DRIFT = "runtime_drift"
    UNDOCUMENTED = "undocumented"


@dataclass
class DriftEvidence:
    """Evidence supporting a drift classification."""
    path: str
    drift_type: str
    description: str
    severity: str  # low, medium, high, critical


@dataclass
class DriftClassification:
    """Result of drift classification."""
    drift_type: DriftType
    spec_changed: bool
    runtime_mismatches: int
    critical_mismatches: int
    evidence: List[DriftEvidence]
    severity: str  # low, medium, high, critical
    recommendations: List[str]


def classify_drift(
    current_spec_hash: Optional[str],
    previous_spec_hash: Optional[str],
    schema_mismatches: Optional[List[Dict[str, Any]]] = None,
    critical_paths: Optional[Set[str]] = None,
    profiles: Optional[CriticalityProfiles] = None,
) -> DriftClassification:
    """
    Classify drift type based on spec changes and runtime behavior.
    
    Args:
        current_spec_hash: Hash of current OpenAPI spec
        previous_spec_hash: Hash of previous OpenAPI spec
        schema_mismatches: List of runtime schema mismatch records
        critical_paths: Set of critical path patterns (overrides profiles)
        profiles: Criticality profiles for determining critical paths
    
    Returns:
        DriftClassification with type, evidence, and recommendations
    """
    if profiles is None:
        profiles = DEFAULT_CRITICALITY_PROFILES
    
    if critical_paths is None:
        critical_paths = set(get_critical_paths(profiles))
    
    evidence: List[DriftEvidence] = []
    recommendations: List[str] = []
    
    # Check for spec drift
    spec_changed = (
        current_spec_hash is not None and
        previous_spec_hash is not None and
        current_spec_hash != previous_spec_hash
    )
    
    if spec_changed:
        evidence.append(DriftEvidence(
            path="spec",
            drift_type="spec_change",
            description=f"Spec hash changed: {previous_spec_hash[:8]}... → {current_spec_hash[:8]}...",
            severity="medium",
        ))
        recommendations.append("Review spec changes for backward compatibility")
    
    # Count schema mismatches
    runtime_mismatches = 0
    critical_mismatches = 0
    
    if schema_mismatches:
        for mismatch in schema_mismatches:
            path = mismatch.get("path", "$")
            runtime_mismatches += 1
            
            # Check if this path is critical
            is_critical = _is_path_critical(path, critical_paths, profiles)
            
            if is_critical:
                critical_mismatches += 1
                evidence.append(DriftEvidence(
                    path=path,
                    drift_type="critical_mismatch",
                    description=mismatch.get("message", "Schema mismatch on critical path"),
                    severity="high",
                ))
            else:
                evidence.append(DriftEvidence(
                    path=path,
                    drift_type="schema_mismatch",
                    description=mismatch.get("message", "Schema mismatch"),
                    severity="medium",
                ))
    
    # Determine drift type
    if spec_changed and runtime_mismatches == 0:
        # Spec changed but no runtime issues
        drift_type = DriftType.SPEC_DRIFT
        severity = "medium"
        recommendations.append("Update baselines to match new spec")
    
    elif not spec_changed and runtime_mismatches > 0:
        # Runtime drift without spec change
        if critical_mismatches > 0:
            drift_type = DriftType.UNDOCUMENTED
            severity = "critical"
            recommendations.append("URGENT: Runtime behavior changed on critical paths without spec update")
            recommendations.append("Investigate implementation changes")
            recommendations.append("Consider rolling back or updating spec")
        else:
            drift_type = DriftType.RUNTIME_DRIFT
            severity = "high"
            recommendations.append("Runtime behavior differs from spec")
            recommendations.append("Update spec to document new behavior or fix implementation")
    
    elif spec_changed and runtime_mismatches > 0:
        # Both spec and runtime changed
        if critical_mismatches > 0:
            drift_type = DriftType.UNDOCUMENTED
            severity = "critical"
            recommendations.append("Spec and runtime both changed with critical path mismatches")
        else:
            drift_type = DriftType.SPEC_DRIFT
            severity = "high"
            recommendations.append("Spec changed and runtime shows mismatches")
            recommendations.append("Verify baselines are updated correctly")
    
    else:
        # No drift
        drift_type = DriftType.NONE
        severity = "low"
    
    return DriftClassification(
        drift_type=drift_type,
        spec_changed=spec_changed,
        runtime_mismatches=runtime_mismatches,
        critical_mismatches=critical_mismatches,
        evidence=evidence,
        severity=severity,
        recommendations=recommendations,
    )


def _is_path_critical(
    path: str,
    critical_paths: Set[str],
    profiles: CriticalityProfiles,
) -> bool:
    """Check if a path is considered critical."""
    # Direct match
    if path in critical_paths:
        return True
    
    # Pattern matching
    for pattern in critical_paths:
        if _path_matches_pattern(path, pattern):
            return True
    
    # Use criticality profiles
    return is_critical_path(path, profiles)


def _path_matches_pattern(path: str, pattern: str) -> bool:
    """Check if path matches a pattern (simple glob)."""
    if "*" in pattern:
        # Convert to simple prefix/suffix matching
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return path.startswith(prefix)
        elif pattern.startswith("*"):
            suffix = pattern[1:]
            return path.endswith(suffix)
    
    return path == pattern


def detect_spec_drift(
    current_spec: Dict[str, Any],
    previous_spec: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Detect specific changes between two specs.
    
    Returns detailed breakdown of spec drift.
    """
    from ..swagger.normalizer import compare_specs
    
    comparison = compare_specs(current_spec, previous_spec)
    
    drift_details = {
        "has_drift": bool(comparison.get("added_paths") or comparison.get("removed_paths") or comparison.get("changed")),
        "is_breaking": comparison.get("is_breaking", False),
        "added_paths": comparison.get("added_paths", []),
        "removed_paths": comparison.get("removed_paths", []),
        "changed": comparison.get("changed", []),
    }
    
    return drift_details


def compute_drift_severity(classification: DriftClassification) -> int:
    """
    Compute a numeric severity score for drift.
    
    Returns: 0 (none) to 100 (critical)
    """
    base_scores = {
        DriftType.NONE: 0,
        DriftType.SPEC_DRIFT: 40,
        DriftType.RUNTIME_DRIFT: 60,
        DriftType.UNDOCUMENTED: 90,
    }
    
    score = base_scores.get(classification.drift_type, 0)
    
    # Add for critical mismatches
    score += min(classification.critical_mismatches * 5, 10)
    
    # Add for total mismatches
    score += min(classification.runtime_mismatches * 2, 10)
    
    return min(score, 100)
