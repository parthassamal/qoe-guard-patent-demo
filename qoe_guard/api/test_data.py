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
# PETSTORE-SPECIFIC TEST DATA
# =============================================================================

# Baseline Pet response (matches Petstore OpenAPI spec)
PETSTORE_BASELINE_PET = {
    "id": 1,
    "name": "doggie",
    "category": {"id": 1, "name": "Dogs"},
    "photoUrls": ["https://example.com/dog.jpg"],
    "tags": [{"id": 1, "name": "friendly"}],
    "status": "available"
}

# PASS Scenario: Minor changes that don't break clients
PETSTORE_CANDIDATE_PASS = {
    "id": 1,
    "name": "doggie",
    "category": {"id": 1, "name": "Dogs"},
    "photoUrls": ["https://example.com/dog.jpg", "https://example.com/dog2.jpg"],  # Added photo
    "tags": [{"id": 1, "name": "friendly"}, {"id": 2, "name": "trained"}],  # Added tag
    "status": "available"
}

# WARN Scenario: Potential issues that need review
PETSTORE_CANDIDATE_WARN = {
    "id": 1,
    "name": "doggie",
    "category": {"id": 1, "name": "Dogs"},
    "photoUrls": [],  # Empty array (potential issue)
    "tags": [{"id": 1, "name": "friendly"}],
    "status": "pending",  # Status changed
    "lastModified": "2026-01-15T10:00:00Z"  # New field added
}

# FAIL Scenario: Breaking changes that will crash clients
PETSTORE_CANDIDATE_FAIL = {
    "petId": "1",  # Renamed + type changed (int -> string)
    "petName": "doggie",  # Renamed field
    "categoryInfo": {"categoryId": 1, "categoryName": "Dogs"},  # Restructured
    "images": ["dog.jpg"],  # Renamed field
    "petStatus": "AVAILABLE"  # Renamed + value changed
    # Missing: tags (removed field)
}

# Broken API Scenarios for USP demonstration
BROKEN_API_SCENARIOS = {
    "schema_drift": {
        "name": "Schema Drift",
        "description": "API returns different structure than OpenAPI spec",
        "qoe_impact": "HIGH - Client crashes due to unexpected structure",
        "baseline": PETSTORE_BASELINE_PET,
        "candidate": {
            "data": {
                "pet": {
                    "id": 1,
                    "name": "doggie"
                }
            },
            "meta": {"page": 1, "total": 1}
        },
        "expected_changes": [
            "$.id (removed - wrapped in data.pet)",
            "$.name (removed - wrapped in data.pet)",
            "$.data (added - unexpected wrapper)",
            "$.meta (added - unexpected field)"
        ]
    },
    
    "type_mismatch": {
        "name": "Type Mismatch",
        "description": "Field types don't match spec - int became string, string became int",
        "qoe_impact": "HIGH - Parse failures, type errors in client code",
        "baseline": {"id": 1, "name": "doggie", "price": 29.99},
        "candidate": {"id": "1", "name": 123, "price": "29.99"},
        "expected_changes": [
            "$.id type_changed (number -> string)",
            "$.name type_changed (string -> number)",
            "$.price type_changed (number -> string)"
        ]
    },
    
    "missing_required": {
        "name": "Missing Required Fields",
        "description": "Required fields missing from response",
        "qoe_impact": "CRITICAL - Feature completely broken, null pointer exceptions",
        "baseline": {"id": 1, "name": "doggie", "photoUrls": ["url1"], "status": "available"},
        "candidate": {"id": 1},
        "expected_changes": [
            "$.name (removed - required field)",
            "$.photoUrls (removed - required field)",
            "$.status (removed - required field)"
        ]
    },
    
    "null_injection": {
        "name": "Null Injection",
        "description": "Fields unexpectedly null when they should have values",
        "qoe_impact": "MEDIUM - UI displays blank, potential crashes",
        "baseline": {"id": 1, "name": "doggie", "status": "available", "category": {"id": 1, "name": "Dogs"}},
        "candidate": {"id": 1, "name": None, "status": None, "category": None},
        "expected_changes": [
            "$.name type_changed (string -> null)",
            "$.status type_changed (string -> null)",
            "$.category type_changed (object -> null)"
        ]
    },
    
    "array_corruption": {
        "name": "Array Corruption",
        "description": "Array structure broken - arrays became objects or scalars",
        "qoe_impact": "CRITICAL - Loop failures, iteration crashes",
        "baseline": {"photoUrls": ["url1", "url2"], "tags": [{"id": 1, "name": "tag1"}]},
        "candidate": {"photoUrls": "url1", "tags": {"id": 1, "name": "tag1"}},
        "expected_changes": [
            "$.photoUrls type_changed (array -> string)",
            "$.tags type_changed (array -> object)"
        ]
    },
    
    "deep_nesting_change": {
        "name": "Deep Nesting Change",
        "description": "Changes in deeply nested structures",
        "qoe_impact": "HIGH - Nested data access fails",
        "baseline": {
            "pet": {
                "details": {
                    "health": {
                        "vaccinations": [
                            {"name": "rabies", "date": "2024-01-01"}
                        ]
                    }
                }
            }
        },
        "candidate": {
            "pet": {
                "details": {
                    "health": {
                        "vaccinations": "rabies:2024-01-01"  # Array became string
                    }
                }
            }
        },
        "expected_changes": [
            "$.pet.details.health.vaccinations type_changed (array -> string)"
        ]
    }
}

