\
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SCENARIOS_FILE = DATA_DIR / "scenarios.json"
RUNS_FILE = DATA_DIR / "runs.json"

def _ensure() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not SCENARIOS_FILE.exists():
        SCENARIOS_FILE.write_text("[]", encoding="utf-8")
    if not RUNS_FILE.exists():
        RUNS_FILE.write_text("[]", encoding="utf-8")

def _load(path: Path) -> List[Dict[str, Any]]:
    _ensure()
    return json.loads(path.read_text(encoding="utf-8"))

def _save(path: Path, rows: List[Dict[str, Any]]) -> None:
    _ensure()
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

def list_scenarios() -> List[Dict[str, Any]]:
    return _load(SCENARIOS_FILE)

def get_scenario(scenario_id: str | int) -> Optional[Dict[str, Any]]:
    scenario_id_int = int(scenario_id) if isinstance(scenario_id, str) and scenario_id.isdigit() else scenario_id
    for s in list_scenarios():
        s_id = s.get("scenario_id")
        # Handle both string and integer IDs for backward compatibility
        if (isinstance(s_id, int) and s_id == scenario_id_int) or (isinstance(s_id, str) and (s_id == str(scenario_id) or (s_id.isdigit() and int(s_id) == scenario_id_int))):
            return s
    return None

def upsert_scenario(
    endpoint: str,
    baseline_response: Dict[str, Any],
    tags: List[str] | None = None,
    *,
    base_url: str | None = None,
    name: str | None = None,
    scenario_id: str | None = None,
    baseline_endpoint: str | None = None,
    candidate_endpoint: str | None = None,
) -> Dict[str, Any]:
    """
    Creates or updates a scenario.

    Backward compatible with the original demo schema: older scenarios may not have `base_url`/`name`.
    """
    tags = tags or []
    rows = list_scenarios()

    def _key(s: Dict[str, Any]) -> Tuple[str | None, str, str | None]:
        return (s.get("base_url"), s.get("endpoint"), s.get("name"))

    # Prefer explicit scenario_id update
    if scenario_id:
        scenario_id_int = int(scenario_id) if isinstance(scenario_id, str) and scenario_id.isdigit() else scenario_id
        for s in rows:
            s_id = s.get("scenario_id")
            # Handle both string and integer IDs for backward compatibility
            if (isinstance(s_id, int) and s_id == scenario_id_int) or (isinstance(s_id, str) and (s_id == str(scenario_id) or (s_id.isdigit() and int(s_id) == scenario_id_int))):
                s["endpoint"] = endpoint  # Keep for backward compatibility
                s["base_url"] = base_url
                s["name"] = name
                s["baseline_response"] = baseline_response
                s["tags"] = tags
                if baseline_endpoint is not None:
                    s["baseline_endpoint"] = baseline_endpoint
                if candidate_endpoint is not None:
                    s["candidate_endpoint"] = candidate_endpoint
                s["updated_at"] = int(time.time())
                _save(SCENARIOS_FILE, rows)
                return s

    # Otherwise, upsert by identity (base_url + endpoint + name); fallback to endpoint-only for legacy rows
    for s in rows:
        same_identity = _key(s) == (base_url, endpoint, name)
        legacy_match = (s.get("base_url") is None and s.get("name") is None and s.get("endpoint") == endpoint)
        if same_identity or legacy_match:
            s["base_url"] = base_url
            s["name"] = name
            s["endpoint"] = endpoint  # Keep for backward compatibility
            s["baseline_response"] = baseline_response
            s["tags"] = tags
            if baseline_endpoint is not None:
                s["baseline_endpoint"] = baseline_endpoint
            if candidate_endpoint is not None:
                s["candidate_endpoint"] = candidate_endpoint
            s["updated_at"] = int(time.time())
            _save(SCENARIOS_FILE, rows)
            return s

    # Generate integer ID starting from 1
    existing_ids = [int(s.get("scenario_id", 0)) for s in rows if isinstance(s.get("scenario_id"), (int, str)) and str(s.get("scenario_id", "")).isdigit()]
    new_id = max(existing_ids) + 1 if existing_ids else 1
    
    s = {
        "scenario_id": new_id,
        "name": name,
        "base_url": base_url,
        "endpoint": endpoint,  # Keep for backward compatibility
        "baseline_endpoint": endpoint,  # New field
        "candidate_endpoint": endpoint,  # New field (defaults to same as baseline)
        "baseline_response": baseline_response,
        "tags": tags,
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
    }
    rows.append(s)
    _save(SCENARIOS_FILE, rows)
    return s

def delete_scenarios(scenario_ids: List[str | int]) -> int:
    """
    Delete scenarios by their IDs.
    Returns the number of scenarios deleted.
    """
    rows = list_scenarios()
    original_count = len(rows)
    
    # Convert all IDs to integers for comparison
    ids_to_delete = []
    for sid in scenario_ids:
        if isinstance(sid, str) and sid.isdigit():
            ids_to_delete.append(int(sid))
        elif isinstance(sid, int):
            ids_to_delete.append(sid)
        else:
            ids_to_delete.append(sid)  # Keep as string for UUID compatibility
    
    # Filter out scenarios to delete
    rows = [s for s in rows if s.get("scenario_id") not in ids_to_delete]
    
    _save(SCENARIOS_FILE, rows)
    return original_count - len(rows)

def list_runs() -> List[Dict[str, Any]]:
    return _load(RUNS_FILE)

def add_run(run: Dict[str, Any]) -> Dict[str, Any]:
    rows = list_runs()
    
    # Generate integer ID if not provided
    if "run_id" not in run or not run.get("run_id"):
        existing_ids = []
        for r in rows:
            rid = r.get("run_id")
            # Handle both integer and string IDs (for backward compatibility with UUIDs)
            if isinstance(rid, int):
                existing_ids.append(rid)
            elif isinstance(rid, str) and rid.isdigit():
                existing_ids.append(int(rid))
        new_id = max(existing_ids) + 1 if existing_ids else 1
        run["run_id"] = new_id
    else:
        # If run_id is provided as string and is numeric, convert to int
        provided_id = run.get("run_id")
        if isinstance(provided_id, str) and provided_id.isdigit():
            run["run_id"] = int(provided_id)
    
    rows.append(run)
    _save(RUNS_FILE, rows)
    return run

def get_run(run_id: str | int) -> Optional[Dict[str, Any]]:
    """
    Get a run by ID. Supports both integer and string IDs for backward compatibility.
    """
    # Convert to integer if it's a numeric string
    run_id_int = None
    if isinstance(run_id, str) and run_id.isdigit():
        run_id_int = int(run_id)
    elif isinstance(run_id, int):
        run_id_int = run_id
    
    for r in list_runs():
        rid = r.get("run_id")
        # Match by exact value (int or string)
        if rid == run_id:
            return r
        # Also match if both are numeric and equal
        if run_id_int is not None:
            if isinstance(rid, int) and rid == run_id_int:
                return r
            elif isinstance(rid, str) and rid.isdigit() and int(rid) == run_id_int:
                return r
    return None

def migrate_run_ids_to_integers() -> int:
    """
    Migrate all existing run IDs from UUIDs (or any format) to sequential integers starting from 1.
    Returns the number of runs updated.
    """
    rows = list_runs()
    if not rows:
        return 0
    
    # Update each run with a sequential integer ID
    for idx, run in enumerate(rows, start=1):
        run["run_id"] = idx
    
    _save(RUNS_FILE, rows)
    return len(rows)
