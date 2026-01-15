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

    # v2 introduces schema/value variance that *could* impact QoE
    # Examples:
    # - type change: maxBitrateKbps becomes string
    # - critical field change: manifestUrl changed domain/path
    # - removed: ads.adDecision
    # - added: playback.lowLatencyMode
    # - numeric delta: startPositionSec not zero
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("demo_target_service:app", host="127.0.0.1", port=8001, reload=True)
