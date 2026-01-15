"""
Runtime HTTP Request Runner.

Executes HTTP requests with timing, error handling, and response capture.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

import requests


@dataclass
class RuntimeResult:
    """Result of a runtime HTTP request."""
    success: bool
    status_code: Optional[int] = None
    headers: Optional[Dict[str, str]] = None
    body: Optional[Any] = None
    body_raw: Optional[str] = None
    
    # Timings (milliseconds)
    response_time_ms: Optional[float] = None
    connect_time_ms: Optional[float] = None
    
    # Error info
    error: Optional[str] = None
    error_type: Optional[str] = None  # timeout, connection, http, parse


class RuntimeRunner:
    """Executes HTTP requests for validation."""
    
    def __init__(
        self,
        timeout: int = 30,
        verify_ssl: bool = True,
        follow_redirects: bool = True,
    ):
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.follow_redirects = follow_redirects
        self.session = requests.Session()
    
    def execute(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Any] = None,
        timeout: Optional[int] = None,
    ) -> RuntimeResult:
        """
        Execute an HTTP request and capture results.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            headers: Request headers
            params: Query parameters
            body: Request body (will be JSON serialized if dict)
            timeout: Request timeout override
        
        Returns:
            RuntimeResult with response data and timings
        """
        headers = headers or {}
        timeout = timeout or self.timeout
        
        try:
            start_time = time.time()
            
            # Prepare request kwargs
            kwargs = {
                "headers": headers,
                "timeout": timeout,
                "verify": self.verify_ssl,
                "allow_redirects": self.follow_redirects,
            }
            
            if params:
                kwargs["params"] = params
            
            if body is not None:
                if isinstance(body, (dict, list)):
                    kwargs["json"] = body
                    if "Content-Type" not in headers:
                        headers["Content-Type"] = "application/json"
                else:
                    kwargs["data"] = body
            
            # Execute request
            response = self.session.request(method.upper(), url, **kwargs)
            
            response_time = (time.time() - start_time) * 1000
            
            # Parse response body
            body_parsed = None
            body_raw = None
            try:
                body_raw = response.text
                if response.headers.get("content-type", "").startswith("application/json"):
                    body_parsed = response.json()
                else:
                    body_parsed = body_raw
            except Exception:
                body_parsed = body_raw
            
            # Capture headers
            response_headers = dict(response.headers)
            
            return RuntimeResult(
                success=True,
                status_code=response.status_code,
                headers=response_headers,
                body=body_parsed,
                body_raw=body_raw,
                response_time_ms=round(response_time, 2),
            )
            
        except requests.exceptions.Timeout:
            return RuntimeResult(
                success=False,
                error="Request timed out",
                error_type="timeout",
                response_time_ms=(time.time() - start_time) * 1000,
            )
        
        except requests.exceptions.ConnectionError as e:
            return RuntimeResult(
                success=False,
                error=f"Connection error: {str(e)[:200]}",
                error_type="connection",
            )
        
        except requests.exceptions.RequestException as e:
            return RuntimeResult(
                success=False,
                error=f"Request error: {str(e)[:200]}",
                error_type="http",
            )
        
        except Exception as e:
            return RuntimeResult(
                success=False,
                error=f"Unexpected error: {str(e)[:200]}",
                error_type="unknown",
            )
    
    def close(self):
        """Close the session."""
        self.session.close()


def redact_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Redact sensitive header values."""
    SENSITIVE_HEADERS = {
        "authorization",
        "x-api-key",
        "api-key",
        "x-auth-token",
        "cookie",
        "x-access-token",
    }
    
    redacted = {}
    for key, value in headers.items():
        if key.lower() in SENSITIVE_HEADERS:
            redacted[key] = "[REDACTED]"
        else:
            redacted[key] = value
    
    return redacted
