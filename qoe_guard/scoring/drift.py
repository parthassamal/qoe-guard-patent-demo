"""
Drift Classification Module.

Classifies API drift into categories:
- NONE: No drift detected
- SPEC_DRIFT: OpenAPI spec changed
- RUNTIME_DRIFT: Implementation differs from spec
- UNDOCUMENTED: Runtime changes on critical paths
"""
from enum import Enum
from typing import List, Set, Optional
from dataclasses import dataclass, field


class DriftType(Enum):
    """Types of API drift."""
    NONE = "none"
    SPEC_DRIFT = "spec_drift"
    RUNTIME_DRIFT = "runtime_drift"
    UNDOCUMENTED = "undocumented"


@dataclass
class DriftClassification:
    """Result of drift classification."""
    drift_type: DriftType
    description: str
    affected_paths: List[str] = field(default_factory=list)
    severity: str = "low"  # low, medium, high, critical
    recommendations: List[str] = field(default_factory=list)


def classify_drift(
    spec_changed: bool = False,
    runtime_mismatches: Optional[List[str]] = None,
    critical_paths: Optional[Set[str]] = None
) -> DriftClassification:
    """
    Classify API drift based on spec and runtime changes.
    
    Args:
        spec_changed: Whether the OpenAPI spec hash changed
        runtime_mismatches: Paths where runtime differs from spec
        critical_paths: Set of paths considered critical
        
    Returns:
        DriftClassification with type and details
    """
    runtime_mismatches = runtime_mismatches or []
    critical_paths = critical_paths or set()
    
    # No changes
    if not spec_changed and not runtime_mismatches:
        return DriftClassification(
            drift_type=DriftType.NONE,
            description="No drift detected. API is conformant.",
            severity="low"
        )
    
    # Spec drift only
    if spec_changed and not runtime_mismatches:
        return DriftClassification(
            drift_type=DriftType.SPEC_DRIFT,
            description="OpenAPI specification has changed. Review the spec diff.",
            severity="medium",
            recommendations=[
                "Review the spec changes for breaking modifications",
                "Update consumers if required fields changed",
                "Consider versioning if changes are significant"
            ]
        )
    
    # Check if runtime mismatches affect critical paths
    critical_affected = [
        path for path in runtime_mismatches
        if any(cp in path for cp in critical_paths) or
           any(kw in path.lower() for kw in ["playback", "drm", "license", "entitle"])
    ]
    
    # Undocumented drift (critical)
    if runtime_mismatches and critical_affected:
        return DriftClassification(
            drift_type=DriftType.UNDOCUMENTED,
            description="Undocumented changes detected on critical paths. DANGER!",
            affected_paths=critical_affected,
            severity="critical",
            recommendations=[
                "URGENT: Investigate critical path changes immediately",
                "Block deployment until changes are documented",
                "Update OpenAPI spec to reflect actual behavior",
                "Notify downstream consumers of breaking changes"
            ]
        )
    
    # Runtime drift (non-critical)
    if runtime_mismatches:
        return DriftClassification(
            drift_type=DriftType.RUNTIME_DRIFT,
            description="Runtime behavior differs from OpenAPI spec.",
            affected_paths=runtime_mismatches,
            severity="high" if len(runtime_mismatches) > 3 else "medium",
            recommendations=[
                "Update OpenAPI spec to match actual implementation",
                "Or fix implementation to match spec",
                "Review affected paths for consumer impact"
            ]
        )
    
    # Default (shouldn't reach here)
    return DriftClassification(
        drift_type=DriftType.NONE,
        description="Unable to classify drift.",
        severity="low"
    )


def get_drift_severity_score(drift: DriftClassification) -> float:
    """
    Convert drift classification to a numeric severity score.
    
    Returns:
        Score from 0.0 (no drift) to 1.0 (critical drift)
    """
    severity_map = {
        "low": 0.1,
        "medium": 0.4,
        "high": 0.7,
        "critical": 1.0
    }
    return severity_map.get(drift.severity, 0.5)