# Petstore Runtime Metrics for anomaly detection
PETSTORE_RUNTIME_METRICS = [
    # Normal operation
    {"endpoint": "/pet/1", "method": "GET", "latency_ms": 45, "status_code": 200, "timestamp": "2026-01-15T10:00:00Z"},
    {"endpoint": "/pet/2", "method": "GET", "latency_ms": 52, "status_code": 200, "timestamp": "2026-01-15T10:00:01Z"},
    {"endpoint": "/pet/findByStatus", "method": "GET", "latency_ms": 89, "status_code": 200, "timestamp": "2026-01-15T10:00:02Z"},
    # Anomalies - Broken API signals
    {"endpoint": "/pet/999", "method": "GET", "latency_ms": 1500, "status_code": 404, "timestamp": "2026-01-15T10:00:03Z"},  # Not found
    {"endpoint": "/pet/1", "method": "GET", "latency_ms": 15000, "status_code": 504, "timestamp": "2026-01-15T10:00:04Z"},  # Gateway timeout
    {"endpoint": "/store/order", "method": "POST", "latency_ms": 89, "status_code": 500, "timestamp": "2026-01-15T10:00:05Z"},  # Server error
    {"endpoint": "/pet/1", "method": "PUT", "latency_ms": 8500, "status_code": 503, "timestamp": "2026-01-15T10:00:06Z"},  # Service unavailable
    # Recovery
    {"endpoint": "/pet/1", "method": "GET", "latency_ms": 48, "status_code": 200, "timestamp": "2026-01-15T10:00:07Z"},
    {"endpoint": "/pet/3", "method": "GET", "latency_ms": 51, "status_code": 200, "timestamp": "2026-01-15T10:00:08Z"},
]

# Petstore Order baseline and candidates
PETSTORE_BASELINE_ORDER = {
    "id": 1,
    "petId": 1,
    "quantity": 1,
    "shipDate": "2026-01-20T10:00:00Z",
    "status": "placed",
    "complete": False
}

PETSTORE_CANDIDATE_ORDER_PASS = {
    "id": 1,
    "petId": 1,
    "quantity": 1,
    "shipDate": "2026-01-20T10:00:00Z",
    "status": "approved",  # Status updated
    "complete": False,
    "trackingNumber": "TRK123456"  # New optional field
}

PETSTORE_CANDIDATE_ORDER_FAIL = {
    "orderId": "1",  # Renamed + type changed
    "pet_id": 1,  # Renamed with underscore
    "qty": "1",  # Renamed + type changed
    "ship_date": "2026-01-20",  # Renamed + format changed
    "order_status": "PLACED"  # Renamed + value format changed
    # Missing: complete field
}

# Petstore User test data
PETSTORE_BASELINE_USER = {
    "id": 1,
    "username": "john_doe",
    "firstName": "John",
    "lastName": "Doe",
    "email": "john@example.com",
    "phone": "123-456-7890",
    "userStatus": 1
}

PETSTORE_CANDIDATE_USER_FAIL = {
    "userId": "1",  # Renamed + type changed
    "user_name": "john_doe",  # Renamed with underscore
    "name": {"first": "John", "last": "Doe"},  # Restructured
    "contact": {"email": "john@example.com", "phone": "123-456-7890"},  # Restructured
    "active": True  # Renamed from userStatus + type changed
}


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


