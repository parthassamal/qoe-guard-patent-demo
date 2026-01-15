"""Swagger/OpenAPI discovery and processing module."""
from .discovery import discover_openapi_spec, DiscoveryResult
from .normalizer import normalize_spec, NormalizedSpec
from .inventory import extract_operations, NormalizedOperation

__all__ = [
    "discover_openapi_spec",
    "DiscoveryResult",
    "normalize_spec",
    "NormalizedSpec",
    "extract_operations",
    "NormalizedOperation",
]
