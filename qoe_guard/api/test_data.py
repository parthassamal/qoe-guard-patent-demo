"""
Test Data API Endpoints.

Provides sample data and URLs for testing the QoE-Guard system.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List


router = APIRouter(prefix="/test-data", tags=["Test Data"])


# =============================================================================
# SAMPLE SWAGGER/OPENAPI URLS
# =============================================================================

SAMPLE_SWAGGER_URLS = [
    {
        "name": "Swagger Petstore (Official)",
        "url": "https://petstore3.swagger.io/api/v3/openapi.json",
        "description": "Classic demo API with CRUD operations for pets, store, and users",
        "format": "json",
        "version": "OpenAPI 3.0"
    },
    {
        "name": "APIs.guru Directory",
        "url": "https://api.apis.guru/v2/openapi.yaml",
        "description": "Directory of public APIs with metadata",
        "format": "yaml",
        "version": "OpenAPI 3.0"
    },
    {
        "name": "GitHub REST API",
        "url": "https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json",
        "description": "Complete GitHub REST API specification",
        "format": "json",
        "version": "OpenAPI 3.0"
    },
    {
        "name": "Stripe API",
        "url": "https://raw.githubusercontent.com/stripe/openapi/master/openapi/spec3.json",
        "description": "Stripe payment API specification",
        "format": "json",
        "version": "OpenAPI 3.0"
    },
    {
        "name": "Box API",
        "url": "https://raw.githubusercontent.com/box/box-openapi/main/openapi.json",
        "description": "Box cloud storage API specification",
        "format": "json",
        "version": "OpenAPI 3.0"
    }
]


# =============================================================================
# SAMPLE JSON DATA
# =============================================================================

SAMPLE_BASELINE = {
    "playback": {
        "manifestUrl": "https://cdn.example.com/content/123/manifest.m3u8",
        "quality": "HD",
        "maxBitrateKbps": 8000,
        "formats": ["hls", "dash"]
    },
    "drm": {
        "licenseUrl": "https://drm.example.com/license",
        "type": "widevine",
        "keyId": "abc123"
    },
    "entitlement": {
        "allowed": True,
        "tier": "premium",
        "features": ["download", "4k", "hdr"]
    },
    "metadata": {
        "title": "Sample Movie",
        "duration": 7200,
        "genre": "action"
    }
}

SAMPLE_CANDIDATE_MINOR = {
    "playback": {
        "manifestUrl": "https://cdn.example.com/content/123/manifest.m3u8",
        "quality": "HD",
        "maxBitrateKbps": 8500,
        "formats": ["hls", "dash", "smooth"]
    },
    "drm": {
        "licenseUrl": "https://drm.example.com/license",
        "type": "widevine",
        "keyId": "abc123"
    },
    "entitlement": {
        "allowed": True,
        "tier": "premium",
        "features": ["download", "4k", "hdr"]
    },
    "metadata": {
        "title": "Sample Movie",
        "duration": 7200,
        "genre": "action",
        "rating": "PG-13"
    }
}

SAMPLE_CANDIDATE_BREAKING = {
    "playback": {
        "url": "https://cdn-new.example.com/v2/content/123/stream.mpd",
        "resolution": "1080p",
        "maxBitrate": "6000",
        "formats": ["dash"]
    },
    "drm": {
        "license": "https://drm-v2.example.com/acquire",
        "provider": "widevine"
    },
    "access": {
        "granted": True,
        "subscriptionLevel": "gold",
        "capabilities": ["offline", "uhd"]
    },
    "ads": {
        "enabled": True,
        "prerollUrl": "https://ads.example.com/preroll"
    }
}

SAMPLE_RUNTIME_METRICS = [
    {"latency_ms": 145, "status_code": 200, "timestamp": "2025-01-15T10:00:00Z", "endpoint": "/api/playback"},
    {"latency_ms": 132, "status_code": 200, "timestamp": "2025-01-15T10:00:05Z", "endpoint": "/api/playback"},
    {"latency_ms": 5200, "status_code": 500, "timestamp": "2025-01-15T10:00:10Z", "endpoint": "/api/playback"},
    {"latency_ms": 4800, "status_code": 503, "timestamp": "2025-01-15T10:00:15Z", "endpoint": "/api/playback"},
    {"latency_ms": 156, "status_code": 200, "timestamp": "2025-01-15T10:00:20Z", "endpoint": "/api/playback"},
    {"latency_ms": 178, "status_code": 200, "timestamp": "2025-01-15T10:00:25Z", "endpoint": "/api/entitlement"},
    {"latency_ms": 3500, "status_code": 504, "timestamp": "2025-01-15T10:00:30Z", "endpoint": "/api/drm"},
    {"latency_ms": 142, "status_code": 200, "timestamp": "2025-01-15T10:00:35Z", "endpoint": "/api/playback"}
]

SAMPLE_CHANGES = [
    {"change_type": "removed", "path": "$.playback.manifestUrl"},
    {"change_type": "added", "path": "$.playback.url"},
    {"change_type": "type_changed", "path": "$.playback.maxBitrateKbps", "old_type": "integer", "new_type": "string"},
    {"change_type": "removed", "path": "$.entitlement"},
    {"change_type": "added", "path": "$.access"},
    {"change_type": "added", "path": "$.ads"}
]


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("/swagger-urls", response_model=List[Dict[str, str]])
async def get_sample_swagger_urls():
    """
    Get a list of sample Swagger/OpenAPI URLs for testing.
    
    Returns a curated list of public OpenAPI specifications that can be
    used to test the import functionality.
    """
    return SAMPLE_SWAGGER_URLS


@router.get("/baseline")
async def get_sample_baseline() -> Dict[str, Any]:
    """
    Get sample baseline JSON for diff testing.
    
    This represents a typical streaming API response with playback,
    DRM, entitlement, and metadata sections.
    """
    return {
        "description": "Sample baseline JSON (streaming API response)",
        "data": SAMPLE_BASELINE
    }


@router.get("/candidate/minor")
async def get_sample_candidate_minor() -> Dict[str, Any]:
    """
    Get sample candidate JSON with minor (non-breaking) changes.
    
    Changes include:
    - Value changes (maxBitrateKbps: 8000 → 8500)
    - Added fields (formats array extended, rating added)
    """
    return {
        "description": "Sample candidate with minor changes (expected: PASS)",
        "expected_decision": "PASS",
        "data": SAMPLE_CANDIDATE_MINOR
    }


@router.get("/candidate/breaking")
async def get_sample_candidate_breaking() -> Dict[str, Any]:
    """
    Get sample candidate JSON with breaking changes.
    
    Changes include:
    - Field renames (manifestUrl → url, entitlement → access)
    - Type changes (maxBitrateKbps: int → string)
    - Removed fields (keyId, type)
    - New sections (ads)
    """
    return {
        "description": "Sample candidate with breaking changes (expected: FAIL)",
        "expected_decision": "FAIL",
        "data": SAMPLE_CANDIDATE_BREAKING
    }


@router.get("/runtime-metrics")
async def get_sample_runtime_metrics() -> Dict[str, Any]:
    """
    Get sample runtime metrics with anomalies for testing.
    
    Includes normal responses and anomalous spikes in latency
    and error status codes.
    """
    return {
        "description": "Sample runtime metrics with anomalies",
        "anomaly_indices": [2, 3, 6],
        "data": SAMPLE_RUNTIME_METRICS
    }


@router.get("/changes")
async def get_sample_changes() -> Dict[str, Any]:
    """
    Get sample detected changes for ML scoring.
    
    Represents the output of a diff operation for use in
    testing the ML scoring endpoint.
    """
    return {
        "description": "Sample detected changes for ML scoring",
        "expected_score_range": "0.7-0.9 (high risk)",
        "data": SAMPLE_CHANGES
    }


@router.get("/all")
async def get_all_sample_data() -> Dict[str, Any]:
    """
    Get all sample data in one response.
    
    Useful for bulk testing or setting up test scenarios.
    """
    return {
        "swagger_urls": SAMPLE_SWAGGER_URLS,
        "baseline": SAMPLE_BASELINE,
        "candidate_minor": SAMPLE_CANDIDATE_MINOR,
        "candidate_breaking": SAMPLE_CANDIDATE_BREAKING,
        "runtime_metrics": SAMPLE_RUNTIME_METRICS,
        "changes": SAMPLE_CHANGES
    }
