"""
cURL Command Synthesizer.

Generates executable cURL commands from OpenAPI operations with:
- Parameterization
- Secret redaction
- Environment variable support
- Multiple output formats
"""
from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode, quote

from ..swagger.inventory import NormalizedOperation


@dataclass
class AuthConfig:
    """Authentication configuration for cURL generation."""
    auth_type: str  # bearer, api_key, basic, oauth2
    token_env_var: str = "API_TOKEN"  # Environment variable name
    header_name: str = "Authorization"  # Header name for api_key
    prefix: str = "Bearer"  # Prefix for bearer tokens


@dataclass
class CurlCommand:
    """Generated cURL command with metadata."""
    operation_id: Optional[str]
    method: str
    url: str
    command: str
    command_with_env: str  # With environment variable placeholders
    headers: Dict[str, str]
    body: Optional[str]
    redacted_headers: Dict[str, str]


# Headers to always redact
SENSITIVE_HEADERS = {
    "authorization",
    "x-api-key",
    "api-key",
    "x-auth-token",
    "cookie",
    "x-access-token",
}


def synthesize_curl(
    operation: NormalizedOperation,
    base_url: Optional[str] = None,
    auth_config: Optional[AuthConfig] = None,
    param_values: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Any] = None,
    include_example_body: bool = True,
    redact_secrets: bool = True,
) -> CurlCommand:
    """
    Generate a cURL command for an operation.
    
    Args:
        operation: The operation to generate cURL for
        base_url: Override base URL
        auth_config: Authentication configuration
        param_values: Values for path/query parameters
        headers: Additional headers
        body: Request body (overrides example)
        include_example_body: Include example body if available
        redact_secrets: Redact sensitive values
    
    Returns:
        CurlCommand with the generated command
    """
    param_values = param_values or {}
    headers = headers or {}
    
    # Determine URL
    server_url = base_url or operation.server_url or "http://localhost"
    url = _build_url(server_url, operation.path, operation.parameters, param_values)
    
    # Build headers
    all_headers = {}
    
    # Content-Type for requests with body
    if operation.method in ["POST", "PUT", "PATCH"] and operation.request_body_schema:
        all_headers["Content-Type"] = "application/json"
    
    # Add authentication header
    if auth_config:
        auth_header = _build_auth_header(auth_config, redact_secrets)
        if auth_header:
            all_headers[auth_header[0]] = auth_header[1]
    
    # Add custom headers
    all_headers.update(headers)
    
    # Determine body
    request_body = None
    if body is not None:
        request_body = body
    elif include_example_body and operation.examples.get("request"):
        request_body = operation.examples["request"]
    elif operation.request_body_schema:
        request_body = _generate_example_from_schema(operation.request_body_schema)
    
    # Build cURL command
    curl_parts = ["curl", "-X", operation.method]
    curl_parts_with_env = ["curl", "-X", operation.method]
    
    # Add URL
    curl_parts.append(shlex.quote(url))
    curl_parts_with_env.append(shlex.quote(url))
    
    # Add headers
    redacted_headers = {}
    for name, value in all_headers.items():
        is_sensitive = name.lower() in SENSITIVE_HEADERS
        
        if is_sensitive and redact_secrets:
            redacted_value = "[REDACTED]"
            redacted_headers[name] = redacted_value
        else:
            redacted_headers[name] = value
        
        curl_parts.extend(["-H", shlex.quote(f"{name}: {value}")])
        
        # For env version, use variable for sensitive values
        if is_sensitive:
            env_var = _get_env_var_name(name, auth_config)
            curl_parts_with_env.extend(["-H", f'"{name}: ${{{env_var}}}"'])
        else:
            curl_parts_with_env.extend(["-H", shlex.quote(f"{name}: {value}")])
    
    # Add body
    body_str = None
    if request_body is not None:
        if isinstance(request_body, (dict, list)):
            body_str = json.dumps(request_body, indent=2)
        else:
            body_str = str(request_body)
        
        curl_parts.extend(["-d", shlex.quote(body_str)])
        curl_parts_with_env.extend(["-d", shlex.quote(body_str)])
    
    return CurlCommand(
        operation_id=operation.operation_id,
        method=operation.method,
        url=url,
        command=" \\\n  ".join(curl_parts),
        command_with_env=" \\\n  ".join(curl_parts_with_env),
        headers=all_headers,
        body=body_str,
        redacted_headers=redacted_headers,
    )


def _build_url(
    base_url: str,
    path: str,
    parameters: List[Dict[str, Any]],
    param_values: Dict[str, Any],
) -> str:
    """Build URL with path and query parameters."""
    # Ensure base URL doesn't end with /
    base_url = base_url.rstrip("/")
    
    # Fill in path parameters
    url_path = path
    for param in parameters:
        if param.get("in") == "path":
            name = param.get("name")
            value = param_values.get(name, _get_placeholder(param))
            url_path = url_path.replace(f"{{{name}}}", str(value))
    
    # Build query string
    query_params = {}
    for param in parameters:
        if param.get("in") == "query":
            name = param.get("name")
            if name in param_values:
                query_params[name] = param_values[name]
            elif param.get("required"):
                query_params[name] = _get_placeholder(param)
    
    url = f"{base_url}{url_path}"
    if query_params:
        url += "?" + urlencode(query_params)
    
    return url