# =============================================================================
# PETSTORE TEST DATA ENDPOINTS
# =============================================================================

@router.get("/petstore/baseline")
async def get_petstore_baseline() -> Dict[str, Any]:
    """
    Get Petstore Pet baseline JSON (matches OpenAPI spec exactly).
    
    This represents a valid Pet response from the Swagger Petstore API.
    """
    return {
        "description": "Petstore Pet baseline (matches OpenAPI spec)",
        "api": "GET /pet/{petId}",
        "expected_decision": "N/A (baseline)",
        "data": PETSTORE_BASELINE_PET
    }


@router.get("/petstore/candidate/pass")
async def get_petstore_candidate_pass() -> Dict[str, Any]:
    """
    Get Petstore candidate with PASS scenario (minor, non-breaking changes).
    
    Changes:
    - Added new photo URL to photoUrls array
    - Added new tag to tags array
    - All original fields preserved
    """
    return {
        "description": "Petstore candidate with minor changes",
        "expected_decision": "PASS",
        "changes_summary": [
            "Added photo URL (array extended)",
            "Added tag (array extended)"
        ],
        "qoe_impact": "LOW - No client code changes needed",
        "data": PETSTORE_CANDIDATE_PASS
    }


@router.get("/petstore/candidate/warn")
async def get_petstore_candidate_warn() -> Dict[str, Any]:
    """
    Get Petstore candidate with WARN scenario (potential issues).
    
    Changes:
    - photoUrls array is now empty (potential UI issue)
    - status changed from 'available' to 'pending'
    - New field 'lastModified' added
    """
    return {
        "description": "Petstore candidate with potential issues",
        "expected_decision": "WARN",
        "changes_summary": [
            "photoUrls array now empty ($.photoUrls.__len__)",
            "status value changed (available → pending)",
            "New field lastModified added"
        ],
        "qoe_impact": "MEDIUM - May affect UI display, needs review",
        "data": PETSTORE_CANDIDATE_WARN
    }


@router.get("/petstore/candidate/fail")
async def get_petstore_candidate_fail() -> Dict[str, Any]:
    """
    Get Petstore candidate with FAIL scenario (breaking changes).
    
    Breaking changes:
    - id → petId (renamed + type int→string)
    - name → petName (renamed)
    - category → categoryInfo (restructured)
    - photoUrls → images (renamed)
    - status → petStatus (renamed + case changed)
    - tags field removed entirely
    """
    return {
        "description": "Petstore candidate with BREAKING changes",
        "expected_decision": "FAIL",
        "changes_summary": [
            "$.id removed (renamed to petId + type changed)",
            "$.name removed (renamed to petName)",
            "$.category removed (restructured to categoryInfo)",
            "$.photoUrls removed (renamed to images)",
            "$.status removed (renamed to petStatus)",
            "$.tags removed (field deleted)",
            "$.petId added (string instead of int)",
            "$.petName added",
            "$.categoryInfo added",
            "$.images added",
            "$.petStatus added"
        ],
        "qoe_impact": "CRITICAL - Client will crash, all field accessors broken",
        "data": PETSTORE_CANDIDATE_FAIL
    }


@router.get("/petstore/broken-api-scenarios")
async def get_broken_api_scenarios() -> Dict[str, Any]:
    """
    Get all broken API scenarios for USP demonstration.
    
    These scenarios demonstrate QoE-Guard's core capability:
    detecting broken APIs even when HTTP 200 is returned.
    
    Scenarios include:
    - Schema Drift: Response structure differs from spec
    - Type Mismatch: Field types changed
    - Missing Required: Required fields absent
    - Null Injection: Fields unexpectedly null
    - Array Corruption: Arrays became objects/scalars
    - Deep Nesting Change: Changes in nested structures
    """
    return {
        "description": "Broken API detection scenarios (QoE-Guard USP)",
        "total_scenarios": len(BROKEN_API_SCENARIOS),
        "scenarios": BROKEN_API_SCENARIOS
    }


@router.get("/petstore/broken-api-scenarios/{scenario_name}")
async def get_broken_api_scenario(scenario_name: str) -> Dict[str, Any]:
    """
    Get a specific broken API scenario by name.
    
    Available scenarios:
    - schema_drift
    - type_mismatch
    - missing_required
    - null_injection
    - array_corruption
    - deep_nesting_change
    """
    if scenario_name not in BROKEN_API_SCENARIOS:
        raise HTTPException(
            status_code=404,
            detail=f"Scenario '{scenario_name}' not found. Available: {list(BROKEN_API_SCENARIOS.keys())}"
        )
    return BROKEN_API_SCENARIOS[scenario_name]


