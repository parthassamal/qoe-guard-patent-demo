"""Scoring module for brittleness, QoE risk, and drift classification."""
from .brittleness import compute_brittleness_score, BrittlenessResult
from .qoe_risk import compute_qoe_risk, QoERiskResult
from .drift import classify_drift, DriftClassification, DriftType
from .criticality import (
    DEFAULT_CRITICALITY_PROFILES,
    get_criticality_weight,
    CriticalityProfiles,
)

__all__ = [
    "compute_brittleness_score",
    "BrittlenessResult",
    "compute_qoe_risk",
    "QoERiskResult",
    "classify_drift",
    "DriftClassification",
    "DriftType",
    "DEFAULT_CRITICALITY_PROFILES",
    "get_criticality_weight",
    "CriticalityProfiles",
]
