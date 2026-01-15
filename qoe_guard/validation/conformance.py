"""
Schema Conformance Validation.

Validates API responses against OpenAPI schemas.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

import jsonschema


@dataclass
class SchemaMismatch:
    """A schema validation mismatch."""
    path: str
    message: str
    schema_path: str
    value: Any


@dataclass
class ConformanceResult:
    """Result of schema conformance validation."""
    valid: bool
    mismatches: List[SchemaMismatch]
    schema_used: Optional[Dict[str, Any]] = None


class SchemaValidator:
    """Validates responses against JSON schemas."""
    
    def __init__(self, schema: Dict[str, Any]):
        """
        Initialize with a JSON schema.
        
        Args:
            schema: JSON schema to validate against
        """
        self.schema = schema
        self._validator = jsonschema.Draft7Validator(schema)
    
    def validate(self, data: Any) -> ConformanceResult:
        """
        Validate data against the schema.
        
        Args:
            data: Data to validate
        
        Returns:
            ConformanceResult with validation status and mismatches
        """
        mismatches = []
        
        for error in self._validator.iter_errors(data):
            path = _format_path(error.absolute_path)
            schema_path = _format_path(error.absolute_schema_path)
            
            mismatches.append(SchemaMismatch(
                path=path,
                message=error.message,
                schema_path=schema_path,
                value=error.instance,
            ))
        
        return ConformanceResult(
            valid=len(mismatches) == 0,
            mismatches=mismatches,
            schema_used=self.schema,
        )


def validate_response(
    response_body: Any,
    schema: Dict[str, Any],
    status_code: Optional[int] = None,
    response_schemas: Optional[Dict[str, Dict[str, Any]]] = None,
) -> ConformanceResult:
    """
    Validate an API response against its schema.
    
    Args:
        response_body: Response body to validate
        schema: JSON schema (used if response_schemas not provided)
        status_code: HTTP status code (for selecting schema from response_schemas)
        response_schemas: Dict of status_code -> schema
    
    Returns:
        ConformanceResult
    """
    # Select schema based on status code if available
    selected_schema = schema
    if response_schemas and status_code:
        str_code = str(status_code)
        if str_code in response_schemas:
            selected_schema = response_schemas[str_code]
        elif "default" in response_schemas:
            selected_schema = response_schemas["default"]
        else:
            # Try to find a matching 2xx schema
            for code, s in response_schemas.items():
                if code.startswith("2") and 200 <= status_code < 300:
                    selected_schema = s
                    break
    
    if not selected_schema:
        return ConformanceResult(
            valid=True,
            mismatches=[],
            schema_used=None,
        )
    
    validator = SchemaValidator(selected_schema)
    return validator.validate(response_body)


def _format_path(path) -> str:
    """Format a JSON path from jsonschema path."""
    if not path:
        return "$"
    
    parts = ["$"]
    for part in path:
        if isinstance(part, int):
            parts.append(f"[{part}]")
        else:
            parts.append(f".{part}")
    
    return "".join(parts)


def compare_schemas(
    expected: Dict[str, Any],
    actual: Dict[str, Any],
) -> List[SchemaMismatch]:
    """
    Compare two schemas and find differences.
    
    Returns list of differences.
    """
    differences = []
    
    # Compare types
    if expected.get("type") != actual.get("type"):
        differences.append(SchemaMismatch(
            path="$",
            message=f"Type mismatch: expected {expected.get('type')}, got {actual.get('type')}",
            schema_path="type",
            value=actual.get("type"),
        ))
    
    # Compare required fields
    expected_required = set(expected.get("required", []))
    actual_required = set(actual.get("required", []))
    
    for field in expected_required - actual_required:
        differences.append(SchemaMismatch(
            path=f"$.{field}",
            message=f"Field no longer required: {field}",
            schema_path="required",
            value=field,
        ))
    
    for field in actual_required - expected_required:
        differences.append(SchemaMismatch(
            path=f"$.{field}",
            message=f"Field now required: {field}",
            schema_path="required",
            value=field,
        ))
    
    # Compare properties
    expected_props = expected.get("properties", {})
    actual_props = actual.get("properties", {})
    
    for prop in set(expected_props.keys()) - set(actual_props.keys()):
        differences.append(SchemaMismatch(
            path=f"$.{prop}",
            message=f"Property removed: {prop}",
            schema_path=f"properties.{prop}",
            value=None,
        ))
    
    for prop in set(actual_props.keys()) - set(expected_props.keys()):
        differences.append(SchemaMismatch(
            path=f"$.{prop}",
            message=f"Property added: {prop}",
            schema_path=f"properties.{prop}",
            value=actual_props[prop],
        ))
    
    return differences
