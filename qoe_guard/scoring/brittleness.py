"""
Brittleness Scoring Module.

Computes a brittleness score (0-100) based on:
- Contract complexity
- Change sensitivity
- Runtime fragility
- Blast radius
"""
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class BrittlenessResult:
    """Result of brittleness calculation."""
    score: float
    top_contributors: List[Tuple[str, str, float]] = field(default_factory=list)
    breakdown: Dict[str, float] = field(default_factory=dict)


# Weight configuration
BRITTLENESS_WEIGHTS = {
    "contract_complexity": 0.25,
    "change_sensitivity": 0.30,
    "runtime_fragility": 0.25,
    "blast_radius": 0.20,
}


def compute_brittleness_score(
    contract_complexity: float = 0.0,
    change_sensitivity: float = 0.0,
    runtime_fragility: float = 0.0,
    blast_radius: float = 0.0,
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Compute brittleness score from component signals.
    
    Args:
        contract_complexity: Normalized score (0-1) for schema complexity
        change_sensitivity: Normalized score (0-1) for change impact
        runtime_fragility: Normalized score (0-1) for runtime stability
        blast_radius: Normalized score (0-1) for impact scope
        weights: Optional custom weights
        
    Returns:
        Brittleness score from 0 to 100
    """
    w = weights or BRITTLENESS_WEIGHTS
    
    # Clamp inputs to [0, 1]
    contract_complexity = max(0, min(1, contract_complexity))
    change_sensitivity = max(0, min(1, change_sensitivity))
    runtime_fragility = max(0, min(1, runtime_fragility))
    blast_radius = max(0, min(1, blast_radius))
    
    # Weighted sum
    score = (
        w.get("contract_complexity", 0.25) * contract_complexity +
        w.get("change_sensitivity", 0.30) * change_sensitivity +
        w.get("runtime_fragility", 0.25) * runtime_fragility +
        w.get("blast_radius", 0.20) * blast_radius
    )
    
    # Scale to 0-100
    return round(score * 100, 2)


def compute_contract_complexity(schema: Dict[str, Any]) -> float:
    """
    Compute contract complexity from an OpenAPI schema.
    
    Factors:
    - Schema depth
    - Number of required fields
    - Union/anyOf complexity
    - Constraint tightness
    
    Returns:
        Normalized complexity score (0-1)
    """
    if not schema:
        return 0.0
    
    score = 0.0
    
    # Count required fields
    required = schema.get("required", [])
    score += min(len(required) * 0.05, 0.3)
    
    # Check for nested objects
    properties = schema.get("properties", {})
    nested_count = sum(
        1 for p in properties.values()
        if isinstance(p, dict) and p.get("type") == "object"
    )
    score += min(nested_count * 0.1, 0.3)
    
    # Check for anyOf/oneOf
    if "anyOf" in schema or "oneOf" in schema:
        score += 0.2
    
    # Check for constraints
    constraints = ["minLength", "maxLength", "minimum", "maximum", "pattern", "enum"]
    constraint_count = sum(1 for c in constraints if c in schema)
    score += min(constraint_count * 0.05, 0.2)
    
    return min(score, 1.0)


def compute_change_sensitivity(
    removed_fields: int = 0,
    type_changes: int = 0,
    enum_changes: int = 0,
    requiredness_changes: int = 0
) -> float:
    """
    Compute change sensitivity based on detected changes.
    
    Returns:
        Normalized sensitivity score (0-1)
    """
    score = 0.0
    
    # Removed fields are high impact
    score += min(removed_fields * 0.15, 0.4)
    
    # Type changes are breaking
    score += min(type_changes * 0.2, 0.3)
    
    # Enum changes can break clients
    score += min(enum_changes * 0.1, 0.2)
    
    # Requiredness changes
    score += min(requiredness_changes * 0.1, 0.1)
    
    return min(score, 1.0)


def compute_runtime_fragility(
    timeout_rate: float = 0.0,
    error_rate: float = 0.0,
    latency_variance: float = 0.0
) -> float:
    """
    Compute runtime fragility from operational metrics.
    
    Returns:
        Normalized fragility score (0-1)
    """
    score = 0.0
    
    # High timeout rate indicates fragility
    score += min(timeout_rate * 2, 0.4)
    
    # Error rate
    score += min(error_rate * 2, 0.4)
    
    # High variance indicates instability
    # Normalize variance (assuming typical latency in ms)
    normalized_variance = min(latency_variance / 1000, 1.0)
    score += normalized_variance * 0.2
    
    return min(score, 1.0)


def compute_blast_radius(
    criticality_score: float = 0.0,
    dependency_count: int = 0,
    environment_weight: float = 1.0
) -> float:
    """
    Compute blast radius based on criticality and dependencies.
    
    Args:
        criticality_score: How critical this endpoint is (0-1)
        dependency_count: Number of downstream dependencies
        environment_weight: Production=1.0, Staging=0.5, Dev=0.2
        
    Returns:
        Normalized blast radius score (0-1)
    """
    score = 0.0
    
    # Direct criticality
    score += criticality_score * 0.5
    
    # Dependency amplification
    score += min(dependency_count * 0.05, 0.3)
    
    # Environment weighting
    score *= environment_weight
    
    return min(score, 1.0)
