\
from __future__ import annotations
import json
import os
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from .diff import json_diff
from .features import extract_features, to_dict
from .model import score, Features
from .storage import upsert_scenario, list_scenarios, list_runs, add_run, get_run, get_scenario, delete_scenarios
from .webhooks import notify_from_env, ValidationResult
from .swagger_analyzer import analyze_swagger, to_dict as swagger_analysis_to_dict

templates = Jinja2Templates(directory=str(__import__("pathlib").Path(__file__).resolve().parent / "templates"))

app = FastAPI(
    title="QoE-Guard API",
    description="""
    **QoE-aware JSON Variance Analytics System for Streaming API Validation**
    
    Validates streaming API responses by measuring hierarchical JSON variance versus stored baselines,
    predicting QoE risk, and gating releases with PASS/WARN/FAIL decisions.
    
    ## Features
    - Hierarchical JSON diff with path-level change detection
    - Variance feature extraction (structural drift, type changes, numeric deltas)
    - QoE risk scoring with weighted model
    - Policy-based gating (PASS/WARN/FAIL)
    - Explainable reports with top signals and path-level diffs
    - Webhook notifications (Slack, Gmail, Discord, Teams)
    
    ## Quick Links
    - **Web UI**: Visit `/` for the interactive interface
    - **Swagger UI**: This page (`/docs`)
    - **ReDoc**: Alternative docs at `/redoc`
    - **OpenAPI Schema**: JSON schema at `/openapi.json`
    """,
    version="0.1.0",
    contact={
        "name": "QoE-Guard",
        "url": "https://github.com/parthassamal/qoe-guard-patent-demo",
    },
    license_info={
        "name": "MIT",
    },
    servers=[
        {"url": "http://localhost:8010", "description": "Local development"},
        {"url": "https://your-production-url.com", "description": "Production (update in code)"},
    ],
)

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

def _fetch_json(url: str, *, method: str = "GET", params: Dict[str, Any] | None = None, headers: Dict[str, str] | None = None, json_body: Any = None, timeout: float | None = None) -> Any:
    method = method.upper()
    if method == "GET":
        resp = requests.get(url, params=params or {}, headers=headers or {}, timeout=timeout or DEFAULT_TIMEOUT_SEC)
    elif method == "POST":
        resp = requests.post(url, params=params or {}, headers=headers or {}, json=json_body, timeout=timeout or DEFAULT_TIMEOUT_SEC)
    elif method == "PUT":
        resp = requests.put(url, params=params or {}, headers=headers or {}, json=json_body, timeout=timeout or DEFAULT_TIMEOUT_SEC)
    elif method == "DELETE":
        resp = requests.delete(url, params=params or {}, headers=headers or {}, timeout=timeout or DEFAULT_TIMEOUT_SEC)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")
    resp.raise_for_status()
    try:
        return resp.json()
    except Exception as e:
        raise ValueError(f"Response was not valid JSON from {url}: {e}") from e

