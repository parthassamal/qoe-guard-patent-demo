"""
Feature Extraction Module.

Extracts numeric feature vectors from diff results for scoring and ML models.
"""
from typing import Optional
from .model import DiffResult, FeatureVector, Change


def extract_features(diff_result: DiffResult) -> FeatureVector:
    """
    Extract a feature vector from a diff result.
    
    Args:
        diff_result: The result of a JSON diff operation.
        
    Returns:
        FeatureVector with numeric features suitable for scoring.
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
    
    # Calculate numeric deltas (for value changes with numeric values)
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
    )


def features_to_dict(features: FeatureVector) -> dict:
    """Convert FeatureVector to a dictionary for serialization."""
    return {
        "total_changes": features.total_changes,
        "added_fields": features.added_fields,
        "removed_fields": features.removed_fields,
        "value_changes": features.value_changes,
        "type_changes": features.type_changes,
        "critical_changes": features.critical_changes,
        "breaking_changes": features.breaking_changes,
        "array_length_changes": features.array_length_changes,
        "max_numeric_delta": features.max_numeric_delta,
    }
