"""
OpenAPI Operation Inventory.

Extracts operations from normalized OpenAPI specs into a structured format.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class Parameter:
    """API parameter definition."""
    name: str
    location: str  # path, query, header, cookie
    required: bool
    schema: Optional[Dict[str, Any]]
    description: Optional[str] = None
    example: Any = None


@dataclass
class NormalizedOperation:
    """Normalized API operation."""
    operation_id: Optional[str]
    method: str
    path: str
    tags: List[str]
    summary: Optional[str]
    description: Optional[str]
    server_url: Optional[str]
    security: List[Dict[str, Any]]
    parameters: List[Dict[str, Any]]
    request_body_schema: Optional[Dict[str, Any]]
    response_schemas: Dict[str, Dict[str, Any]]  # status_code -> schema
    examples: Dict[str, Any]
    deprecated: bool


def extract_operations(
    spec: Dict[str, Any],
    spec_id: Optional[str] = None,
) -> List[NormalizedOperation]:
    """
    Extract all operations from an OpenAPI spec.
    
    Args:
        spec: Normalized OpenAPI spec
        spec_id: Optional spec ID for reference
    
    Returns:
        List of NormalizedOperation objects
    """
    operations = []
    paths = spec.get("paths", {})
    
    # Get default servers
    servers = spec.get("servers", [])
    default_server = servers[0].get("url") if servers else None
    
    # Swagger 2.0 fallback
    if not default_server and "host" in spec:
        scheme = spec.get("schemes", ["https"])[0]
        host = spec.get("host", "")
        base_path = spec.get("basePath", "")
        default_server = f"{scheme}://{host}{base_path}"
    
    # Global security
    global_security = spec.get("security", [])
    
    for path, path_item in paths.items():
        # Path-level parameters
        path_params = path_item.get("parameters", [])
        
        # Path-level servers override
        path_servers = path_item.get("servers", [])
        path_server = path_servers[0].get("url") if path_servers else default_server
        
        # Process each HTTP method
        for method in ["get", "post", "put", "patch", "delete", "head", "options", "trace"]:
            if method not in path_item:
                continue
            
            operation = path_item[method]
            
            # Operation-level servers override
            op_servers = operation.get("servers", [])
            server_url = op_servers[0].get("url") if op_servers else path_server
            
            # Merge parameters (operation params override path params)
            params = _merge_parameters(path_params, operation.get("parameters", []))
            
            # Extract request body schema
            request_body_schema = None
            request_body = operation.get("requestBody", {})
            if request_body:
                content = request_body.get("content", {})
                # Prefer JSON
                for mime in ["application/json", "application/xml", "multipart/form-data"]:
                    if mime in content:
                        request_body_schema = content[mime].get("schema")
                        break
                if not request_body_schema and content:
                    # Take first available
                    first_mime = list(content.keys())[0]
                    request_body_schema = content[first_mime].get("schema")
            
            # Swagger 2.0 body parameter
            for param in params:
                if param.get("in") == "body":
                    request_body_schema = param.get("schema")
                    break
            
            # Extract response schemas
            response_schemas = {}
            responses = operation.get("responses", {})
            for status_code, response in responses.items():
                schema = None
                content = response.get("content", {})
                if content:
                    for mime in ["application/json", "application/xml"]:
                        if mime in content:
                            schema = content[mime].get("schema")
                            break
                    if not schema and content:
                        first_mime = list(content.keys())[0]
                        schema = content[first_mime].get("schema")
                
                # Swagger 2.0
                if not schema and "schema" in response:
                    schema = response.get("schema")
                
                if schema:
                    response_schemas[str(status_code)] = schema
            
            # Extract examples
            examples = _extract_examples(operation, request_body)
            
            # Security (operation-level overrides global)
            security = operation.get("security", global_security)
            
            # Create operation object
            normalized_op = NormalizedOperation(
                operation_id=operation.get("operationId"),
                method=method.upper(),
                path=path,
                tags=operation.get("tags", []),
                summary=operation.get("summary"),
                description=operation.get("description"),
                server_url=server_url,
                security=security,
                parameters=[_normalize_parameter(p) for p in params if p.get("in") != "body"],
                request_body_schema=request_body_schema,
                response_schemas=response_schemas,
                examples=examples,
                deprecated=operation.get("deprecated", False),
            )
            
            operations.append(normalized_op)
    
    return operations


def _merge_parameters(
    path_params: List[Dict],
    op_params: List[Dict],
) -> List[Dict]:
    """
    Merge path-level and operation-level parameters.
    
    Operation parameters override path parameters with the same name and location.
    """
    result = {(p.get("name"), p.get("in")): p for p in path_params}
    for p in op_params:
        key = (p.get("name"), p.get("in"))
        result[key] = p
    return list(result.values())


def _normalize_parameter(param: Dict) -> Dict:
    """Normalize a parameter to a consistent format."""
    return {
        "name": param.get("name"),
        "in": param.get("in"),
        "required": param.get("required", False),
        "schema": param.get("schema", {"type": param.get("type", "string")}),
        "description": param.get("description"),
        "example": param.get("example"),
    }


def _extract_examples(operation: Dict, request_body: Dict) -> Dict[str, Any]:
    """Extract examples from operation."""
    examples = {}
    
    # Request body examples
    if request_body:
        content = request_body.get("content", {})
        for mime, media_type in content.items():
            if "example" in media_type:
                examples["request"] = media_type["example"]
                break
            if "examples" in media_type:
                first_example = list(media_type["examples"].values())[0]
                examples["request"] = first_example.get("value")
                break
    
    # Response examples
    responses = operation.get("responses", {})
    for status_code, response in responses.items():
        content = response.get("content", {})
        for mime, media_type in content.items():
            if "example" in media_type:
                examples[f"response_{status_code}"] = media_type["example"]
                break
            if "examples" in media_type:
                first_example = list(media_type["examples"].values())[0]
                examples[f"response_{status_code}"] = first_example.get("value")
                break
    
    return examples


def filter_operations(
    operations: List[NormalizedOperation],
    tags: Optional[List[str]] = None,
    methods: Optional[List[str]] = None,
    deprecated: Optional[bool] = None,
    search: Optional[str] = None,
) -> List[NormalizedOperation]:
    """
    Filter operations by various criteria.
    
    Args:
        operations: List of operations to filter
        tags: Filter by tag names
        methods: Filter by HTTP methods
        deprecated: Filter by deprecated status
        search: Search in path, summary, operation_id
    
    Returns:
        Filtered list of operations
    """
    result = operations
    
    if tags:
        result = [op for op in result if any(t in op.tags for t in tags)]
    
    if methods:
        methods_upper = [m.upper() for m in methods]
        result = [op for op in result if op.method in methods_upper]
    
    if deprecated is not None:
        result = [op for op in result if op.deprecated == deprecated]
    
    if search:
        search_lower = search.lower()
        result = [
            op for op in result
            if (search_lower in op.path.lower() or
                (op.summary and search_lower in op.summary.lower()) or
                (op.operation_id and search_lower in op.operation_id.lower()))
        ]
    
    return result


def group_by_tag(operations: List[NormalizedOperation]) -> Dict[str, List[NormalizedOperation]]:
    """Group operations by their tags."""
    groups: Dict[str, List[NormalizedOperation]] = {}
    
    for op in operations:
        if op.tags:
            for tag in op.tags:
                if tag not in groups:
                    groups[tag] = []
                groups[tag].append(op)
        else:
            if "untagged" not in groups:
                groups["untagged"] = []
            groups["untagged"].append(op)
    
    return groups
