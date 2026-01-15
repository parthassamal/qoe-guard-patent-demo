\
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
from .features import Features

@dataclass
class Decision:
    risk_score: float  # 0..1
    action: str        # PASS/WARN/FAIL
    reasons: Dict[str, Any]

# Interpretable "QoE-aware" weights (demo)
# In a production system, these weights would be learned from historical variance + QoE outcomes.
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
    import math
    return 1.0 / (1.0 + math.exp(-x))

def score(features: Features) -> Decision:
    # Simple linear + sigmoid
    x = 0.0
    x += WEIGHTS["critical_changes"] * features.critical_changes
    x += WEIGHTS["type_changes"] * features.type_changes
    x += WEIGHTS["removed_fields"] * features.removed_fields
    x += WEIGHTS["added_fields"] * features.added_fields
    x += WEIGHTS["array_len_changes"] * features.array_len_changes
    x += WEIGHTS["numeric_delta_max"] * min(features.numeric_delta_max / 5.0, 10.0)  # scale
    x += WEIGHTS["numeric_delta_sum"] * min(features.numeric_delta_sum / 10.0, 10.0)
    x += WEIGHTS["value_changes"] * min(features.value_changes / 10.0, 10.0)

    # bias: default low risk unless evidence
    x -= 1.2

    risk = _sigmoid(x)

    # Policy thresholds (demo)
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
