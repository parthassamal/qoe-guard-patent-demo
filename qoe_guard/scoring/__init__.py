"""
Scoring Module for QoE-Guard.

Provides brittleness scoring, QoE risk assessment, and drift classification.
"""
from .brittleness import compute_brittleness_score
from .qoe_risk import compute_qoe_risk
from .criticality import get_criticality_for_path, DEFAULT_CRITICALITY_PROFILES
from .drift import classify_drift, DriftType, DriftClassification

__all__ = [
    "compute_brittleness_score",
    "compute_qoe_risk",
    "get_criticality_for_path",
    "DEFAULT_CRITICALITY_PROFILES",
    "classify_drift",
    "DriftType",
    "DriftClassification",
]
