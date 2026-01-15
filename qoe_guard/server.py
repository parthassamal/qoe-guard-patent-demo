\
from __future__ import annotations
import json
import os
import time
import uuid
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from .diff import diff_json
from .features import extract_features, to_dict
from .model import score
from .storage import upsert_scenario, list_scenarios, list_runs, add_run, get_run
from .webhooks import notify_from_env, ValidationResult

templates = Jinja2Templates(directory=str(__import__("pathlib").Path(__file__).resolve().parent / "templates"))

app = FastAPI(title="QoE-Guard Patent Demo", version="0.1.0")

load_dotenv()

DEFAULT_TARGET_BASE_URL = os.getenv("QOE_GUARD_TARGET_BASE_URL") or os.getenv("TARGET_BASE_URL") or "http://127.0.0.1:8001"
DEFAULT_ENDPOINT = os.getenv("QOE_GUARD_ENDPOINT") or "/play"
DEFAULT_TIMEOUT_SEC = float(os.getenv("QOE_GUARD_HTTP_TIMEOUT_SEC") or "15")

def _redirect_with_error(msg: str) -> RedirectResponse:
    # keep URL-safe and reasonably short; avoid dumping secrets in error strings
    safe = (msg or "Unknown error").replace("\n", " ").strip()
    if len(safe) > 300:
        safe = safe[:300] + "…"
    return RedirectResponse(url=f"/?error={urllib.parse.quote_plus(safe)}", status_code=302)

def _redirect_with_msg(msg: str) -> RedirectResponse:
    safe = (msg or "").replace("\n", " ").strip()
    return RedirectResponse(url=f"/?msg={urllib.parse.quote_plus(safe)}", status_code=302)

def _parse_json_maybe(raw: str | None, *, default: Any) -> Any:
    if raw is None:
        return default
    s = raw.strip()
    if not s:
        return default
    try:
        return json.loads(s)
    except Exception as e:
        raise ValueError(f"Invalid JSON: {e}") from e

def _parse_tags(raw: str | None) -> List[str]:
    if not raw:
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]

def _join_url(base_url: str, endpoint: str) -> str:
    b = base_url.rstrip("/")
    ep = endpoint if endpoint.startswith("/") else f"/{endpoint}"
    return f"{b}{ep}"

def _fetch_json(url: str, *, params: Dict[str, Any] | None = None, headers: Dict[str, str] | None = None, timeout: float | None = None) -> Any:
    resp = requests.get(url, params=params or {}, headers=headers or {}, timeout=timeout or DEFAULT_TIMEOUT_SEC)
    resp.raise_for_status()
    try:
        return resp.json()
    except Exception as e:
        raise ValueError(f"Response was not valid JSON from {url}: {e}") from e

def _human(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    scenarios = list_scenarios()
    for s in scenarios:
        s["updated_at_human"] = _human(s.get("updated_at", int(time.time())))
        s["base_url"] = s.get("base_url") or DEFAULT_TARGET_BASE_URL
        s["name"] = s.get("name") or ""

    runs = list_runs()[-20:][::-1]
    for r in runs:
        r["created_at_human"] = _human(r.get("created_at", int(time.time())))

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "scenarios": scenarios,
            "runs": runs,
            "default_base_url": DEFAULT_TARGET_BASE_URL,
            "default_endpoint": DEFAULT_ENDPOINT,
            "error": request.query_params.get("error"),
            "msg": request.query_params.get("msg"),
        },
    )

@app.get("/seed")
def seed():
    # Seed baseline using v1 of the demo endpoint
    baseline = _fetch_json(_join_url(DEFAULT_TARGET_BASE_URL, DEFAULT_ENDPOINT), params={"v": 1})
    upsert_scenario(endpoint=DEFAULT_ENDPOINT, base_url=DEFAULT_TARGET_BASE_URL, baseline_response=baseline, tags=["baseline", "demo"], name="demo-play-v1")
    return RedirectResponse(url="/", status_code=302)

