"""
Sample Data Fixtures for QoE-Guard Testing.

This module provides comprehensive test data for unit, integration, and smoke tests.
"""

# =============================================================================
# SAMPLE OPENAPI SPECIFICATIONS
# =============================================================================

SAMPLE_OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "Streaming Service API",
        "version": "1.0.0",
        "description": "Video streaming API with playback, DRM, and entitlement endpoints"
    },
    "servers": [
        {"url": "https://api.example.com/v1"}
    ],
    "paths": {
        "/playback/{contentId}": {
            "get": {
                "operationId": "getPlaybackManifest",
                "summary": "Get playback manifest",
                "description": "Retrieves the playback manifest URL for video streaming",
                "tags": ["playback"],
                "parameters": [
                    {
                        "name": "contentId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/PlaybackResponse"
                                }
                            }
                        }
                    }
                }
            }
        },
        "/entitlement/{userId}": {
            "get": {
                "operationId": "getEntitlement",
                "summary": "Get user entitlement",
                "description": "Checks user's content access rights",
                "tags": ["entitlement"],
                "parameters": [
                    {
                        "name": "userId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Entitlement check result",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/EntitlementResponse"
                                }
                            }
                        }
                    }
                }
            }
        },
        "/drm/license": {
            "post": {
                "operationId": "getLicense",
                "summary": "Get DRM license",
                "description": "Retrieves DRM license for content playback",
                "tags": ["drm"],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/LicenseRequest"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "License response",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/LicenseResponse"
                                }
                            }
                        }
                    }
                }
            }
        }
    },
    "components": {
        "schemas": {
            "PlaybackResponse": {
                "type": "object",
                "required": ["manifestUrl", "quality"],
                "properties": {
                    "manifestUrl": {"type": "string"},
                    "quality": {"type": "string", "enum": ["SD", "HD", "4K"]},
                    "maxBitrateKbps": {"type": "integer"},
                    "subtitles": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            },
            "EntitlementResponse": {
                "type": "object",
                "required": ["allowed", "tier"],
                "properties": {
                    "allowed": {"type": "boolean"},
                    "tier": {"type": "string"},
                    "expiresAt": {"type": "string", "format": "date-time"}
                }
            },
            "LicenseRequest": {
                "type": "object",
                "required": ["contentId", "deviceId"],
                "properties": {
                    "contentId": {"type": "string"},
                    "deviceId": {"type": "string"},
                    "drmType": {"type": "string", "enum": ["widevine", "fairplay", "playready"]}
                }
            },
            "LicenseResponse": {
                "type": "object",
                "required": ["license"],
                "properties": {
                    "license": {"type": "string"},
                    "expiresAt": {"type": "string", "format": "date-time"}
                }
            }
        }
    }
}


# =============================================================================
# SAMPLE JSON RESPONSES
# =============================================================================