@router.get("/petstore/runtime-metrics")
async def get_petstore_runtime_metrics() -> Dict[str, Any]:
    """
    Get Petstore runtime metrics with anomalies.
    
    Includes normal API calls and anomalous ones:
    - 404 Not Found
    - 504 Gateway Timeout
    - 500 Internal Server Error
    - 503 Service Unavailable
    
    Anomaly indices: 3, 4, 5, 6 (0-indexed)
    """
    return {
        "description": "Petstore runtime metrics with anomalies",
        "total_requests": len(PETSTORE_RUNTIME_METRICS),
        "anomaly_indices": [3, 4, 5, 6],
        "anomaly_types": ["404 Not Found", "504 Timeout", "500 Error", "503 Unavailable"],
        "data": PETSTORE_RUNTIME_METRICS
    }


@router.get("/petstore/order/baseline")
async def get_petstore_order_baseline() -> Dict[str, Any]:
    """Get Petstore Order baseline JSON."""
    return {
        "description": "Petstore Order baseline",
        "api": "GET /store/order/{orderId}",
        "data": PETSTORE_BASELINE_ORDER
    }


@router.get("/petstore/order/candidate/pass")
async def get_petstore_order_candidate_pass() -> Dict[str, Any]:
    """Get Petstore Order candidate with minor changes (PASS)."""
    return {
        "description": "Petstore Order with minor changes",
        "expected_decision": "PASS",
        "changes_summary": ["status updated", "trackingNumber added"],
        "data": PETSTORE_CANDIDATE_ORDER_PASS
    }


@router.get("/petstore/order/candidate/fail")
async def get_petstore_order_candidate_fail() -> Dict[str, Any]:
    """Get Petstore Order candidate with breaking changes (FAIL)."""
    return {
        "description": "Petstore Order with BREAKING changes",
        "expected_decision": "FAIL",
        "changes_summary": [
            "All fields renamed with different naming convention",
            "Type changes (int → string)",
            "complete field removed"
        ],
        "data": PETSTORE_CANDIDATE_ORDER_FAIL
    }


@router.get("/petstore/user/baseline")
async def get_petstore_user_baseline() -> Dict[str, Any]:
    """Get Petstore User baseline JSON."""
    return {
        "description": "Petstore User baseline",
        "api": "GET /user/{username}",
        "data": PETSTORE_BASELINE_USER
    }


@router.get("/petstore/user/candidate/fail")
async def get_petstore_user_candidate_fail() -> Dict[str, Any]:
    """Get Petstore User candidate with breaking changes (FAIL)."""
    return {
        "description": "Petstore User with BREAKING changes",
        "expected_decision": "FAIL",
        "changes_summary": [
            "All fields renamed",
            "firstName/lastName restructured to name.first/name.last",
            "email/phone restructured to contact object",
            "userStatus → active with type change"
        ],
        "data": PETSTORE_CANDIDATE_USER_FAIL
    }


@router.get("/petstore/all")
async def get_all_petstore_data() -> Dict[str, Any]:
    """
    Get all Petstore test data in one response.
    
    Includes all baselines, candidates, broken API scenarios,
    and runtime metrics for comprehensive testing.
    """
    return {
        "pet": {
            "baseline": PETSTORE_BASELINE_PET,
            "candidate_pass": PETSTORE_CANDIDATE_PASS,
            "candidate_warn": PETSTORE_CANDIDATE_WARN,
            "candidate_fail": PETSTORE_CANDIDATE_FAIL
        },
        "order": {
            "baseline": PETSTORE_BASELINE_ORDER,
            "candidate_pass": PETSTORE_CANDIDATE_ORDER_PASS,
            "candidate_fail": PETSTORE_CANDIDATE_ORDER_FAIL
        },
        "user": {
            "baseline": PETSTORE_BASELINE_USER,
            "candidate_fail": PETSTORE_CANDIDATE_USER_FAIL
        },
        "broken_api_scenarios": BROKEN_API_SCENARIOS,
        "runtime_metrics": PETSTORE_RUNTIME_METRICS
    }
