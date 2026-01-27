\
from __future__ import annotations
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Demo Target Streaming API", version="0.1.0")

@app.get("/play")
def play(v: int = 1):
    # v1 = baseline response (stable, QoE-safe)
    if v == 1:
        return JSONResponse({
            "requestId": "req-123",
            "playback": {
                "manifestUrl": "https://cdn.example.com/manifest.m3u8",
                "drm": {"type": "widevine", "licenseUrl": "https://drm.example.com/wv"},
                "maxBitrateKbps": 8000,
                "startPositionSec": 0
            },
            "entitlement": {
                "allowed": True,
                "plan": "premium"
            },
            "ads": {
                "enabled": True,
                "adDecision": {"adTag": "https://ads.example.com/vast"}
            },
            "metadata": {
                "title": "Demo Movie",
                "genre": "Drama",
                "durationSec": 5400
            }
        })

    # v2 introduces schema/value variance that *could* impact QoE (WARN level)
    # Examples:
    # - type change: maxBitrateKbps becomes string
    # - critical field change: manifestUrl changed domain/path
    # - removed: ads.adDecision
    # - added: playback.lowLatencyMode
    # - numeric delta: startPositionSec not zero
    elif v == 2:
        return JSONResponse({
            "requestId": "req-123",
            "playback": {
                "manifestUrl": "https://cdn2.example.com/manifest_ll.m3u8",
                "drm": {"type": "widevine", "licenseUrl": "https://drm.example.com/wv"},
                "maxBitrateKbps": "6000",
                "startPositionSec": 12,
                "lowLatencyMode": True
            },
            "entitlement": {
                "allowed": True,
                "plan": "premium",
                "regionPolicy": {"geo": "US", "allowHD": True}
            },
            "ads": {
                "enabled": True
            },
            "metadata": {
                "title": "Demo Movie",
                "genre": "Drama",
                "durationSec": 5400,
                "audioTracks": ["en", "es"]
            }
        })
    
    # v3 = minor changes (PASS level) - safe additions and small value changes
    elif v == 3:
        return JSONResponse({
            "requestId": "req-123",
            "playback": {
                "manifestUrl": "https://cdn.example.com/manifest.m3u8",
                "drm": {"type": "widevine", "licenseUrl": "https://drm.example.com/wv"},
                "maxBitrateKbps": 8200,  # Small increase
                "startPositionSec": 0
            },
            "entitlement": {
                "allowed": True,
                "plan": "premium"
            },
            "ads": {
                "enabled": True,
                "adDecision": {"adTag": "https://ads.example.com/vast"}
            },
            "metadata": {
                "title": "Demo Movie",
                "genre": "Drama",
                "durationSec": 5400,
                "year": 2024  # New optional field
            }
        })
    
    # v4 = breaking changes (FAIL level) - major structural changes
    else:  # v4 or higher
        return JSONResponse({
            "requestId": "req-456",  # Changed
            "stream": {  # Renamed from "playback"
                "url": "https://cdn-new.example.com/v2/stream.mpd",  # Renamed and changed
                "protection": {"scheme": "widevine", "server": "https://drm-v2.example.com/license"},  # Restructured
                "bitrate": 5000,  # Renamed from maxBitrateKbps
                "offset": 0  # Renamed from startPositionSec
            },
            "access": {  # Renamed from "entitlement"
                "granted": True,  # Renamed from "allowed"
                "tier": "gold"  # Renamed from "plan"
            },
            "advertising": {  # Renamed from "ads"
                "active": True  # Renamed from "enabled"
            },
            "info": {  # Renamed from "metadata"
                "name": "Demo Movie",  # Renamed from "title"
                "category": "Drama",  # Renamed from "genre"
                "length": 5400  # Renamed from "durationSec"
            }
        })

@app.get("/openapi.json")
def openapi_spec():
    """OpenAPI/Swagger specification for discovery demo."""
    return JSONResponse({
        "openapi": "3.0.0",
        "info": {
            "title": "Demo Target Streaming API",
            "version": "0.1.0",
            "description": "Demo API for QoE-Guard validation testing"
        },
        "servers": [
            {"url": "http://localhost:8001", "description": "Local development"}
        ],
        "paths": {
            "/play": {
                "get": {
                    "summary": "Get playback configuration",
                    "operationId": "play",
                    "parameters": [
                        {
                            "name": "v",
                            "in": "query",
                            "schema": {"type": "integer", "default": 1},
                            "description": "Version: 1=baseline, 2=warn, 3=pass, 4=fail"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Playback configuration",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "requestId": {"type": "string"},
                                            "playback": {"type": "object"},
                                            "entitlement": {"type": "object"},
                                            "ads": {"type": "object"},
                                            "metadata": {"type": "object"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("demo_target_service:app", host="0.0.0.0", port=8001, reload=True)