def _human(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

@app.get(
    "/",
    response_class=HTMLResponse,
    tags=["Web UI"],
    summary="Main Web Interface",
    description="Interactive web UI for managing scenarios, running validations, and viewing reports.",
)
def index(request: Request):
    scenarios = list_scenarios()
    for s in scenarios:
        s["updated_at_human"] = _human(s.get("updated_at", int(time.time())))
        s["base_url"] = s.get("base_url") or DEFAULT_TARGET_BASE_URL
        s["name"] = s.get("name") or ""

    runs = list_runs()[-20:][::-1]
    scenarios_dict = {s["scenario_id"]: s for s in scenarios}
    for r in runs:
        r["created_at_human"] = _human(r.get("created_at", int(time.time())))
        # Add scenario name if scenario_id exists
        scenario_id = r.get("scenario_id")
        if scenario_id and scenario_id in scenarios_dict:
            r["scenario_name"] = scenarios_dict[scenario_id].get("name") or scenarios_dict[scenario_id].get("endpoint", "Unknown")
        else:
            r["scenario_name"] = r.get("scenario_name") or "Unknown"

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

    diff_result = json_diff(baseline, candidate)
    feats_vector = extract_features(diff_result)
    # Convert FeatureVector to Features for scoring
    feats = Features(
        critical_changes=feats_vector.critical_changes,
        type_changes=feats_vector.type_changes,
        removed_fields=feats_vector.removed_fields,
        added_fields=feats_vector.added_fields,
        array_len_changes=feats_vector.array_length_changes,
        numeric_delta_max=feats_vector.max_numeric_delta,
        numeric_delta_sum=0.0,  # Not calculated in extract_features
        value_changes=feats_vector.value_changes,
    )
    decision = score(feats)

    # Generate integer run_id (will be set by add_run if not provided)
    record = {
        "scenario_id": scenario["scenario_id"],
        "endpoint": scenario["endpoint"],
        "candidate_version": int(v),
        "created_at": int(time.time()),
        "risk_score": decision.risk_score,
        "action": decision.action,
        "reasons": decision.reasons,
        "features": to_dict(feats_vector),
        "changes": [
            {
                "path": c.path,
                "change_type": c.change_type,
                "before": json.dumps(c.old_value, ensure_ascii=False, indent=2) if isinstance(c.old_value, (dict, list)) else str(c.old_value),
                "after": json.dumps(c.new_value, ensure_ascii=False, indent=2) if isinstance(c.new_value, (dict, list)) else str(c.new_value),
            }
            for c in diff_result.changes
        ],
        "baseline": baseline,
        "candidate": candidate,
    }
    saved_run = add_run(record)
    run_id = saved_run["run_id"]
    return RedirectResponse(url=f"/runs/{run_id}/report", status_code=302)

@app.post(
    "/seed_custom",
    tags=["Scenarios"],
    summary="Create or update baseline scenario",
    description="""
    Create or update a baseline scenario from a live endpoint or pasted JSON.
    
    - If `baseline_json` is provided, it's used directly (no network call)
    - Otherwise, fetches from `base_url + endpoint` with optional headers/params
    - Headers are NOT stored (security: avoid persisting tokens)
    """,
)
def seed_custom(
    name: str = Form(...),
    tags: str = Form(""),
    base_url: str = Form(""),
    endpoint: str = Form(""),
    baseline_option: str = Form("live"),
    baseline_request_type: str = Form("GET"),
    baseline_params_json: str = Form(""),
    baseline_headers_json: str = Form(""),
    baseline_request_body_json: str = Form(""),
    baseline_json: str = Form(""),
):
    """
    Seed a baseline scenario either by fetching live JSON or by pasting JSON.

    Notes:
    - Headers are used only for the request and are NOT persisted to disk (avoid storing secrets).
    - Scenario name is required.
    """
    try:
        # Validate scenario name
        if not name or not name.strip():
            raise ValueError("Scenario name is required")
        
        # Determine baseline source
        use_live = baseline_option == "live"
        use_json = baseline_option == "json"
        
        tag_list = _parse_tags(tags)
        baseline = None
        
        # Preserve endpoint and base_url for scenario saving (needed even in JSON mode)
        saved_endpoint = endpoint.strip() if endpoint else ""
        saved_base_url = base_url.strip() if base_url else ""
        
        if use_json and baseline_json.strip():
            # Use provided JSON directly
            baseline = _parse_json_maybe(baseline_json, default={})
            if not isinstance(baseline, dict):
                raise ValueError("baseline_json must be a JSON object")
            # For JSON mode, use provided endpoint/base_url or defaults
            if not saved_endpoint:
                saved_endpoint = "/"
        elif use_live:
            # Fetch from endpoint
            saved_base_url = base_url.strip()
            saved_endpoint = endpoint.strip()
            if not saved_base_url:
                raise ValueError("Base URL is required for live request")
            if not saved_endpoint:
                raise ValueError("Endpoint path is required for live request")
            
            params = _parse_json_maybe(baseline_params_json, default={})
            if not isinstance(params, dict):
                raise ValueError("baseline_params_json must be a JSON object")
            headers = _parse_json_maybe(baseline_headers_json, default={})
            if not isinstance(headers, dict):
                raise ValueError("baseline_headers_json must be a JSON object")
            
            # Replace localhost with demo-target for Docker networking
            if "localhost:8001" in saved_base_url or "127.0.0.1:8001" in saved_base_url:
                saved_base_url = saved_base_url.replace("localhost:8001", "demo-target:8001").replace("127.0.0.1:8001", "demo-target:8001")
            
            url = _join_url(saved_base_url, saved_endpoint)
            
            # Make request based on type
            if baseline_request_type == "GET":
                baseline = _fetch_json(url, params=params, headers=headers)
            elif baseline_request_type in ("POST", "PUT"):
                request_body = _parse_json_maybe(baseline_request_body_json, default=None)
                if baseline_request_type == "POST":
                    baseline = _fetch_json(url, method="POST", params=params, headers=headers, json_body=request_body)
                else:
                    baseline = _fetch_json(url, method="PUT", params=params, headers=headers, json_body=request_body)
            elif baseline_request_type == "DELETE":
                baseline = _fetch_json(url, method="DELETE", params=params, headers=headers)
            else:
                raise ValueError(f"Unsupported request type: {baseline_request_type}")
        else:
            raise ValueError("Please select either 'Live Request' or 'Baseline JSON' for baseline")

        upsert_scenario(
            endpoint=saved_endpoint or "/",
            base_url=saved_base_url or "",
            name=name.strip(),
            baseline_response=baseline,
            tags=tag_list,
            baseline_endpoint=saved_endpoint or "/",
            candidate_endpoint=saved_endpoint or "/",
        )
        return _redirect_with_msg("Scenario saved")
    except Exception as e:
        return _redirect_with_error(str(e))

@app.post(
    "/update_scenario",
    tags=["Scenarios"],
    summary="Update scenario",
    description="Update a scenario's name, endpoints, and tags.",
)
def update_scenario(
    scenario_id: str = Form(...),
    name: str = Form(...),
    baseline_endpoint: str = Form(""),
    candidate_endpoint: str = Form(""),
    tags: str = Form(""),
):
    """Update an existing scenario."""
    try:
        scenario = get_scenario(scenario_id)
        if not scenario:
            return JSONResponse({"success": False, "error": "Scenario not found"}, status_code=404)
        
        tag_list = _parse_tags(tags)
        
        # Update scenario using upsert with scenario_id
        updated = upsert_scenario(
            endpoint=baseline_endpoint or scenario.get("endpoint", ""),
            baseline_response=scenario.get("baseline_response", {}),
            tags=tag_list,
            base_url=scenario.get("base_url"),
            name=name,
            scenario_id=scenario_id,
            baseline_endpoint=baseline_endpoint or scenario.get("endpoint", ""),
            candidate_endpoint=candidate_endpoint or baseline_endpoint or scenario.get("endpoint", ""),
        )
        
        return JSONResponse({"success": True, "scenario": updated})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.post(
    "/delete_scenarios",
    tags=["Scenarios"],
    summary="Delete selected scenarios",
    description="Delete one or more scenarios by their IDs.",
)
def delete_scenarios_endpoint(
    scenario_ids: str = Form(...),
):
    """
    Delete scenarios by their IDs (comma-separated).
    """
    try:
        ids_list = [sid.strip() for sid in scenario_ids.split(",") if sid.strip()]
        if not ids_list:
            return _redirect_with_error("No scenario IDs provided")
        
        deleted_count = delete_scenarios(ids_list)
        if deleted_count == 0:
            return _redirect_with_error("No scenarios were deleted. Check if the IDs are valid.")
        
        return _redirect_with_msg(f"Deleted {deleted_count} scenario(s)")
    except Exception as e:
        return _redirect_with_error(str(e))

@app.post(
    "/run_custom",
    tags=["Validation"],
    summary="Run validation against stored baseline",
    description="""
    Run a validation comparing a candidate response against a stored baseline scenario.
    
    - Selects scenario by `scenario_id`
    - Fetches candidate from URL (or uses `candidate_json` if provided)
    - Computes hierarchical diff → variance features → risk score → PASS/WARN/FAIL
    - Sends notifications (Slack/Gmail) if configured
    - Returns redirect to report page
    """,
)
def run_custom(
    request: Request,
    scenario_id: str = Form(...),
    candidate_base_url: str = Form(""),
    candidate_endpoint: str = Form(""),
    baseline_base_url: str = Form(""),
    baseline_endpoint: str = Form(""),
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
        scenario = get_scenario(scenario_id)
        if not scenario:
            raise ValueError("Scenario not found")

        headers = _parse_json_maybe(headers_json, default={})
        if not isinstance(headers, dict):
            raise ValueError("headers_json must be a JSON object")
        params = _parse_json_maybe(candidate_params_json, default={})
        if not isinstance(params, dict):
            raise ValueError("candidate_params_json must be a JSON object")

        # Use provided baseline/base_url and endpoint, or fall back to scenario defaults
        baseline_url = (baseline_base_url or scenario.get("base_url") or DEFAULT_TARGET_BASE_URL).strip()
        baseline_ep = (baseline_endpoint or scenario.get("endpoint") or DEFAULT_ENDPOINT).strip()
        
        candidate_url = (candidate_base_url or scenario.get("base_url") or DEFAULT_TARGET_BASE_URL).strip()
        candidate_ep = (candidate_endpoint or scenario.get("endpoint") or DEFAULT_ENDPOINT).strip()
        
        # Replace localhost with demo-target for Docker internal communication
        baseline_url = baseline_url.replace("localhost:8001", "demo-target:8001").replace("127.0.0.1:8001", "demo-target:8001")
        candidate_url = candidate_url.replace("localhost:8001", "demo-target:8001").replace("127.0.0.1:8001", "demo-target:8001")
        
        url = _join_url(candidate_url, candidate_ep)
        # Also replace localhost in the final URL
        url = url.replace("localhost:8001", "demo-target:8001").replace("127.0.0.1:8001", "demo-target:8001")

        baseline = scenario["baseline_response"]

        # Use pasted JSON if provided, otherwise fetch live
        if candidate_json.strip():
            candidate = _parse_json_maybe(candidate_json, default={})
            url = "(pasted JSON)"
        else:
            candidate = _fetch_json(url, params=params, headers=headers)

        diff_result = json_diff(baseline, candidate)
        feats_vector = extract_features(diff_result)
        # Convert FeatureVector to Features for scoring
        feats = Features(
            critical_changes=feats_vector.critical_changes,
            type_changes=feats_vector.type_changes,
            removed_fields=feats_vector.removed_fields,
            added_fields=feats_vector.added_fields,
            array_len_changes=feats_vector.array_length_changes,
            numeric_delta_max=feats_vector.max_numeric_delta,
            numeric_delta_sum=0.0,  # Not calculated in extract_features
            value_changes=feats_vector.value_changes,
        )
        decision = score(feats)

        # Build baseline URL
        baseline_full_url = _join_url(baseline_url, baseline_ep)
        
        # Generate integer run_id (will be set by add_run if not provided)
        record = {
            "scenario_id": scenario.get("scenario_id"),
            "scenario_name": scenario.get("name"),
            "scenario_base_url": scenario.get("base_url"),
            "endpoint": baseline_ep,  # Keep for backward compatibility
            "baseline_url": baseline_full_url,  # Full baseline URL
            "candidate_version": 0,
            "candidate_url": url,
            "candidate_params": params,
            "created_at": int(time.time()),
            "risk_score": decision.risk_score,
            "action": decision.action,
            "reasons": decision.reasons,
            "features": to_dict(feats_vector),
            "changes": [
                {
                    "path": c.path,
                    "change_type": c.change_type,
                    "before": json.dumps(c.old_value, ensure_ascii=False, indent=2) if isinstance(c.old_value, (dict, list)) else str(c.old_value),
                    "after": json.dumps(c.new_value, ensure_ascii=False, indent=2) if isinstance(c.new_value, (dict, list)) else str(c.new_value),
                }
                for c in diff_result.changes
            ],
            "baseline": baseline,
            "candidate": candidate,
        }
        saved_run = add_run(record)
        run_id = saved_run["run_id"]
        
        # Send notifications (Slack, Gmail, etc.)
        try:
            report_url = f"{request.base_url}runs/{run_id}/report" if hasattr(request, 'base_url') else None
            notify_result = ValidationResult(
                run_id=str(run_id),  # Convert to string for notification
                endpoint=baseline_ep,
                risk_score=decision.risk_score,
                action=decision.action,
                change_count=len(diff_result.changes),
                top_signals=decision.reasons.get("top_signals", []),
                report_url=str(report_url) if report_url else None,
            )
            notify_from_env(notify_result)
        except Exception as notify_err:
            # Don't fail the request if notifications fail
            print(f"Notification error: {notify_err}")
        
        # Check if this is an API request (from batch execution)
        # If request has Accept: application/json header, return JSON instead of redirect
        accept_header = request.headers.get("accept", "")
        if "application/json" in accept_header.lower():
            return JSONResponse({
                "success": True,
                "run_id": run_id,
                "risk_score": decision.risk_score,
                "action": decision.action,
                "message": "Validation run completed successfully"
            })
        
        return RedirectResponse(url=f"/runs/{run_id}/report", status_code=302)
    except Exception as e:
        # Check if this is an API request
        accept_header = request.headers.get("accept", "")
        if "application/json" in accept_header.lower():
            return JSONResponse({
                "success": False,
                "error": str(e)
            }, status_code=400)
        return _redirect_with_error(str(e))

@app.post(
    "/api/swagger/analyze",
    tags=["Swagger Analyzer"],
    summary="Analyze Swagger/OpenAPI specification",
    description="""
    Analyze a Swagger/OpenAPI specification and test all endpoints for:
    - Broken links (404, 500, etc.)
    - Authentication issues (401, 403)
    - Timeout issues
    - Invalid responses
    
    Returns analysis with endpoint health status and recommendations.
    """,
)
def analyze_swagger_endpoint(
    swagger_url: str = Form(""),
    swagger_json: str = Form(""),
    base_url: str = Form(""),
    headers_json: str = Form(""),
    timeout: int = Form(10),
    test_all: bool = Form(False),
):
    """Analyze Swagger/OpenAPI spec and test endpoints."""
    try:
        headers = _parse_json_maybe(headers_json, default={})
        if not isinstance(headers, dict):
            raise ValueError("headers_json must be a JSON object")
        
        # If swagger_json is provided, parse it and pass directly to analysis
        if swagger_json and swagger_json.strip():
            # Parse the JSON to validate it
            try:
                spec_data = json.loads(swagger_json.strip())
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON: {e}")
            
            # Import the analysis function components
            from .swagger_analyzer import (
                extract_endpoints, test_endpoint, EndpointStatus, 
                SwaggerAnalysis, EndpointTest
            )
            from .swagger.discovery import _is_openapi_spec
            
            if not _is_openapi_spec(spec_data):
                raise ValueError("Provided JSON is not a valid OpenAPI/Swagger specification")
            
            # Extract base URL from spec or use provided override
            spec_base_url = base_url.strip() or None
            if not spec_base_url and isinstance(spec_data, dict):
                servers = spec_data.get("servers", [])
                if servers and isinstance(servers, list) and len(servers) > 0:
                    spec_base_url = servers[0].get("url", "")
            
            # Extract endpoints from the spec
            if not spec_base_url:
                spec_base_url = "https://api.example.com"  # Default fallback
            
            endpoints = extract_endpoints(spec_data, spec_base_url)
            
            # Test endpoints
            endpoint_tests = []
            for endpoint in endpoints:
                method = endpoint.get("method", "GET")
                path = endpoint.get("path", "")
                full_url = endpoint.get("full_url", endpoint.get("url", ""))
                
                # Skip non-GET methods unless test_all is True
                if not test_all and method.upper() != "GET":
                    continue
                
                try:
                    test_result = test_endpoint(
                        method=method,
                        url=full_url,
                        headers=headers,
                        timeout=timeout,
                    )
                    endpoint_tests.append(test_result)
                except Exception as e:
                    endpoint_tests.append(EndpointTest(
                        method=method,
                        path=path,
                        url=full_url,
                        status=EndpointStatus.UNKNOWN,
                        error_message=str(e),
                    ))
            
            # Calculate statistics
            healthy_count = sum(1 for t in endpoint_tests if t.status == EndpointStatus.HEALTHY)
            broken_count = sum(1 for t in endpoint_tests if t.status == EndpointStatus.BROKEN)
            auth_required_count = sum(1 for t in endpoint_tests if t.status == EndpointStatus.AUTH_REQUIRED)
            
            # Generate recommendations
            recommendations = []
            if broken_count > 0:
                recommendations.append(f"{broken_count} endpoint(s) returned error status codes. Check server logs and endpoint implementations.")
            if auth_required_count > 0:
                recommendations.append(f"{auth_required_count} endpoint(s) require authentication. Ensure headers are properly configured.")
            if len(endpoint_tests) == 0:
                recommendations.append("No endpoints were tested. Check that your OpenAPI spec contains valid path definitions.")
            
            start_time = time.time()
            timeout_count = sum(1 for t in endpoint_tests if t.status == EndpointStatus.TIMEOUT)
            
            analysis = SwaggerAnalysis(
                swagger_url="(provided as JSON)",
                base_url=spec_base_url or "",
                total_endpoints=len(endpoints),
                tested_endpoints=len(endpoint_tests),
                healthy_count=healthy_count,
                broken_count=broken_count,
                auth_required_count=auth_required_count,
                timeout_count=timeout_count,
                endpoint_tests=endpoint_tests,
                analysis_time_sec=time.time() - start_time,
                recommendations=recommendations,
            )
        elif swagger_url and swagger_url.strip():
            analysis = analyze_swagger(
                swagger_url=swagger_url.strip(),
                base_url=base_url.strip() or None,
                headers=headers,
                timeout=timeout,
                test_all=test_all,
            )
        else:
            raise ValueError("Either swagger_url or swagger_json must be provided")
        
        return JSONResponse(swagger_analysis_to_dict(analysis))
        
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

@app.get("/swagger-analyzer", response_class=HTMLResponse)
def swagger_analyzer_page(request: Request):
    """Swagger analyzer UI page."""
    return templates.TemplateResponse("swagger_analyzer.html", {"request": request})

@app.get(
    "/api/runs/{run_id}",
    tags=["API"],
    summary="Get validation run by ID",
    description="Retrieve a validation run's complete data including risk score, decision, features, and changes.",
    response_description="Validation run data as JSON",
)
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


@app.post(
    "/api/test-request",
    tags=["API"],
    summary="Test API request",
    description="Make an API request server-side to avoid CORS issues. Returns request and response details.",
)
def test_request(
    request_url: str = Form(""),
    base_url: str = Form(""),
    endpoint: str = Form(""),
    request_method: str = Form("GET"),
    request_type: str = Form("GET"),  # Legacy support
    headers_json: str = Form(""),
    params_json: str = Form(""),
    request_body_json: str = Form(""),
):
    """Make an API request and return details."""
    import time
    from urllib.parse import urlparse, urlencode, urlunparse
    
    try:
        # Determine HTTP method (support both request_method and request_type for backward compatibility)
        method = request_method or request_type or "GET"
        
        # Parse JSON fields
        headers = {}
        params = {}
        body = None
        
        if headers_json.strip():
            try:
                headers = json.loads(headers_json)
            except json.JSONDecodeError as e:
                return JSONResponse(
                    {"error": f"Invalid Headers JSON: {str(e)}"},
                    status_code=400
                )
        
        if params_json.strip():
            try:
                params = json.loads(params_json)
            except json.JSONDecodeError as e:
                return JSONResponse(
                    {"error": f"Invalid Query Params JSON: {str(e)}"},
                    status_code=400
                )
        
        if request_body_json.strip() and method in ("POST", "PUT"):
            try:
                body = json.loads(request_body_json)
            except json.JSONDecodeError as e:
                return JSONResponse(
                    {"error": f"Invalid Request Body JSON: {str(e)}"},
                    status_code=400
                )
        
        # Build URL - support both single request_url or base_url + endpoint
        if request_url.strip():
            # Use single request_url field
            url = request_url.strip()
        elif base_url.strip() and endpoint.strip():
            # Use separate base_url and endpoint fields
            base_url_clean = base_url.strip()
            endpoint_clean = endpoint.strip()
            
            # Replace localhost with demo-target for Docker networking
            if "localhost:8001" in base_url_clean or "127.0.0.1:8001" in base_url_clean:
                base_url_clean = base_url_clean.replace("localhost:8001", "demo-target:8001").replace("127.0.0.1:8001", "demo-target:8001")
            
            url = base_url_clean.rstrip("/") + "/" + endpoint_clean.lstrip("/")
        else:
            return JSONResponse(
                {"error": "Either 'request_url' or both 'base_url' and 'endpoint' must be provided"},
                status_code=400
            )
        
        # Replace localhost in full URL if present
        if "localhost:8001" in url or "127.0.0.1:8001" in url:
            url = url.replace("localhost:8001", "demo-target:8001").replace("127.0.0.1:8001", "demo-target:8001")
        
        # Add query parameters if provided
        if params:
            parsed = urlparse(url)
            existing_params = {}
            if parsed.query:
                from urllib.parse import parse_qs
                existing_params = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(parsed.query).items()}
            existing_params.update(params)
            query_string = urlencode(existing_params)
            url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, query_string, parsed.fragment))
        
        # Prepare request
        request_headers = {
            "Content-Type": "application/json",
            **headers
        }
        
        # Make request
        start_time = time.time()
        try:
            if method == "GET":
                resp = requests.get(url, headers=request_headers, timeout=DEFAULT_TIMEOUT_SEC)
            elif method == "POST":
                resp = requests.post(url, headers=request_headers, json=body, timeout=DEFAULT_TIMEOUT_SEC)
            elif method == "PUT":
                resp = requests.put(url, headers=request_headers, json=body, timeout=DEFAULT_TIMEOUT_SEC)
            elif method == "DELETE":
                resp = requests.delete(url, headers=request_headers, timeout=DEFAULT_TIMEOUT_SEC)
            else:
                return JSONResponse(
                    {"error": f"Unsupported request method: {method}"},
                    status_code=400
                )
            duration_ms = int((time.time() - start_time) * 1000)
        except requests.exceptions.RequestException as e:
            return JSONResponse(
                {
                    "error": f"Request failed: {str(e)}",
                    "request_details": {
                        "method": method,
                        "url": url,
                        "headers": request_headers,
                        "params": params,
                        "body": body,
                    }
                },
                status_code=500
            )
        
        # Parse response
        response_headers = dict(resp.headers)
        try:
            response_body = resp.json()
        except:
            response_body = resp.text
        
        return JSONResponse({
            "success": True,
            "request": {
                "method": method,
                "url": url,
                "headers": request_headers,
                "params": params,
                "body": body,
            },
            "response": {
                "status_code": resp.status_code,
                "status_text": resp.reason,
                "headers": response_headers,
                "body": response_body,
                "duration_ms": duration_ms,
            }
        })
        
    except Exception as e:
        return JSONResponse(
            {"error": f"Unexpected error: {str(e)}"},
            status_code=500
        )


