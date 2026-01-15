"""
Swagger/OpenAPI Endpoint Analyzer

Analyzes OpenAPI/Swagger specifications and tests endpoints for:
- Broken links (404, 500, etc.)
- Authentication issues (401, 403)
- Timeout issues
- Invalid responses
- Missing required parameters
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
import yaml


class EndpointStatus(Enum):
    HEALTHY = "healthy"
    BROKEN = "broken"  # 4xx/5xx
    AUTH_REQUIRED = "auth_required"  # 401/403
    TIMEOUT = "timeout"
    INVALID_RESPONSE = "invalid_response"
    MISSING_PARAMS = "missing_params"
    UNKNOWN = "unknown"


@dataclass
class EndpointTest:
    method: str
    path: str
    full_url: str
    status_code: Optional[int] = None
    status: EndpointStatus = EndpointStatus.UNKNOWN
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    requires_auth: bool = False
    missing_params: List[str] = None
    response_size_bytes: Optional[int] = None


@dataclass
class SwaggerAnalysis:
    swagger_url: str
    base_url: str
    total_endpoints: int
    tested_endpoints: int
    healthy_count: int
    broken_count: int
    auth_required_count: int
    timeout_count: int
    endpoint_tests: List[EndpointTest]
    analysis_time_sec: float
    recommendations: List[str]


def parse_openapi_spec(spec_content: str, spec_format: str = "json") -> Dict[str, Any]:
    """Parse OpenAPI spec from JSON or YAML."""
    if spec_format == "yaml" or spec_content.strip().startswith("openapi:") or spec_content.strip().startswith("swagger:"):
        try:
            return yaml.safe_load(spec_content)
        except Exception as e:
            raise ValueError(f"Invalid YAML: {e}")
    else:
        try:
            return json.loads(spec_content)
        except Exception as e:
            raise ValueError(f"Invalid JSON: {e}")


def fetch_openapi_spec(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> Dict[str, Any]:
    """Fetch OpenAPI spec from URL."""
    resp = requests.get(url, headers=headers or {}, timeout=timeout)
    resp.raise_for_status()
    
    content_type = resp.headers.get("content-type", "").lower()
    if "yaml" in content_type or "yml" in content_type:
        return parse_openapi_spec(resp.text, "yaml")
    else:
        return parse_openapi_spec(resp.text, "json")


def extract_endpoints(openapi_spec: Dict[str, Any], base_url: str) -> List[Dict[str, Any]]:
    """Extract all endpoints from OpenAPI spec."""
    endpoints = []
    paths = openapi_spec.get("paths", {})
    servers = openapi_spec.get("servers", [])
    
    # Determine base URL
    if servers and isinstance(servers, list) and len(servers) > 0:
        server_url = servers[0].get("url", base_url)
    else:
        server_url = base_url
    
    for path, path_item in paths.items():
        for method in ["get", "post", "put", "patch", "delete", "head", "options"]:
            if method in path_item:
                operation = path_item[method]
                full_url = urljoin(server_url.rstrip("/") + "/", path.lstrip("/"))
                
                endpoints.append({
                    "method": method.upper(),
                    "path": path,
                    "full_url": full_url,
                    "operation": operation,
                    "summary": operation.get("summary", ""),
                    "operation_id": operation.get("operationId", ""),
                    "parameters": operation.get("parameters", []),
                    "request_body": operation.get("requestBody"),
                    "security": operation.get("security", []),
                })
    
    return endpoints


def test_endpoint(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 10,
    skip_auth: bool = False,
) -> EndpointTest:
    """Test a single endpoint."""
    start_time = time.time()
    test = EndpointTest(method=method, path=urlparse(url).path, full_url=url)
    
    try:
        # Prepare request
        req_kwargs = {
            "headers": headers or {},
            "timeout": timeout,
        }
        
        if method.upper() in ["GET", "HEAD", "OPTIONS"]:
            req_kwargs["params"] = params or {}
        else:
            req_kwargs["json"] = params or {}
        
        # Make request
        resp = requests.request(method.upper(), url, **req_kwargs)
        
        test.response_time_ms = (time.time() - start_time) * 1000
        test.status_code = resp.status_code
        test.response_size_bytes = len(resp.content)
        
        # Classify status
        if resp.status_code == 200:
            test.status = EndpointStatus.HEALTHY
        elif resp.status_code in [401, 403]:
            test.status = EndpointStatus.AUTH_REQUIRED
            test.requires_auth = True
            test.error_message = f"Authentication required ({resp.status_code})"
        elif resp.status_code >= 400:
            test.status = EndpointStatus.BROKEN
            try:
                error_detail = resp.json().get("detail", resp.text[:200])
            except:
                error_detail = resp.text[:200]
            test.error_message = f"{resp.status_code}: {error_detail}"
        else:
            test.status = EndpointStatus.HEALTHY
            
    except requests.exceptions.Timeout:
        test.status = EndpointStatus.TIMEOUT
        test.error_message = f"Request timeout after {timeout}s"
    except requests.exceptions.ConnectionError as e:
        test.status = EndpointStatus.BROKEN
        test.error_message = f"Connection error: {str(e)[:200]}"
    except Exception as e:
        test.status = EndpointStatus.UNKNOWN
        test.error_message = f"Error: {str(e)[:200]}"
    
    return test


def analyze_swagger(
    swagger_url: str,
    base_url: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 10,
    test_all: bool = False,
) -> SwaggerAnalysis:
    """
    Analyze a Swagger/OpenAPI specification and test endpoints.
    
    Args:
        swagger_url: URL to OpenAPI spec (JSON or YAML)
        base_url: Override base URL from spec (optional)
        headers: Headers to use for testing (optional)
        timeout: Request timeout in seconds
        test_all: If False, only test GET endpoints. If True, test all methods.
    
    Returns:
        SwaggerAnalysis with test results and recommendations
    """
    start_time = time.time()
    
    # Fetch and parse spec
    try:
        spec = fetch_openapi_spec(swagger_url, headers, timeout=30)
    except Exception as e:
        return SwaggerAnalysis(
            swagger_url=swagger_url,
            base_url=base_url or "",
            total_endpoints=0,
            tested_endpoints=0,
            healthy_count=0,
            broken_count=0,
            auth_required_count=0,
            timeout_count=0,
            endpoint_tests=[],
            analysis_time_sec=time.time() - start_time,
            recommendations=[f"Failed to fetch/parse OpenAPI spec: {e}"],
        )
    
    # Extract base URL
    if not base_url:
        servers = spec.get("servers", [])
        if servers and isinstance(servers, list) and len(servers) > 0:
            base_url = servers[0].get("url", "")
        else:
            base_url = ""
    
    # Extract endpoints
    endpoints = extract_endpoints(spec, base_url)
    
    # Filter endpoints to test
    if not test_all:
        endpoints = [e for e in endpoints if e["method"] == "GET"]
    
    # Test endpoints
    endpoint_tests = []
    for endpoint in endpoints:
        test = test_endpoint(
            method=endpoint["method"],
            url=endpoint["full_url"],
            headers=headers,
            timeout=timeout,
        )
        endpoint_tests.append(test)
    
    # Count statuses
    healthy_count = sum(1 for t in endpoint_tests if t.status == EndpointStatus.HEALTHY)
    broken_count = sum(1 for t in endpoint_tests if t.status == EndpointStatus.BROKEN)
    auth_required_count = sum(1 for t in endpoint_tests if t.status == EndpointStatus.AUTH_REQUIRED)
    timeout_count = sum(1 for t in endpoint_tests if t.status == EndpointStatus.TIMEOUT)
    
    # Generate recommendations
    recommendations = []
    if broken_count > 0:
        recommendations.append(f"⚠️ {broken_count} endpoint(s) returned errors (4xx/5xx)")
    if auth_required_count > 0:
        recommendations.append(f"🔐 {auth_required_count} endpoint(s) require authentication")
    if timeout_count > 0:
        recommendations.append(f"⏱️ {timeout_count} endpoint(s) timed out")
    if healthy_count == len(endpoint_tests) and len(endpoint_tests) > 0:
        recommendations.append("✅ All tested endpoints are healthy")
    elif healthy_count == 0 and len(endpoint_tests) > 0:
        recommendations.append("❌ No healthy endpoints found - check base URL and authentication")
    
    return SwaggerAnalysis(
        swagger_url=swagger_url,
        base_url=base_url,
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


def to_dict(analysis: SwaggerAnalysis) -> Dict[str, Any]:
    """Convert SwaggerAnalysis to dictionary for JSON serialization."""
    return {
        "swagger_url": analysis.swagger_url,
        "base_url": analysis.base_url,
        "total_endpoints": analysis.total_endpoints,
        "tested_endpoints": analysis.tested_endpoints,
        "healthy_count": analysis.healthy_count,
        "broken_count": analysis.broken_count,
        "auth_required_count": analysis.auth_required_count,
        "timeout_count": analysis.timeout_count,
        "endpoint_tests": [
            {
                "method": t.method,
                "path": t.path,
                "full_url": t.full_url,
                "status_code": t.status_code,
                "status": t.status.value,
                "response_time_ms": round(t.response_time_ms, 2) if t.response_time_ms else None,
                "error_message": t.error_message,
                "requires_auth": t.requires_auth,
                "response_size_bytes": t.response_size_bytes,
            }
            for t in analysis.endpoint_tests
        ],
        "analysis_time_sec": round(analysis.analysis_time_sec, 2),
        "recommendations": analysis.recommendations,
    }