BASELINE_PLAYBACK_RESPONSE = {
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

CANDIDATE_PLAYBACK_RESPONSE_MINOR = {
    "playback": {
        "manifestUrl": "https://cdn.example.com/content/123/manifest.m3u8",
        "quality": "HD",
        "maxBitrateKbps": 8500,  # Minor change
        "formats": ["hls", "dash", "smooth"]  # Added format
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
        "rating": "PG-13"  # New field
    }
}

CANDIDATE_PLAYBACK_RESPONSE_BREAKING = {
    "playback": {
        "url": "https://cdn-new.example.com/v2/content/123/stream.mpd",  # Field renamed
        "resolution": "1080p",  # Field renamed + different value
        "maxBitrate": "6000",  # Type changed: int -> string
        "formats": ["dash"]  # Removed format
    },
    "drm": {
        "license": "https://drm-v2.example.com/acquire",  # Field renamed
        "provider": "widevine",  # Field renamed
        # keyId removed
    },
    "access": {  # Section renamed from 'entitlement'
        "granted": True,  # Field renamed
        "subscriptionLevel": "gold",  # Field renamed
        "capabilities": ["offline", "uhd"]  # Field renamed + different values
    },
    "ads": {  # New section
        "enabled": True,
        "prerollUrl": "https://ads.example.com/preroll"
    }
}


# =============================================================================
# SAMPLE RUNTIME METRICS
# =============================================================================

RUNTIME_METRICS_NORMAL = [
    {"latency_ms": 145, "status_code": 200, "timestamp": "2025-01-15T10:00:00Z", "endpoint": "/api/playback"},
    {"latency_ms": 132, "status_code": 200, "timestamp": "2025-01-15T10:00:05Z", "endpoint": "/api/playback"},
    {"latency_ms": 156, "status_code": 200, "timestamp": "2025-01-15T10:00:10Z", "endpoint": "/api/playback"},
    {"latency_ms": 128, "status_code": 200, "timestamp": "2025-01-15T10:00:15Z", "endpoint": "/api/playback"},
    {"latency_ms": 149, "status_code": 200, "timestamp": "2025-01-15T10:00:20Z", "endpoint": "/api/playback"},
    {"latency_ms": 142, "status_code": 200, "timestamp": "2025-01-15T10:00:25Z", "endpoint": "/api/entitlement"},
    {"latency_ms": 138, "status_code": 200, "timestamp": "2025-01-15T10:00:30Z", "endpoint": "/api/drm"},
    {"latency_ms": 151, "status_code": 200, "timestamp": "2025-01-15T10:00:35Z", "endpoint": "/api/playback"},
]

RUNTIME_METRICS_WITH_ANOMALIES = [
    {"latency_ms": 145, "status_code": 200, "timestamp": "2025-01-15T10:00:00Z", "endpoint": "/api/playback"},
    {"latency_ms": 132, "status_code": 200, "timestamp": "2025-01-15T10:00:05Z", "endpoint": "/api/playback"},
    {"latency_ms": 5200, "status_code": 500, "timestamp": "2025-01-15T10:00:10Z", "endpoint": "/api/playback"},  # Anomaly
    {"latency_ms": 4800, "status_code": 503, "timestamp": "2025-01-15T10:00:15Z", "endpoint": "/api/playback"},  # Anomaly
    {"latency_ms": 156, "status_code": 200, "timestamp": "2025-01-15T10:00:20Z", "endpoint": "/api/playback"},
    {"latency_ms": 178, "status_code": 200, "timestamp": "2025-01-15T10:00:25Z", "endpoint": "/api/entitlement"},
    {"latency_ms": 3500, "status_code": 504, "timestamp": "2025-01-15T10:00:30Z", "endpoint": "/api/drm"},  # Anomaly
    {"latency_ms": 142, "status_code": 200, "timestamp": "2025-01-15T10:00:35Z", "endpoint": "/api/playback"},
]


# =============================================================================
# SAMPLE CHANGES FOR ML SCORING
# =============================================================================

CHANGES_MINOR = [
    {"change_type": "value_changed", "path": "$.playback.maxBitrateKbps", "old_value": 8000, "new_value": 8500},
    {"change_type": "added", "path": "$.playback.formats[2]", "new_value": "smooth"},
    {"change_type": "added", "path": "$.metadata.rating", "new_value": "PG-13"},
]

CHANGES_BREAKING = [
    {"change_type": "removed", "path": "$.playback.manifestUrl"},
    {"change_type": "added", "path": "$.playback.url"},
    {"change_type": "removed", "path": "$.playback.quality"},
    {"change_type": "added", "path": "$.playback.resolution"},
    {"change_type": "type_changed", "path": "$.playback.maxBitrateKbps", "old_type": "integer", "new_type": "string"},
    {"change_type": "removed", "path": "$.drm.licenseUrl"},
    {"change_type": "added", "path": "$.drm.license"},
    {"change_type": "removed", "path": "$.drm.keyId"},
    {"change_type": "removed", "path": "$.entitlement"},
    {"change_type": "added", "path": "$.access"},
    {"change_type": "added", "path": "$.ads"},
]


# =============================================================================
# SAMPLE SEMANTIC DRIFT DATA
# =============================================================================

SEMANTIC_EQUIVALENTS = [
    ("playback_url", "manifest_url", True),
    ("playback_url", "stream_link", True),
    ("quality", "resolution", True),
    ("HD", "1080p", True),
    ("entitlement", "access_rights", True),
    ("playback", "authentication", False),
    ("drm", "analytics", False),
]


# =============================================================================
# PUBLIC TEST APIS
# =============================================================================

PUBLIC_SWAGGER_URLS = [
    {
        "name": "Swagger Petstore",
        "url": "https://petstore3.swagger.io/api/v3/openapi.json",
        "description": "Classic demo API with pets, store, users",
    },
    {
        "name": "APIs.guru Directory",
        "url": "https://api.apis.guru/v2/openapi.yaml",
        "description": "Directory of public APIs",
    },
    {
        "name": "JSONPlaceholder",
        "url": "https://jsonplaceholder.typicode.com",
        "description": "Fake REST API for testing (no Swagger, but useful for manual tests)",
    },
]


# =============================================================================
# EXPECTED TEST OUTCOMES
# =============================================================================

EXPECTED_DIFF_MINOR = {
    "total_changes": 3,
    "breaking_changes": 0,
    "decision": "PASS",
    "qoe_risk": 0.15,
}

EXPECTED_DIFF_BREAKING = {
    "total_changes": 11,
    "breaking_changes": 6,
    "decision": "FAIL",
    "qoe_risk": 0.85,
}


# =============================================================================
# USER CREDENTIALS FOR TESTS
# =============================================================================

TEST_USER = {
    "email": "test@example.com",
    "password": "testpassword123",
    "role": "developer"
}

TEST_ADMIN = {
    "email": "admin@example.com",
    "password": "adminpassword123",
    "role": "admin"
}

TEST_APPROVER = {
    "email": "approver@example.com",
    "password": "approverpassword123",
    "role": "approver"
}
