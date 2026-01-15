"""
OpenAPI Spec Normalizer.

Normalizes OpenAPI specs by:
- Dereferencing $ref pointers
- Flattening schemas
- Computing spec hash
- Extracting metadata
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set


@dataclass
class NormalizedSpec:
    """Normalized OpenAPI specification."""
    spec: Dict[str, Any]
    spec_hash: str
    openapi_version: str
    title: Optional[str]
    description: Optional[str]
    servers: List[str]
    tags: List[str]
    security_schemes: Dict[str, Any]
    deref_trace: Dict[str, str] = field(default_factory=dict)


class NormalizationError(Exception):
    """Error during spec normalization."""
    pass


def normalize_spec(spec: Dict[str, Any]) -> NormalizedSpec:
    """
    Normalize an OpenAPI specification.
    
    Args:
        spec: Raw OpenAPI spec dictionary
    
    Returns:
        NormalizedSpec with dereferenced schemas and metadata
    """
    # Make a deep copy to avoid modifying the original
    normalized = copy.deepcopy(spec)
    
    # Track $ref resolutions
    deref_trace = {}
    
    # Dereference all $refs
    normalized = _dereference_spec(normalized, normalized, deref_trace)
    
    # Extract metadata
    openapi_version = normalized.get("openapi", normalized.get("swagger", "unknown"))
    info = normalized.get("info", {})
    title = info.get("title")
    description = info.get("description")
    
    # Extract servers
    servers = []
    if "servers" in normalized:
        servers = [s.get("url", "") for s in normalized.get("servers", [])]
    elif "host" in normalized:
        # Swagger 2.0
        scheme = normalized.get("schemes", ["https"])[0]
        host = normalized.get("host", "")
        base_path = normalized.get("basePath", "")
        servers = [f"{scheme}://{host}{base_path}"]
    
    # Extract tags
    tags = [t.get("name", "") for t in normalized.get("tags", [])]
    
    # Extract security schemes
    security_schemes = {}
    if "components" in normalized:
        security_schemes = normalized.get("components", {}).get("securitySchemes", {})
    elif "securityDefinitions" in normalized:
        # Swagger 2.0
        security_schemes = normalized.get("securityDefinitions", {})
    
    # Compute spec hash
    spec_hash = _compute_spec_hash(normalized)
    
    return NormalizedSpec(
        spec=normalized,
        spec_hash=spec_hash,
        openapi_version=openapi_version,
        title=title,
        description=description,
        servers=servers,
        tags=tags,
        security_schemes=security_schemes,
        deref_trace=deref_trace,
    )


def _dereference_spec(
    node: Any,
    root: Dict[str, Any],
    trace: Dict[str, str],
    visited: Optional[Set[str]] = None,
    path: str = "#",
) -> Any:
    """
    Recursively dereference $ref pointers in a spec.
    
    Args:
        node: Current node to process
        root: Root of the spec (for resolving refs)
        trace: Dictionary to track ref resolutions
        visited: Set of visited refs (for circular reference detection)
        path: Current JSON pointer path
    
    Returns:
        Dereferenced node
    """
    if visited is None:
        visited = set()
    
    if isinstance(node, dict):
        if "$ref" in node:
            ref = node["$ref"]
            
            # Check for circular reference
            if ref in visited:
                # Return a placeholder for circular refs
                return {"$circular_ref": ref}
            
            visited.add(ref)
            trace[path] = ref
            
            # Resolve the reference
            resolved = _resolve_ref(ref, root)
            if resolved is not None:
                # Recursively dereference the resolved value
                return _dereference_spec(resolved, root, trace, visited, ref)
            else:
                # Keep the unresolved ref
                return node
        else:
            # Process all keys
            return {
                k: _dereference_spec(v, root, trace, visited.copy(), f"{path}/{k}")
                for k, v in node.items()
            }
    
    elif isinstance(node, list):
        return [
            _dereference_spec(item, root, trace, visited.copy(), f"{path}/{i}")
            for i, item in enumerate(node)
        ]
    
    else:
        return node


def _resolve_ref(ref: str, root: Dict[str, Any]) -> Optional[Any]:
    """
    Resolve a JSON reference.
    
    Args:
        ref: JSON reference string (e.g., "#/components/schemas/Pet")
        root: Root document
    
    Returns:
        Resolved value or None if not found
    """
    if not ref.startswith("#/"):
        # External references not supported
        return None
    
    # Split the path
    parts = ref[2:].split("/")
    
    # Navigate to the referenced value
    current = root
    for part in parts:
        # Decode JSON pointer escapes
        part = part.replace("~1", "/").replace("~0", "~")
        
        if isinstance(current, dict):
            if part in current:
                current = current[part]
            else:
                return None
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    
    return current


def _compute_spec_hash(spec: Dict[str, Any]) -> str:
    """
    Compute a deterministic hash of the spec.
    
    Only includes paths and schemas, not metadata like descriptions.
    """
    # Extract the parts that matter for API compatibility
    significant = {
        "paths": spec.get("paths", {}),
        "components": spec.get("components", {}),
        "definitions": spec.get("definitions", {}),  # Swagger 2.0
    }
    
    # Sort keys for deterministic serialization
    json_str = json.dumps(significant, sort_keys=True, default=str)
    
    return hashlib.sha256(json_str.encode()).hexdigest()


def compare_specs(
    spec1: Dict[str, Any],
    spec2: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compare two specs and return differences.
    
    Returns:
        Dictionary with added, removed, and changed paths
    """
    paths1 = set(spec1.get("paths", {}).keys())
    paths2 = set(spec2.get("paths", {}).keys())
    
    added = paths2 - paths1
    removed = paths1 - paths2
    common = paths1 & paths2
    
    changed = []
    for path in common:
        p1 = spec1["paths"][path]
        p2 = spec2["paths"][path]
        
        # Check methods
        methods1 = set(k for k in p1.keys() if k in ["get", "post", "put", "patch", "delete", "head", "options"])
        methods2 = set(k for k in p2.keys() if k in ["get", "post", "put", "patch", "delete", "head", "options"])
        
        if methods1 != methods2:
            changed.append({
                "path": path,
                "type": "methods_changed",
                "before": list(methods1),
                "after": list(methods2),
            })
        else:
            # Check each method for schema changes
            for method in methods1:
                if _method_changed(p1.get(method, {}), p2.get(method, {})):
                    changed.append({
                        "path": path,
                        "method": method,
                        "type": "schema_changed",
                    })
    
    return {
        "added_paths": list(added),
        "removed_paths": list(removed),
        "changed": changed,
        "is_breaking": len(removed) > 0 or any(c.get("type") == "schema_changed" for c in changed),
    }


def _method_changed(method1: Dict, method2: Dict) -> bool:
    """Check if a method definition has changed significantly."""
    # Compare parameters
    params1 = {p.get("name"): p for p in method1.get("parameters", [])}
    params2 = {p.get("name"): p for p in method2.get("parameters", [])}
    
    if set(params1.keys()) != set(params2.keys()):
        return True
    
    # Compare responses
    resp1 = set(method1.get("responses", {}).keys())
    resp2 = set(method2.get("responses", {}).keys())
    
    if resp1 != resp2:
        return True
    
    return False