def _get_placeholder(param: Dict[str, Any]) -> str:
    """Get a placeholder value for a parameter."""
    schema = param.get("schema", {})
    param_type = schema.get("type", "string")
    example = param.get("example") or schema.get("example")
    
    if example is not None:
        return str(example)
    
    name = param.get("name", "value")
    
    if param_type == "integer":
        return "1"
    elif param_type == "number":
        return "1.0"
    elif param_type == "boolean":
        return "true"
    else:
        return f"{{{name}}}"


def _build_auth_header(
    config: AuthConfig,
    redact: bool,
) -> Optional[tuple]:
    """Build authentication header."""
    if config.auth_type == "bearer":
        value = f"${{{config.token_env_var}}}" if not redact else "[REDACTED]"
        return ("Authorization", f"{config.prefix} {value}")
    elif config.auth_type == "api_key":
        value = f"${{{config.token_env_var}}}" if not redact else "[REDACTED]"
        return (config.header_name, value)
    elif config.auth_type == "basic":
        value = f"${{{config.token_env_var}}}" if not redact else "[REDACTED]"
        return ("Authorization", f"Basic {value}")
    
    return None


def _get_env_var_name(header_name: str, auth_config: Optional[AuthConfig]) -> str:
    """Get environment variable name for a header."""
    if auth_config and header_name.lower() == auth_config.header_name.lower():
        return auth_config.token_env_var
    
    # Generate from header name
    return header_name.upper().replace("-", "_")


def _generate_example_from_schema(schema: Dict[str, Any]) -> Any:
    """Generate an example value from a JSON schema."""
    if "example" in schema:
        return schema["example"]
    
    schema_type = schema.get("type")
    
    if schema_type == "object":
        result = {}
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        for prop_name, prop_schema in properties.items():
            if prop_name in required or len(result) < 3:
                result[prop_name] = _generate_example_from_schema(prop_schema)
        
        return result
    
    elif schema_type == "array":
        items = schema.get("items", {})
        return [_generate_example_from_schema(items)]
    
    elif schema_type == "string":
        if schema.get("format") == "date-time":
            return "2024-01-15T00:00:00Z"
        elif schema.get("format") == "date":
            return "2024-01-15"
        elif schema.get("format") == "email":
            return "user@example.com"
        elif schema.get("format") == "uri":
            return "https://example.com"
        elif schema.get("enum"):
            return schema["enum"][0]
        else:
            return "string"
    
    elif schema_type == "integer":
        return 1
    
    elif schema_type == "number":
        return 1.0
    
    elif schema_type == "boolean":
        return True
    
    elif schema_type == "null":
        return None
    
    return "value"


def generate_curl_bundle(
    operations: List[NormalizedOperation],
    base_url: Optional[str] = None,
    auth_config: Optional[AuthConfig] = None,
    output_format: str = "script",
) -> str:
    """
    Generate a bundle of cURL commands for multiple operations.
    
    Args:
        operations: List of operations
        base_url: Override base URL
        auth_config: Authentication configuration
        output_format: "script" (bash), "json", or "markdown"
    
    Returns:
        Bundle content as string
    """
    commands = []
    for op in operations:
        cmd = synthesize_curl(op, base_url, auth_config, redact_secrets=False)
        commands.append(cmd)
    
    if output_format == "json":
        return json.dumps([
            {
                "operation_id": cmd.operation_id,
                "method": cmd.method,
                "url": cmd.url,
                "command": cmd.command,
            }
            for cmd in commands
        ], indent=2)
    
    elif output_format == "markdown":
        lines = ["# cURL Commands", ""]
        for cmd in commands:
            lines.append(f"## {cmd.method} {cmd.url}")
            if cmd.operation_id:
                lines.append(f"**Operation ID:** `{cmd.operation_id}`")
            lines.append("")
            lines.append("```bash")
            lines.append(cmd.command_with_env)
            lines.append("```")
            lines.append("")
        return "\n".join(lines)
    
    else:  # script
        lines = [
            "#!/bin/bash",
            "# QoE-Guard cURL Bundle",
            "# Generated automatically",
            "",
            "# Set these environment variables before running:",
            "# export API_TOKEN='your-token-here'",
            "",
            "set -e",
            "",
        ]
        
        for cmd in commands:
            lines.append(f"# {cmd.method} {cmd.operation_id or cmd.url}")
            lines.append(cmd.command_with_env)
            lines.append("")
        
        return "\n".join(lines)
