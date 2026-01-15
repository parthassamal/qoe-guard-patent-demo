"""
Policy Configuration.

Defines configurable thresholds and rules for CI gating.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class PolicyConfig:
    """Policy configuration for validation gating."""
    
    # Identification
    name: str = "default"
    version: str = "1.0.0"
    description: Optional[str] = None
    
    # Brittleness thresholds (0-100)
    brittleness_fail_threshold: float = 75.0
    brittleness_warn_threshold: float = 50.0
    
    # QoE risk thresholds (0.0-1.0)
    qoe_fail_threshold: float = 0.72
    qoe_warn_threshold: float = 0.45
    
    # Override rules (force specific decisions)
    fail_on_critical_type_changes: bool = True
    fail_on_undocumented_drift: bool = True
    warn_on_spec_drift: bool = True
    fail_on_removed_critical_paths: bool = True
    
    # Minimum critical type changes to trigger override
    critical_type_change_threshold: int = 1
    
    # Minimum removed critical paths to trigger override
    removed_critical_threshold: int = 1
    
    # Allow-lists (paths/operations that bypass certain rules)
    allowed_drift_paths: List[str] = field(default_factory=list)
    skip_operations: List[str] = field(default_factory=list)
    
    # CI gate behavior
    ci_hard_gate: bool = True  # If True, FAIL blocks build; if False, only warns
    require_approval_on_warn: bool = False  # Require manual approval for WARN
    
    # Baseline promotion requirements
    min_stable_runs_for_promotion: int = 3
    max_qoe_degradation_for_promotion: float = 0.05  # Max increase in risk score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "brittleness_fail_threshold": self.brittleness_fail_threshold,
            "brittleness_warn_threshold": self.brittleness_warn_threshold,
            "qoe_fail_threshold": self.qoe_fail_threshold,
            "qoe_warn_threshold": self.qoe_warn_threshold,
            "fail_on_critical_type_changes": self.fail_on_critical_type_changes,
            "fail_on_undocumented_drift": self.fail_on_undocumented_drift,
            "warn_on_spec_drift": self.warn_on_spec_drift,
            "fail_on_removed_critical_paths": self.fail_on_removed_critical_paths,
            "critical_type_change_threshold": self.critical_type_change_threshold,
            "removed_critical_threshold": self.removed_critical_threshold,
            "allowed_drift_paths": self.allowed_drift_paths,
            "skip_operations": self.skip_operations,
            "ci_hard_gate": self.ci_hard_gate,
            "require_approval_on_warn": self.require_approval_on_warn,
            "min_stable_runs_for_promotion": self.min_stable_runs_for_promotion,
            "max_qoe_degradation_for_promotion": self.max_qoe_degradation_for_promotion,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PolicyConfig":
        """Create from dictionary."""
        return cls(
            name=data.get("name", "default"),
            version=data.get("version", "1.0.0"),
            description=data.get("description"),
            brittleness_fail_threshold=data.get("brittleness_fail_threshold", 75.0),
            brittleness_warn_threshold=data.get("brittleness_warn_threshold", 50.0),
            qoe_fail_threshold=data.get("qoe_fail_threshold", 0.72),
            qoe_warn_threshold=data.get("qoe_warn_threshold", 0.45),
            fail_on_critical_type_changes=data.get("fail_on_critical_type_changes", True),
            fail_on_undocumented_drift=data.get("fail_on_undocumented_drift", True),
            warn_on_spec_drift=data.get("warn_on_spec_drift", True),
            fail_on_removed_critical_paths=data.get("fail_on_removed_critical_paths", True),
            critical_type_change_threshold=data.get("critical_type_change_threshold", 1),
            removed_critical_threshold=data.get("removed_critical_threshold", 1),
            allowed_drift_paths=data.get("allowed_drift_paths", []),
            skip_operations=data.get("skip_operations", []),
            ci_hard_gate=data.get("ci_hard_gate", True),
            require_approval_on_warn=data.get("require_approval_on_warn", False),
            min_stable_runs_for_promotion=data.get("min_stable_runs_for_promotion", 3),
            max_qoe_degradation_for_promotion=data.get("max_qoe_degradation_for_promotion", 0.05),
        )


# Default policy instance
DEFAULT_POLICY = PolicyConfig()


# Strict policy for production environments
STRICT_POLICY = PolicyConfig(
    name="strict",
    version="1.0.0",
    description="Strict policy for production deployments",
    brittleness_fail_threshold=60.0,
    brittleness_warn_threshold=40.0,
    qoe_fail_threshold=0.60,
    qoe_warn_threshold=0.35,
    fail_on_critical_type_changes=True,
    fail_on_undocumented_drift=True,
    fail_on_removed_critical_paths=True,
    ci_hard_gate=True,
    require_approval_on_warn=True,
    min_stable_runs_for_promotion=5,
    max_qoe_degradation_for_promotion=0.02,
)


# Permissive policy for development
PERMISSIVE_POLICY = PolicyConfig(
    name="permissive",
    version="1.0.0",
    description="Permissive policy for development environments",
    brittleness_fail_threshold=90.0,
    brittleness_warn_threshold=70.0,
    qoe_fail_threshold=0.85,
    qoe_warn_threshold=0.60,
    fail_on_critical_type_changes=False,
    fail_on_undocumented_drift=False,
    warn_on_spec_drift=False,
    ci_hard_gate=False,
    require_approval_on_warn=False,
    min_stable_runs_for_promotion=1,
    max_qoe_degradation_for_promotion=0.20,
)
