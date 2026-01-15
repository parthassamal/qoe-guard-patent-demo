\
from __future__ import annotations
import json
import time
import uuid
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

def get_scenario(scenario_id: str) -> Optional[Dict[str, Any]]:
    for s in list_scenarios():
        if s["scenario_id"] == scenario_id:
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
        for s in rows:
            if s.get("scenario_id") == scenario_id:
                s["endpoint"] = endpoint
                s["base_url"] = base_url
                s["name"] = name
                s["baseline_response"] = baseline_response
                s["tags"] = tags
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
            s["baseline_response"] = baseline_response
            s["tags"] = tags
            s["updated_at"] = int(time.time())
            _save(SCENARIOS_FILE, rows)
            return s

    s = {
        "scenario_id": str(uuid.uuid4()),
        "name": name,
        "base_url": base_url,
        "endpoint": endpoint,
        "baseline_response": baseline_response,
        "tags": tags,
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
    }
    rows.append(s)
    _save(SCENARIOS_FILE, rows)
    return s

def list_runs() -> List[Dict[str, Any]]:
    return _load(RUNS_FILE)

def add_run(run: Dict[str, Any]) -> Dict[str, Any]:
    rows = list_runs()
    rows.append(run)
    _save(RUNS_FILE, rows)
    return run

def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    for r in list_runs():
        if r["run_id"] == run_id:
            return r
    return None
