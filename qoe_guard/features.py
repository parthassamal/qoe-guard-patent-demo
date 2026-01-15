\
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
from .diff import Change, _type_name

@dataclass
class Features:
    added_fields: int
    removed_fields: int
    type_changes: int
    value_changes: int
    numeric_delta_sum: float
    numeric_delta_max: float
    array_len_changes: int
    critical_changes: int

CRITICAL_PATH_PREFIXES = [
    "$.playback",
    "$.entitlement",
    "$.drm",
    "$.ads",
]

def _is_critical(path: str) -> bool:
    return any(path.startswith(p) for p in CRITICAL_PATH_PREFIXES)

def extract_features(changes: List[Change]) -> Features:
    added = removed = typec = valc = 0
    num_sum = 0.0
    num_max = 0.0
    arr_len = 0
    critical = 0

    for c in changes:
        if _is_critical(c.path):
            critical += 1

        if c.change_type == "added":
            added += 1
        elif c.change_type == "removed":
            removed += 1
        elif c.change_type == "type_changed":
            typec += 1
        elif c.change_type == "value_changed":
            valc += 1
            # special array length markers
            if c.path.endswith(".__len__"):
                arr_len += 1
            # numeric deltas
            if isinstance(c.before, (int, float)) and isinstance(c.after, (int, float)):
                d = float(c.after) - float(c.before)
                num_sum += abs(d)
                num_max = max(num_max, abs(d))

    return Features(
        added_fields=added,
        removed_fields=removed,
        type_changes=typec,
        value_changes=valc,
        numeric_delta_sum=num_sum,
        numeric_delta_max=num_max,
        array_len_changes=arr_len,
        critical_changes=critical,
    )

def to_dict(f: Features) -> Dict[str, Any]:
    return {
        "added_fields": f.added_fields,
        "removed_fields": f.removed_fields,
        "type_changes": f.type_changes,
        "value_changes": f.value_changes,
        "numeric_delta_sum": round(f.numeric_delta_sum, 6),
        "numeric_delta_max": round(f.numeric_delta_max, 6),
        "array_len_changes": f.array_len_changes,
        "critical_changes": f.critical_changes,
    }
