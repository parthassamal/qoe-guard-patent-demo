"""
Pytest Configuration and Fixtures.
"""
import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_baseline():
    """Sample baseline JSON for testing."""
    return {
        "playback": {
            "manifestUrl": "https://cdn.example.com/stream.m3u8",
            "quality": "HD",
            "maxBitrateKbps": 8000
        },
        "drm": {
            "licenseUrl": "https://drm.example.com/license",
            "type": "widevine"
        },
        "entitlement": {
            "allowed": True,
            "tier": "premium"
        }
    }


@pytest.fixture
def sample_candidate_minor():
    """Sample candidate with minor changes."""
    return {
        "playback": {
            "manifestUrl": "https://cdn.example.com/stream.m3u8",
            "quality": "HD",
            "maxBitrateKbps": 8500  # Minor value change
        },
        "drm": {
            "licenseUrl": "https://drm.example.com/license",
            "type": "widevine"
        },
        "entitlement": {
            "allowed": True,
            "tier": "premium",
            "expiresAt": "2025-12-31"  # New field
        }
    }


@pytest.fixture
def sample_candidate_breaking():
    """Sample candidate with breaking changes."""
    return {
        "playback": {
            "url": "https://cdn-new.example.com/stream.mpd",  # Renamed field
            "resolution": "1080p",  # Renamed field
            "maxBitrate": "6000"  # Type change: int -> string
        },
        "drm": {
            "license": "https://drm-v2.example.com/acquire"  # Renamed field
            # type removed
        },
        "access": {  # Renamed from entitlement
            "granted": True,
            "subscriptionLevel": "gold"
        }
    }


@pytest.fixture
def sample_openapi_spec():
    """Sample OpenAPI specification."""
    return {
        "openapi": "3.0.3",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/test": {
                "get": {
                    "operationId": "getTest",
                    "responses": {"200": {"description": "OK"}}
                }
            }
        }
    }


@pytest.fixture
def sample_runtime_metrics():
    """Sample runtime metrics with anomalies."""
    return [
        {"latency_ms": 145, "status_code": 200},
        {"latency_ms": 132, "status_code": 200},
        {"latency_ms": 5200, "status_code": 500},  # Anomaly
        {"latency_ms": 156, "status_code": 200},
    ]