@app.get("/run")
def run_validation(v: int = 2):
    # Fetch baseline scenario
    scenarios = list_scenarios()
    if not scenarios:
        return RedirectResponse(url="/seed", status_code=302)
    scenario = scenarios[0]
    baseline = scenario["baseline_response"]

    # Fetch candidate response
    base_url = scenario.get("base_url") or DEFAULT_TARGET_BASE_URL
    candidate = _fetch_json(_join_url(base_url, scenario["endpoint"]), params={"v": v})

    changes = diff_json(baseline, candidate)
    feats = extract_features(changes)
    decision = score(feats)

    run_id = str(uuid.uuid4())
    record = {
        "run_id": run_id,
        "scenario_id": scenario["scenario_id"],
        "endpoint": scenario["endpoint"],
        "candidate_version": int(v),
        "created_at": int(time.time()),
        "risk_score": decision.risk_score,
        "action": decision.action,
        "reasons": decision.reasons,
        "features": to_dict(feats),
        "changes": [
            {
                "path": c.path,
                "change_type": c.change_type,
                "before": json.dumps(c.before, ensure_ascii=False, indent=2) if isinstance(c.before, (dict, list)) else str(c.before),
                "after": json.dumps(c.after, ensure_ascii=False, indent=2) if isinstance(c.after, (dict, list)) else str(c.after),
            }
            for c in changes
        ],
        "baseline": baseline,
        "candidate": candidate,
    }
    add_run(record)
    return RedirectResponse(url=f"/runs/{run_id}/report", status_code=302)

@app.post("/seed_custom")
def seed_custom(
    base_url: str = Form(...),
    endpoint: str = Form(...),
    name: str = Form(""),
    tags: str = Form(""),
    params_json: str = Form(""),
    headers_json: str = Form(""),
    baseline_json: str = Form(""),
):
    """
    Seed a baseline scenario either by fetching live JSON (GET base_url+endpoint) or by pasting JSON.

    Notes:
    - Headers are used only for the request and are NOT persisted to disk (avoid storing secrets).
    """
    try:
        base_url = base_url.strip()
        endpoint = endpoint.strip()
        if not base_url:
            raise ValueError("Base URL is required")
        if not endpoint:
            raise ValueError("Endpoint path is required")

        params = _parse_json_maybe(params_json, default={})
        if not isinstance(params, dict):
            raise ValueError("params_json must be a JSON object")
        headers = _parse_json_maybe(headers_json, default={})
        if not isinstance(headers, dict):
            raise ValueError("headers_json must be a JSON object")
        tag_list = _parse_tags(tags)

        if baseline_json.strip():
            baseline = _parse_json_maybe(baseline_json, default={})
        else:
            url = _join_url(base_url, endpoint)
            baseline = _fetch_json(url, params=params, headers=headers)

        upsert_scenario(
            endpoint=endpoint,
            base_url=base_url,
            name=name.strip() or None,
            baseline_response=baseline,
            tags=tag_list,
        )
        return _redirect_with_msg("Baseline saved")
    except Exception as e:
        return _redirect_with_error(str(e))

