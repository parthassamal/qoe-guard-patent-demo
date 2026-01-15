\
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

JSON = Any

@dataclass
class Change:
    path: str
    change_type: str  # added, removed, type_changed, value_changed
    before: Any = None
    after: Any = None

def _type_name(x: Any) -> str:
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

def _walk(before: JSON, after: JSON, path: str, changes: List[Change]) -> None:
    tb, ta = _type_name(before), _type_name(after)

    # Path exists only in one side
    if before is None and after is not None and path != "$":
        changes.append(Change(path=path, change_type="added", before=None, after=after))
        return
    if after is None and before is not None and path != "$":
        changes.append(Change(path=path, change_type="removed", before=before, after=None))
        return

    # Type mismatch
    if tb != ta:
        changes.append(Change(path=path, change_type="type_changed", before=before, after=after))
        return

    # Recurse
    if isinstance(before, dict) and isinstance(after, dict):
        keys = set(before.keys()) | set(after.keys())
        for k in sorted(keys):
            b = before.get(k, None)
            a = after.get(k, None)
            _walk(b, a, f"{path}.{k}", changes)
        return

    if isinstance(before, list) and isinstance(after, list):
        # Compare length, and then compare by index up to min length
        if len(before) != len(after):
            changes.append(Change(path=f"{path}.__len__", change_type="value_changed", before=len(before), after=len(after)))
        n = min(len(before), len(after))
        for i in range(n):
            _walk(before[i], after[i], f"{path}[{i}]", changes)
        return

    # Primitive value
    if before != after:
        changes.append(Change(path=path, change_type="value_changed", before=before, after=after))

def diff_json(baseline: JSON, candidate: JSON) -> List[Change]:
    changes: List[Change] = []
    _walk(baseline, candidate, "$", changes)
    # filter root-only null artifacts
    return [c for c in changes if c.path != "$"]
