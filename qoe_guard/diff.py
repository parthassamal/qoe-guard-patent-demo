"""
JSON Diff Engine for QoE-Guard.

Compares two JSON objects and produces a list of changes
with path information and change classification.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional

from .model import Change, DiffResult, FeatureVector, Features
from .scoring.criticality import get_criticality_for_path
from .scoring.qoe_risk import compute_qoe_risk, compute_qoe_action

JSON = Any


# =============================================================================
# INTERNAL CHANGE CLASS (for diff_json backward compatibility)
# =============================================================================

@dataclass
class InternalChange:
    """Internal change representation for diff engine."""
    path: str
    change_type: str  # added, removed, type_changed, value_changed
    before: Any = None
    after: Any = None


# =============================================================================
# TYPE UTILITIES
# =============================================================================

def _type_name(x: Any) -> str:
    """Get human-readable type name for JSON values."""
    if x is None:
        return "null"
    if isinstance(x, bool):
        return "bool"
    if isinstance(x, (int, float)):
        return "number"
    if isinstance(x, str):
        return "string"
    if isinstance(x, list):
        return "array"
    if isinstance(x, dict):
        return "object"
    return type(x).__name__


# =============================================================================
# DIFF WALKER
# =============================================================================

def _walk(before: JSON, after: JSON, path: str, changes: List[InternalChange]) -> None:
    """Recursively walk and compare JSON structures."""
    tb, ta = _type_name(before), _type_name(after)

    # Path exists only in one side
    if before is None and after is not None and path != "$":
        changes.append(InternalChange(path=path, change_type="added", before=None, after=after))
        return
    if after is None and before is not None and path != "$":
        changes.append(InternalChange(path=path, change_type="removed", before=before, after=None))
        return

    # Type mismatch
    if tb != ta:
        changes.append(InternalChange(path=path, change_type="type_changed", before=before, after=after))
        return

    # Recurse into objects
    if isinstance(before, dict) and isinstance(after, dict):
        keys = set(before.keys()) | set(after.keys())
        for k in sorted(keys):
            b = before.get(k, None)
            a = after.get(k, None)
            _walk(b, a, f"{path}.{k}", changes)
        return

    # Recurse into arrays
    if isinstance(before, list) and isinstance(after, list):
        # Track length changes
        if len(before) != len(after):
            changes.append(InternalChange(
                path=f"{path}.__len__",
                change_type="value_changed",
                before=len(before),
                after=len(after)
            ))
        # Compare items up to min length
        n = min(len(before), len(after))
        for i in range(n):
            _walk(before[i], after[i], f"{path}[{i}]", changes)
        # Track added/removed items
        if len(after) > len(before):
            for i in range(len(before), len(after)):
                changes.append(InternalChange(
                    path=f"{path}[{i}]",
                    change_type="added",
                    before=None,
                    after=after[i]
                ))
        elif len(before) > len(after):
            for i in range(len(after), len(before)):
                changes.append(InternalChange(
                    path=f"{path}[{i}]",
                    change_type="removed",
                    before=before[i],
                    after=None
                ))
        return

    # Primitive value comparison
    if before != after:
        changes.append(InternalChange(path=path, change_type="value_changed", before=before, after=after))


# =============================================================================
# PUBLIC API
# =============================================================================

def diff_json(baseline: JSON, candidate: JSON) -> List[InternalChange]:
    """
    Compare two JSON objects and return list of changes.
    
    Args:
        baseline: The original/expected JSON
        candidate: The new/actual JSON
        
    Returns:
        List of InternalChange objects describing differences
    """
    changes: List[InternalChange] = []
    _walk(baseline, candidate, "$", changes)
    # Filter root-only artifacts
    return [c for c in changes if c.path != "$"]


def json_diff(baseline: JSON, candidate: JSON) -> DiffResult:
    """
    Compare two JSON objects and return a DiffResult with scoring.
    
    This is the main entry point for JSON comparison.
    
    Args:
        baseline: The original/expected JSON
        candidate: The new/actual JSON
        
    Returns:
        DiffResult with changes, risk score, and decision
    """
    internal_changes = diff_json(baseline, candidate)
    
    # Convert to model Change objects
    changes: List[Change] = []
    for ic in internal_changes:
        criticality = get_criticality_for_path(ic.path)
        is_breaking = ic.change_type in ("type_changed", "removed")
        is_critical = criticality >= 0.8
        
        change = Change(
            path=ic.path,
            change_type=ic.change_type,
            old_value=ic.before,
            new_value=ic.after,
            old_type=_type_name(ic.before) if ic.change_type == "type_changed" else None,
            new_type=_type_name(ic.after) if ic.change_type == "type_changed" else None,
            is_breaking=is_breaking,
            is_critical=is_critical,
            criticality_score=criticality,
        )
        changes.append(change)
    
    # Calculate scores
    critical_changes = sum(1 for c in changes if c.is_critical)
    type_changes = sum(1 for c in changes if c.change_type == "type_changed")
    removed_fields = sum(1 for c in changes if c.change_type == "removed")
    
    qoe_risk = compute_qoe_risk(
        changes_count=len(changes),
        critical_changes=critical_changes,
        type_changes=type_changes,
        removed_fields=removed_fields,
    )
    
    decision = compute_qoe_action(qoe_risk)
    
    return DiffResult(
        changes=changes,
        decision=decision,
        qoe_risk_score=qoe_risk,
        summary=f"{len(changes)} changes detected ({critical_changes} critical)"
    )


def extract_features(diff_result: DiffResult) -> FeatureVector:
    """
    Extract numeric features from a diff result.
    
    Args:
        diff_result: Result from json_diff
        
    Returns:
        FeatureVector with numeric features for scoring
    """
    changes = diff_result.changes
    
    # Count by type
    added = sum(1 for c in changes if c.change_type == "added")
    removed = sum(1 for c in changes if c.change_type == "removed")
    value_changed = sum(1 for c in changes if c.change_type == "value_changed")
    type_changed = sum(1 for c in changes if c.change_type == "type_changed")
    
    # Count special categories
    critical = sum(1 for c in changes if getattr(c, 'is_critical', False))
    breaking = sum(1 for c in changes if getattr(c, 'is_breaking', False))
    
    # Calculate array changes
    array_changes = sum(1 for c in changes if '[' in c.path)
    
    # Calculate numeric deltas
    numeric_deltas = []
    for c in changes:
        if c.change_type == "value_changed":
            try:
                if isinstance(c.old_value, (int, float)) and isinstance(c.new_value, (int, float)):
                    delta = abs(c.new_value - c.old_value)
                    numeric_deltas.append(delta)
            except (TypeError, AttributeError):
                pass
    
    max_numeric_delta = max(numeric_deltas) if numeric_deltas else 0
    numeric_delta_sum = sum(numeric_deltas)
    
    return FeatureVector(
        total_changes=len(changes),
        added_fields=added,
        removed_fields=removed,
        value_changes=value_changed,
        type_changes=type_changed,
        critical_changes=critical,
        breaking_changes=breaking,
        array_length_changes=array_changes,
        max_numeric_delta=max_numeric_delta,
        numeric_delta_sum=numeric_delta_sum,
    )


def to_legacy_features(diff_result: DiffResult) -> Features:
    """
    Convert diff result to legacy Features format for scoring.
    
    Args:
        diff_result: Result from json_diff
        
    Returns:
        Features object for legacy score() function
    """
    fv = extract_features(diff_result)
    return Features(
        critical_changes=fv.critical_changes,
        type_changes=fv.type_changes,
        removed_fields=fv.removed_fields,
        added_fields=fv.added_fields,
        array_len_changes=fv.array_length_changes,
        numeric_delta_max=fv.max_numeric_delta,
        numeric_delta_sum=fv.numeric_delta_sum,
        value_changes=fv.value_changes,
    )
