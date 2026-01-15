"""
OpenAPI/Swagger Discovery Module.

Discovers OpenAPI documents from various sources:
- Direct OpenAPI JSON/YAML URLs
- Swagger UI pages (discovers underlying spec)
- FastAPI /docs pages
- ReDoc pages
"""
from __future__ import annotations

import re
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse

import requests
import yaml


@dataclass
class DiscoveryResult:
    """Result of OpenAPI discovery."""
    spec: Dict[str, Any]
    doc_url: str
    source_url: str
    trace: List[Dict[str, str]] = field(default_factory=list)
    format: str = "json"  # json or yaml


class DiscoveryError(Exception):
    """Error during OpenAPI discovery."""
    pass


def discover_openapi_spec(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
) -> DiscoveryResult:
    """
    Discover OpenAPI specification from a URL.
    
    Supports:
    - Direct OpenAPI JSON/YAML URLs
    - Swagger UI HTML pages
    - FastAPI /docs pages
    - ReDoc HTML pages
    
    Args:
        url: URL to discover from
        headers: Optional HTTP headers
        timeout: Request timeout in seconds
    
    Returns:
        DiscoveryResult with parsed spec and metadata
    
    Raises:
        DiscoveryError: If spec cannot be discovered
    """
    trace = []
    headers = headers or {}
    
    try:
        # First, try to fetch the URL
        trace.append({"action": "fetch", "url": url})
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        
        content_type = resp.headers.get("content-type", "").lower()
        
        # Check if it's already an OpenAPI spec
        if "json" in content_type or url.endswith(".json"):
            try:
                spec = resp.json()
                if _is_openapi_spec(spec):
                    trace.append({"action": "parsed", "type": "direct_json"})
                    return DiscoveryResult(
                        spec=spec,
                        doc_url=url,
                        source_url=url,
                        trace=trace,
                        format="json",
                    )
            except json.JSONDecodeError:
                pass
        
        if "yaml" in content_type or url.endswith((".yaml", ".yml")):
            try:
                spec = yaml.safe_load(resp.text)
                if _is_openapi_spec(spec):
                    trace.append({"action": "parsed", "type": "direct_yaml"})
                    return DiscoveryResult(
                        spec=spec,
                        doc_url=url,
                        source_url=url,
                        trace=trace,
                        format="yaml",
                    )
            except yaml.YAMLError:
                pass
        
        # Check if it's an HTML page (Swagger UI, FastAPI docs, ReDoc)
        if "html" in content_type or resp.text.strip().startswith("<!"):
            trace.append({"action": "detected", "type": "html_page"})
            
            # Try to find OpenAPI URL in the HTML
            spec_url = _find_spec_url_in_html(resp.text, url)
            
            if spec_url:
                trace.append({"action": "discovered", "url": spec_url})
                
                # Fetch the discovered spec
                spec_resp = requests.get(spec_url, headers=headers, timeout=timeout)
                spec_resp.raise_for_status()
                
                # Parse the spec
                try:
                    spec = spec_resp.json()
                    if _is_openapi_spec(spec):
                        trace.append({"action": "parsed", "type": "discovered_json"})
                        return DiscoveryResult(
                            spec=spec,
                            doc_url=spec_url,
                            source_url=url,
                            trace=trace,
                            format="json",
                        )
                except json.JSONDecodeError:
                    pass
                
                try:
                    spec = yaml.safe_load(spec_resp.text)
                    if _is_openapi_spec(spec):
                        trace.append({"action": "parsed", "type": "discovered_yaml"})
                        return DiscoveryResult(
                            spec=spec,
                            doc_url=spec_url,
                            source_url=url,
                            trace=trace,
                            format="yaml",
                        )
                except yaml.YAMLError:
                    pass
        
        # Try common OpenAPI paths relative to the URL
        base_url = _get_base_url(url)
        common_paths = [
            "/openapi.json",
            "/swagger.json",
            "/api-docs",
            "/v3/api-docs",
            "/v2/api-docs",
            "/api/openapi.json",
            "/api/swagger.json",
            "/docs/openapi.json",
        ]
        
        for path in common_paths:
            try_url = urljoin(base_url, path)
            trace.append({"action": "probe", "url": try_url})
            
            try:
                probe_resp = requests.get(try_url, headers=headers, timeout=10)
                if probe_resp.status_code == 200:
                    try:
                        spec = probe_resp.json()
                        if _is_openapi_spec(spec):
                            trace.append({"action": "found", "url": try_url})
                            return DiscoveryResult(
                                spec=spec,
                                doc_url=try_url,
                                source_url=url,
                                trace=trace,
                                format="json",
                            )
                    except json.JSONDecodeError:
                        pass
            except requests.RequestException:
                continue
        
        raise DiscoveryError(f"Could not discover OpenAPI spec from {url}")
        
    except requests.RequestException as e:
        raise DiscoveryError(f"HTTP error during discovery: {str(e)}")


def _is_openapi_spec(data: Any) -> bool:
    """Check if data looks like an OpenAPI spec."""
    if not isinstance(data, dict):
        return False
    
    # OpenAPI 3.x
    if "openapi" in data and "paths" in data:
        return True
    
    # Swagger 2.0
    if "swagger" in data and "paths" in data:
        return True
    
    return False


def _get_base_url(url: str) -> str:
    """Extract base URL (scheme + host) from URL."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _find_spec_url_in_html(html: str, base_url: str) -> Optional[str]:
    """
    Find OpenAPI spec URL in HTML content.
    
    Looks for:
    - SwaggerUIBundle config
    - FastAPI OpenAPI URL
    - ReDoc spec-url attribute
    - Direct links to openapi.json/swagger.json
    """
    # SwaggerUIBundle url configuration
    patterns = [
        # SwaggerUI: url: "..."
        r'url:\s*["\']([^"\']+\.json)["\']',
        r'url:\s*["\']([^"\']+/openapi)["\']',
        r'url:\s*["\']([^"\']+/swagger)["\']',
        r'url:\s*["\']([^"\']+api-docs[^"\']*)["\']',
        
        # FastAPI: window.__OPENAPI_URL__ = "..."
        r'__OPENAPI_URL__\s*=\s*["\']([^"\']+)["\']',
        
        # ReDoc: spec-url="..."
        r'spec-url=["\']([^"\']+)["\']',
        
        # Generic: href to openapi.json or swagger.json
        r'href=["\']([^"\']*openapi\.json)["\']',
        r'href=["\']([^"\']*swagger\.json)["\']',
        
        # configUrl for Swagger UI
        r'configUrl:\s*["\']([^"\']+)["\']',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            spec_url = match.group(1)
            # Make absolute URL
            if not spec_url.startswith(("http://", "https://")):
                spec_url = urljoin(base_url, spec_url)
            return spec_url
    
    return None


def discover_from_swagger_config(
    config_url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
) -> DiscoveryResult:
    """
    Discover OpenAPI spec from a Swagger config URL.
    
    Some Swagger UI deployments use a config file that points to the spec.
    """
    headers = headers or {}
    trace = [{"action": "fetch_config", "url": config_url}]
    
    try:
        resp = requests.get(config_url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        
        config = resp.json()
        
        # Look for spec URL in config
        spec_url = config.get("url") or config.get("urls", [{}])[0].get("url")
        
        if spec_url:
            if not spec_url.startswith(("http://", "https://")):
                spec_url = urljoin(config_url, spec_url)
            
            return discover_openapi_spec(spec_url, headers, timeout)
        
        raise DiscoveryError("No spec URL found in config")
        
    except requests.RequestException as e:
        raise DiscoveryError(f"Error fetching config: {str(e)}")