@app.post("/run_custom")
def run_custom(
    request: Request,
    scenario_id: str = Form(...),
    candidate_base_url: str = Form(""),
    candidate_endpoint: str = Form(""),
    candidate_params_json: str = Form(""),
    headers_json: str = Form(""),
    candidate_json: str = Form(""),
):
    """
    Run validation using a stored scenario baseline against a candidate response.

    If candidate_json is provided, use it directly (no network call).
    Otherwise, fetch from candidate_base_url + candidate_endpoint.

    Notes:
    - Headers are used only for the request and are NOT persisted to disk (avoid storing secrets).
    """
    try:
        scenario = None
        for s in list_scenarios():
            if s.get("scenario_id") == scenario_id:
                scenario = s
                break
        if not scenario:
            raise ValueError("Scenario not found")

        headers = _parse_json_maybe(headers_json, default={})
        if not isinstance(headers, dict):
            raise ValueError("headers_json must be a JSON object")
        params = _parse_json_maybe(candidate_params_json, default={})
        if not isinstance(params, dict):
            raise ValueError("candidate_params_json must be a JSON object")

        base_url = (candidate_base_url or scenario.get("base_url") or DEFAULT_TARGET_BASE_URL).strip()
        endpoint = (candidate_endpoint or scenario.get("endpoint") or DEFAULT_ENDPOINT).strip()
        url = _join_url(base_url, endpoint)

        baseline = scenario["baseline_response"]

        # Use pasted JSON if provided, otherwise fetch live
        if candidate_json.strip():
            candidate = _parse_json_maybe(candidate_json, default={})
            url = "(pasted JSON)"
        else:
            candidate = _fetch_json(url, params=params, headers=headers)

        changes = diff_json(baseline, candidate)
        feats = extract_features(changes)
        decision = score(feats)

        run_id = str(uuid.uuid4())
        record = {
            "run_id": run_id,
            "scenario_id": scenario.get("scenario_id"),
            "scenario_name": scenario.get("name"),
            "scenario_base_url": scenario.get("base_url"),
            "endpoint": endpoint,
            "candidate_version": 0,
            "candidate_url": url,
            "candidate_params": params,
            "created_at": int(time.time()),
            "risk_score": decision.risk_score,
            "action": decision.action,
            "reasons": decision.reasons,
            "features": to_dict(feats),
            "changes": [
                {
                    "path": c.path,
                    "change_type": c.change_type,
                    "before": json.dumps(c.before, ensure_ascii=False, indent=2) if isinstance(c.before, (dict, list)) else str(c.before),
                    "after": json.dumps(c.after, ensure_ascii=False, indent=2) if isinstance(c.after, (dict, list)) else str(c.after),
                }
                for c in changes
            ],
            "baseline": baseline,
            "candidate": candidate,
        }
        add_run(record)
        
        # Send notifications (Slack, Gmail, etc.)
        try:
            report_url = f"{request.base_url}runs/{run_id}/report" if hasattr(request, 'base_url') else None
            notify_result = ValidationResult(
                run_id=run_id,
                endpoint=endpoint,
                risk_score=decision.risk_score,
                action=decision.action,
                change_count=len(changes),
                top_signals=decision.reasons.get("top_signals", []),
                report_url=str(report_url) if report_url else None,
            )
            notify_from_env(notify_result)
        except Exception as notify_err:
            # Don't fail the request if notifications fail
            print(f"Notification error: {notify_err}")
        
        return RedirectResponse(url=f"/runs/{run_id}/report", status_code=302)
    except Exception as e:
        return _redirect_with_error(str(e))

@app.get("/api/runs/{run_id}")
def api_run(run_id: str):
    r = get_run(run_id)
    if not r:
        return JSONResponse({"error": "not found"}, status_code=404)
    return r

@app.get("/runs/{run_id}/report", response_class=HTMLResponse)
def report(request: Request, run_id: str):
    r = get_run(run_id)
    if not r:
        return HTMLResponse("<h1>Not found</h1><p><a href='/'>Back</a></p>", status_code=404)

    # Prepare pretty JSON
    r_view = dict(r)
    r_view["reasons_pretty"] = json.dumps(r.get("reasons", {}), indent=2, ensure_ascii=False)
    r_view["features_pretty"] = json.dumps(r.get("features", {}), indent=2, ensure_ascii=False)
    r_view["baseline_pretty"] = json.dumps(r.get("baseline", {}), indent=2, ensure_ascii=False)
    r_view["candidate_pretty"] = json.dumps(r.get("candidate", {}), indent=2, ensure_ascii=False)
    r_view["candidate_meta_pretty"] = json.dumps(
        {
            "candidate_url": r.get("candidate_url"),
            "candidate_params": r.get("candidate_params"),
            "scenario_id": r.get("scenario_id"),
            "scenario_name": r.get("scenario_name"),
            "scenario_base_url": r.get("scenario_base_url"),
        },
        indent=2,
        ensure_ascii=False,
    )

    return templates.TemplateResponse("report.html", {"request": request, "run": r_view})
