"""
Brittleness Scoring Engine.

Computes an endpoint brittleness score (0-100) based on four signal families:
1. Contract Complexity - Schema depth, unions, required fields, free-form objects
2. Change Sensitivity - Spec diffs, backward-incompatible changes
3. Runtime Fragility - Timeouts, errors, latency variance, nondeterminism
4. Blast Radius - Tag criticality, environment weight, dependency count
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple


@dataclass
class ComplexitySignals:
    """Contract complexity signals."""
    schema_depth: int = 0
    branch_factor: int = 0  # anyOf/oneOf count
    required_fields: int = 0
    freeform_objects: int = 0  # additionalProperties usage
    parameter_count: int = 0
    constraint_tightness: float = 0.0  # min/max/pattern presence ratio
    
    def score(self) -> float:
        """Compute complexity sub-score (0-100)."""
        # Normalize each signal
        depth_score = min(self.schema_depth * 10, 30)  # max 30 for depth 3+
        branch_score = min(self.branch_factor * 15, 25)  # max 25 for 2+ unions
        required_score = min(self.required_fields * 2, 15)  # max 15
        freeform_score = min(self.freeform_objects * 20, 20)  # max 20
        param_score = min(self.parameter_count * 3, 10)  # max 10
        
        return min(depth_score + branch_score + required_score + freeform_score + param_score, 100)


@dataclass
class ChangeSignals:
    """Change sensitivity signals."""
    removed_fields: int = 0
    type_changes: int = 0
    enum_changes: int = 0
    response_code_changes: int = 0
    requiredness_changes: int = 0
    breaking_changes: int = 0
    
    def score(self) -> float:
        """Compute change sensitivity sub-score (0-100)."""
        removed_score = min(self.removed_fields * 20, 40)
        type_score = min(self.type_changes * 25, 30)
        enum_score = min(self.enum_changes * 10, 10)
        response_score = min(self.response_code_changes * 10, 10)
        required_score = min(self.requiredness_changes * 15, 10)
        
        return min(removed_score + type_score + enum_score + response_score + required_score, 100)


@dataclass
class FragilitySignals:
    """Runtime fragility signals."""
    timeout_rate: float = 0.0  # 0-1
    error_rate: float = 0.0  # 0-1 (5xx responses)
    latency_variance: float = 0.0  # stddev of response times
    schema_mismatch_rate: float = 0.0  # 0-1
    nondeterminism_rate: float = 0.0  # optional fields flapping
    
    def score(self) -> float:
        """Compute runtime fragility sub-score (0-100)."""
        timeout_score = self.timeout_rate * 30
        error_score = self.error_rate * 25
        latency_score = min(self.latency_variance / 100, 1) * 15  # Normalize by 100ms
        mismatch_score = self.schema_mismatch_rate * 20
        nondet_score = self.nondeterminism_rate * 10
        
        return min(timeout_score + error_score + latency_score + mismatch_score + nondet_score, 100)


@dataclass
class BlastSignals:
    """Blast radius signals."""
    tag_criticality: float = 0.5  # 0-1, from criticality profiles
    environment_weight: float = 0.5  # prod=1.0, stage=0.5, dev=0.2
    dependency_count: int = 0  # number of downstream consumers
    
    def score(self) -> float:
        """Compute blast radius sub-score (0-100)."""
        criticality_score = self.tag_criticality * 50
        env_score = self.environment_weight * 30
        dep_score = min(self.dependency_count * 5, 20)
        
        return min(criticality_score + env_score + dep_score, 100)


@dataclass
class BrittlenessContributor:
    """A top contributor to brittleness score."""
    path: str
    reason: str
    impact: float
    family: str


@dataclass
class BrittlenessResult:
    """Result of brittleness scoring."""
    score: float  # 0-100
    complexity_score: float
    change_score: float
    fragility_score: float
    blast_score: float
    top_contributors: List[BrittlenessContributor]
    signals: Dict[str, Any]


# Weights for combining sub-scores
BRITTLENESS_WEIGHTS = {
    "complexity": 0.25,
    "change": 0.30,
    "fragility": 0.25,
    "blast": 0.20,
}


def compute_brittleness_score(
    operation_schema: Optional[Dict[str, Any]] = None,
    parameters: Optional[List[Dict[str, Any]]] = None,
    current_spec: Optional[Dict[str, Any]] = None,
    previous_spec: Optional[Dict[str, Any]] = None,
    runtime_results: Optional[List[Dict[str, Any]]] = None,
    tag_criticality: float = 0.5,
    environment: str = "default",
    dependency_count: int = 0,
) -> BrittlenessResult:
    """
    Compute brittleness score for an operation.
    
    Args:
        operation_schema: Response schema for the operation
        parameters: List of operation parameters
        current_spec: Current OpenAPI spec (for change detection)
        previous_spec: Previous OpenAPI spec (for change detection)
        runtime_results: List of runtime validation results
        tag_criticality: Criticality weight from profiles (0-1)
        environment: Environment name (dev/stage/prod)
        dependency_count: Number of downstream consumers
    
    Returns:
        BrittlenessResult with score and breakdown
    """
    contributors = []
    
    # 1. Contract Complexity
    complexity = _compute_contract_complexity(
        operation_schema or {},
        parameters or [],
    )
    complexity_score = complexity.score()
    
    if complexity.schema_depth > 3:
        contributors.append(BrittlenessContributor(
            path="$",
            reason=f"Deep schema nesting (depth {complexity.schema_depth})",
            impact=complexity.schema_depth * 10,
            family="complexity",
        ))
    
    if complexity.branch_factor > 0:
        contributors.append(BrittlenessContributor(
            path="$",
            reason=f"Schema unions present ({complexity.branch_factor} anyOf/oneOf)",
            impact=complexity.branch_factor * 15,
            family="complexity",
        ))
    
    if complexity.freeform_objects > 0:
        contributors.append(BrittlenessContributor(
            path="$",
            reason=f"Free-form objects ({complexity.freeform_objects} additionalProperties)",
            impact=complexity.freeform_objects * 20,
            family="complexity",
        ))
    
    # 2. Change Sensitivity
    change = _compute_change_sensitivity(current_spec, previous_spec)
    change_score = change.score()
    
    if change.removed_fields > 0:
        contributors.append(BrittlenessContributor(
            path="$",
            reason=f"Removed fields ({change.removed_fields})",
            impact=change.removed_fields * 20,
            family="change",
        ))
    
    if change.type_changes > 0:
        contributors.append(BrittlenessContributor(
            path="$",
            reason=f"Type changes ({change.type_changes})",
            impact=change.type_changes * 25,
            family="change",
        ))
    
    # 3. Runtime Fragility
    fragility = _compute_runtime_fragility(runtime_results or [])
    fragility_score = fragility.score()
    
    if fragility.timeout_rate > 0.1:
        contributors.append(BrittlenessContributor(
            path="runtime",
            reason=f"High timeout rate ({fragility.timeout_rate:.1%})",
            impact=fragility.timeout_rate * 30,
            family="fragility",
        ))
    
    if fragility.error_rate > 0.1:
        contributors.append(BrittlenessContributor(
            path="runtime",
            reason=f"High error rate ({fragility.error_rate:.1%})",
            impact=fragility.error_rate * 25,
            family="fragility",
        ))
    
    if fragility.schema_mismatch_rate > 0.1:
        contributors.append(BrittlenessContributor(
            path="runtime",
            reason=f"Schema mismatches ({fragility.schema_mismatch_rate:.1%})",
            impact=fragility.schema_mismatch_rate * 20,
            family="fragility",
        ))
    
    # 4. Blast Radius
    env_weight = {"prod": 1.0, "production": 1.0, "stage": 0.5, "staging": 0.5, "dev": 0.2, "development": 0.2}.get(environment.lower(), 0.5)
    blast = BlastSignals(
        tag_criticality=tag_criticality,
        environment_weight=env_weight,
        dependency_count=dependency_count,
    )
    blast_score = blast.score()
    
    if tag_criticality > 0.8:
        contributors.append(BrittlenessContributor(
            path="tag",
            reason=f"High criticality tag ({tag_criticality:.2f})",
            impact=tag_criticality * 50,
            family="blast",
        ))
    
    # Combine scores
    total_score = (
        BRITTLENESS_WEIGHTS["complexity"] * complexity_score +
        BRITTLENESS_WEIGHTS["change"] * change_score +
        BRITTLENESS_WEIGHTS["fragility"] * fragility_score +
        BRITTLENESS_WEIGHTS["blast"] * blast_score
    )
    
    # Sort contributors by impact
    contributors.sort(key=lambda c: c.impact, reverse=True)
    
    return BrittlenessResult(
        score=round(total_score, 2),
        complexity_score=round(complexity_score, 2),
        change_score=round(change_score, 2),
        fragility_score=round(fragility_score, 2),
        blast_score=round(blast_score, 2),
        top_contributors=contributors[:5],
        signals={
            "complexity": {
                "schema_depth": complexity.schema_depth,
                "branch_factor": complexity.branch_factor,
                "required_fields": complexity.required_fields,
                "freeform_objects": complexity.freeform_objects,
                "parameter_count": complexity.parameter_count,
            },
            "change": {
                "removed_fields": change.removed_fields,
                "type_changes": change.type_changes,
                "enum_changes": change.enum_changes,
                "response_code_changes": change.response_code_changes,
                "requiredness_changes": change.requiredness_changes,
            },
            "fragility": {
                "timeout_rate": fragility.timeout_rate,
                "error_rate": fragility.error_rate,
                "latency_variance": fragility.latency_variance,
                "schema_mismatch_rate": fragility.schema_mismatch_rate,
                "nondeterminism_rate": fragility.nondeterminism_rate,
            },
            "blast": {
                "tag_criticality": blast.tag_criticality,
                "environment_weight": blast.environment_weight,
                "dependency_count": blast.dependency_count,
            },
        },
    )


def _compute_contract_complexity(
    schema: Dict[str, Any],
    parameters: List[Dict[str, Any]],
) -> ComplexitySignals:
    """Compute contract complexity signals from schema."""
    signals = ComplexitySignals()
    
    signals.parameter_count = len(parameters)
    
    if schema:
        depth, branches, freeform, required = _analyze_schema(schema)
        signals.schema_depth = depth
        signals.branch_factor = branches
        signals.freeform_objects = freeform
        signals.required_fields = required
        
        # Constraint tightness
        total_props, constrained_props = _count_constraints(schema)
        if total_props > 0:
            signals.constraint_tightness = constrained_props / total_props
    
    return signals


def _analyze_schema(
    schema: Dict[str, Any],
    depth: int = 0,
) -> Tuple[int, int, int, int]:
    """
    Recursively analyze schema for complexity signals.
    
    Returns: (max_depth, branch_count, freeform_count, required_count)
    """
    max_depth = depth
    branches = 0
    freeform = 0
    required = 0
    
    # Count unions
    if "anyOf" in schema:
        branches += len(schema["anyOf"])
        for sub in schema["anyOf"]:
            d, b, f, r = _analyze_schema(sub, depth + 1)
            max_depth = max(max_depth, d)
            branches += b
            freeform += f
            required += r
    
    if "oneOf" in schema:
        branches += len(schema["oneOf"])
        for sub in schema["oneOf"]:
            d, b, f, r = _analyze_schema(sub, depth + 1)
            max_depth = max(max_depth, d)
            branches += b
            freeform += f
            required += r
    
    # Check for free-form objects
    if schema.get("additionalProperties") is True:
        freeform += 1
    
    # Count required fields
    required += len(schema.get("required", []))
    
    # Recurse into properties
    if "properties" in schema:
        for prop_schema in schema["properties"].values():
            d, b, f, r = _analyze_schema(prop_schema, depth + 1)
            max_depth = max(max_depth, d)
            branches += b
            freeform += f
            required += r
    
    # Recurse into items (arrays)
    if "items" in schema:
        items = schema["items"]
        if isinstance(items, dict):
            d, b, f, r = _analyze_schema(items, depth + 1)
            max_depth = max(max_depth, d)
            branches += b
            freeform += f
            required += r
    
    return max_depth, branches, freeform, required


def _count_constraints(schema: Dict[str, Any]) -> Tuple[int, int]:
    """Count total properties and constrained properties."""
    total = 0
    constrained = 0
    
    if "properties" in schema:
        for prop_schema in schema["properties"].values():
            total += 1
            if any(k in prop_schema for k in ["minimum", "maximum", "minLength", "maxLength", "pattern", "enum"]):
                constrained += 1
            
            # Recurse
            sub_total, sub_constrained = _count_constraints(prop_schema)
            total += sub_total
            constrained += sub_constrained
    
    return total, constrained


def _compute_change_sensitivity(
    current_spec: Optional[Dict[str, Any]],
    previous_spec: Optional[Dict[str, Any]],
) -> ChangeSignals:
    """Compute change sensitivity signals by comparing specs."""
    signals = ChangeSignals()
    
    if not current_spec or not previous_spec:
        return signals
    
    # Compare paths
    current_paths = set(current_spec.get("paths", {}).keys())
    previous_paths = set(previous_spec.get("paths", {}).keys())
    
    # Removed paths are breaking
    removed = previous_paths - current_paths
    signals.removed_fields = len(removed)
    signals.breaking_changes = len(removed)
    
    # Compare common paths
    for path in current_paths & previous_paths:
        current_path = current_spec["paths"][path]
        previous_path = previous_spec["paths"][path]
        
        # Compare methods
        current_methods = set(k for k in current_path if k in ["get", "post", "put", "patch", "delete"])
        previous_methods = set(k for k in previous_path if k in ["get", "post", "put", "patch", "delete"])
        
        removed_methods = previous_methods - current_methods
        signals.removed_fields += len(removed_methods)
        signals.breaking_changes += len(removed_methods)
        
        # Compare responses
        for method in current_methods & previous_methods:
            current_responses = set(current_path[method].get("responses", {}).keys())
            previous_responses = set(previous_path[method].get("responses", {}).keys())
            
            signals.response_code_changes += len(current_responses ^ previous_responses)
    
    return signals


def _compute_runtime_fragility(results: List[Dict[str, Any]]) -> FragilitySignals:
    """Compute runtime fragility signals from validation results."""
    signals = FragilitySignals()
    
    if not results:
        return signals
    
    total = len(results)
    timeouts = 0
    errors = 0
    mismatches = 0
    response_times = []
    
    for result in results:
        if result.get("error") == "timeout":
            timeouts += 1
        
        status_code = result.get("status_code", 0)
        if 500 <= status_code < 600:
            errors += 1
        
        if result.get("schema_mismatches"):
            mismatches += 1
        
        if result.get("response_time_ms"):
            response_times.append(result["response_time_ms"])
    
    signals.timeout_rate = timeouts / total
    signals.error_rate = errors / total
    signals.schema_mismatch_rate = mismatches / total
    
    if len(response_times) > 1:
        signals.latency_variance = statistics.stdev(response_times)
    
    return signals