@app.post(
    "/api/dry-run",
    tags=["API"],
    summary="Dry run validation without saving",
    description="Run a validation comparison between baseline and candidate responses without saving to disk. Returns full validation results including risk score, status, and audit data.",
)
def dry_run_validation(
    baseline_json: str = Form(""),
    candidate_json: str = Form(""),
    baseline_base_url: str = Form(""),
    baseline_endpoint: str = Form(""),
    baseline_request_type: str = Form("GET"),
    baseline_params_json: str = Form(""),
    baseline_headers_json: str = Form(""),
    baseline_request_body_json: str = Form(""),
    candidate_base_url: str = Form(""),
    candidate_endpoint: str = Form(""),
    candidate_request_type: str = Form("GET"),
    candidate_params_json: str = Form(""),
    candidate_headers_json: str = Form(""),
    candidate_request_body_json: str = Form(""),
):
    """Run a dry-run validation without saving results."""
    try:
        # Get baseline
        baseline = None
        baseline_request_details = {}
        
        if baseline_json.strip():
            # Use provided JSON
            baseline = _parse_json_maybe(baseline_json, default={})
            if not isinstance(baseline, dict):
                raise ValueError("baseline_json must be a JSON object")
            baseline_request_details = {
                "method": "JSON",
                "url": "(pasted JSON)",
                "headers": {},
                "params": {},
                "body": None,
            }
        elif baseline_base_url.strip() and baseline_endpoint.strip():
            # Fetch from endpoint
            base_url = baseline_base_url.strip()
            endpoint = baseline_endpoint.strip()
            
            # Replace localhost with demo-target for Docker networking
            if "localhost:8001" in base_url or "127.0.0.1:8001" in base_url:
                base_url = base_url.replace("localhost:8001", "demo-target:8001").replace("127.0.0.1:8001", "demo-target:8001")
            
            params = _parse_json_maybe(baseline_params_json, default={})
            headers = _parse_json_maybe(baseline_headers_json, default={})
            request_body = _parse_json_maybe(baseline_request_body_json, default=None)
            
            url = _join_url(base_url, endpoint)
            if params:
                from urllib.parse import urlencode
                url += "?" + urlencode(params)
            
            baseline_request_details = {
                "method": baseline_request_type,
                "url": url,
                "headers": headers,
                "params": params,
                "body": request_body,
            }
            
            # Fetch baseline
            if baseline_request_type == "GET":
                baseline = _fetch_json(url, params=params, headers=headers)
            elif baseline_request_type == "POST":
                baseline = _fetch_json(url, method="POST", params=params, headers=headers, json_body=request_body)
            elif baseline_request_type == "PUT":
                baseline = _fetch_json(url, method="PUT", params=params, headers=headers, json_body=request_body)
            elif baseline_request_type == "DELETE":
                baseline = _fetch_json(url, method="DELETE", params=params, headers=headers)
            else:
                raise ValueError(f"Unsupported baseline request type: {baseline_request_type}")
        else:
            raise ValueError("Either baseline_json or both baseline_base_url and baseline_endpoint must be provided")
        
        # Get candidate
        candidate = None
        candidate_request_details = {}
        
        if candidate_json.strip():
            # Use provided JSON
            candidate = _parse_json_maybe(candidate_json, default={})
            if not isinstance(candidate, dict):
                raise ValueError("candidate_json must be a JSON object")
            candidate_request_details = {
                "method": "JSON",
                "url": "(pasted JSON)",
                "headers": {},
                "params": {},
                "body": None,
            }
        elif candidate_base_url.strip() and candidate_endpoint.strip():
            # Fetch from endpoint
            base_url = candidate_base_url.strip()
            endpoint = candidate_endpoint.strip()
            
            # Replace localhost with demo-target for Docker networking
            if "localhost:8001" in base_url or "127.0.0.1:8001" in base_url:
                base_url = base_url.replace("localhost:8001", "demo-target:8001").replace("127.0.0.1:8001", "demo-target:8001")
            
            params = _parse_json_maybe(candidate_params_json, default={})
            headers = _parse_json_maybe(candidate_headers_json, default={})
            request_body = _parse_json_maybe(candidate_request_body_json, default=None)
            
            url = _join_url(base_url, endpoint)
            if params:
                from urllib.parse import urlencode
                url += "?" + urlencode(params)
            
            candidate_request_details = {
                "method": candidate_request_type,
                "url": url,
                "headers": headers,
                "params": params,
                "body": request_body,
            }
            
            # Fetch candidate
            if candidate_request_type == "GET":
                candidate = _fetch_json(url, params=params, headers=headers)
            elif candidate_request_type == "POST":
                candidate = _fetch_json(url, method="POST", params=params, headers=headers, json_body=request_body)
            elif candidate_request_type == "PUT":
                candidate = _fetch_json(url, method="PUT", params=params, headers=headers, json_body=request_body)
            elif candidate_request_type == "DELETE":
                candidate = _fetch_json(url, method="DELETE", params=params, headers=headers)
            else:
                raise ValueError(f"Unsupported candidate request type: {candidate_request_type}")
        else:
            raise ValueError("Either candidate_json or both candidate_base_url and candidate_endpoint must be provided")
        
        # Run validation
        diff_result = json_diff(baseline, candidate)
        feats_vector = extract_features(diff_result)
        # Convert FeatureVector to Features for scoring
        feats = Features(
            critical_changes=feats_vector.critical_changes,
            type_changes=feats_vector.type_changes,
            removed_fields=feats_vector.removed_fields,
            added_fields=feats_vector.added_fields,
            array_len_changes=feats_vector.array_length_changes,
            numeric_delta_max=feats_vector.max_numeric_delta,
            numeric_delta_sum=0.0,  # Not calculated in extract_features
            value_changes=feats_vector.value_changes,
        )
        decision = score(feats)
        
        # Format changes for display
        changes = [
            {
                "path": c.path,
                "change_type": c.change_type,
                "before": json.dumps(c.old_value, ensure_ascii=False, indent=2) if isinstance(c.old_value, (dict, list)) else str(c.old_value) if c.old_value is not None else None,
                "after": json.dumps(c.new_value, ensure_ascii=False, indent=2) if isinstance(c.new_value, (dict, list)) else str(c.new_value) if c.new_value is not None else None,
            }
            for c in diff_result.changes
        ]
        
        return JSONResponse({
            "success": True,
            "baseline": {
                "request": baseline_request_details,
                "response": baseline,
            },
            "candidate": {
                "request": candidate_request_details,
                "response": candidate,
            },
            "validation": {
                "risk_score": decision.risk_score,
                "status": decision.action,
                "reasons": decision.reasons,
                "features": to_dict(feats_vector),
                "changes": changes,
                "change_count": len(changes),
            }
        })
        
    except Exception as e:
        return JSONResponse(
            {"error": f"Dry run validation failed: {str(e)}"},
            status_code=500
        )
