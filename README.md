# QoE-Guard

**QoE-aware JSON Variance Analytics System for Streaming API Validation**

A production-ready system that validates streaming API responses by measuring hierarchical JSON variance versus stored baseline scenarios, predicting QoE (Quality of Experience) risk, and gating releases with explainable **PASS/WARN/FAIL** decisions.

---

## 🎯 What is QoE-Guard?

QoE-Guard solves a critical problem in streaming systems: **API response drift can break client experiences** even when responses are technically "schema-valid."

Traditional validation (OpenAPI schemas, unit tests, snapshot diffs) fails to catch:
- Type changes that compile but break clients (`maxBitrateKbps: 8000` → `"8000"`)
- Critical field value changes (`manifestUrl` pointing to wrong CDN)
- Removed nested objects (`ads.adDecision` disappearing)
- Numeric drift in QoE-sensitive fields (`startPositionSec` changing unexpectedly)

**QoE-Guard detects these issues automatically** and produces actionable, auditable reports.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **Scenario Repository** | Store baseline request/response JSON for any endpoint |
| **Hierarchical JSON Diff** | Path-level change detection (added/removed/type_changed/value_changed) |
| **Variance Feature Vector** | Engineered signals: structural drift, type flips, numeric deltas, array cardinality |
| **QoE Risk Scoring** | Weighted model with critical path detection + policy thresholds |
| **PASS/WARN/FAIL Gating** | Explicit deployment decisions with override rules |
| **Explainable Reports** | Top signals, path-level diffs, audit metadata, copy buttons |
| **Real Data Mode** | Validate any endpoint with custom URLs, headers, params |
| **Paste JSON Mode** | No network access needed — paste baseline + candidate JSON directly |
| **Modern UI** | Dark theme, responsive layout, collapsible sections, JSON validation |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip

### Installation

```bash
# Clone the repository
cd qoe_guard_patent_demo

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Start the servers

**Terminal 1 — Demo Target API** (simulates a streaming endpoint):
```bash
source .venv/bin/activate
python demo_target_service.py
# Runs on http://127.0.0.1:8001
```

**Terminal 2 — QoE-Guard Validator**:
```bash
source .venv/bin/activate
uvicorn qoe_guard.server:app --reload --port 8010
# Runs on http://127.0.0.1:8010
```

### Open the UI
Navigate to **http://127.0.0.1:8010** in your browser.

---

## 📖 Usage Guide

### Demo Mode (5-minute walkthrough)

1. **Seed baseline**: Click "Seed baseline" → stores v1 response as known-good
2. **Run v1**: Click "Run v1 (PASS)" → expect **PASS** (risk ~0.23)
3. **Run v2**: Click "Run v2 (WARN/FAIL)" → expect **FAIL** (risk ~0.68)
4. **View report**: Click "Open report" to see:
   - Risk score and decision
   - Policy thresholds
   - Top contributing signals
   - Path-level JSON changes
   - Full baseline vs candidate comparison

### Real Data Mode (your own APIs)

#### Option A: Fetch from live endpoints

1. **Seed a baseline**:
   - Enter **Base URL** (e.g., `https://api.example.com`)
   - Enter **Endpoint path** (e.g., `/v1/playback`)
   - Optionally add **Headers** for authentication
   - Click **"Save baseline scenario"**

2. **Run validation**:
   - Select your scenario from the dropdown
   - Optionally override candidate URL/params
   - Click **"Run validation"**

#### Option B: Paste JSON directly (no network access needed)

Perfect for validating responses from:
- Production systems behind firewalls
- Third-party APIs
- Logs or recorded responses
- Manual testing

1. **Seed baseline from pasted JSON**:
   - Enter scenario name and endpoint (for reference)
   - Click **"Advanced"**
   - Paste your baseline JSON in **"Baseline JSON (optional override)"**
   - Click **"Save baseline scenario"**

2. **Run validation with pasted candidate**:
   - Select your scenario
   - Click **"Advanced (headers, params, paste JSON)"**
   - Paste candidate JSON in **"Candidate JSON (optional override)"**
   - Click **"Run validation"**

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         QoE-Guard System                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Scenario   │    │  Candidate   │    │   Baseline   │      │
│  │  Repository  │◄───│   Fetcher    │    │    Store     │      │
│  └──────┬───────┘    └──────┬───────┘    └──────────────┘      │
│         │                   │                                   │
│         ▼                   ▼                                   │
│  ┌──────────────────────────────────────┐                      │
│  │       Hierarchical Diff Engine       │                      │
│  │  (path-level change records)         │                      │
│  └──────────────────┬───────────────────┘                      │
│                     │                                           │
│                     ▼                                           │
│  ┌──────────────────────────────────────┐                      │
│  │     Variance Feature Extractor       │                      │
│  │  (structural drift, numeric deltas,  │                      │
│  │   type changes, critical paths)      │                      │
│  └──────────────────┬───────────────────┘                      │
│                     │                                           │
│                     ▼                                           │
│  ┌──────────────────────────────────────┐                      │
│  │       QoE Risk Scoring Model         │                      │
│  │  (weighted signals → risk score)     │                      │
│  └──────────────────┬───────────────────┘                      │
│                     │                                           │
│                     ▼                                           │
│  ┌──────────────────────────────────────┐                      │
│  │          Policy Engine               │                      │
│  │  (thresholds → PASS/WARN/FAIL)       │                      │
│  └──────────────────┬───────────────────┘                      │
│                     │                                           │
│                     ▼                                           │
│  ┌──────────────────────────────────────┐                      │
│  │    Explainable Report Generator      │                      │
│  │  (top signals, path diffs, audit)    │                      │
│  └──────────────────────────────────────┘                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
qoe_guard_patent_demo/
├── qoe_guard/
│   ├── __init__.py
│   ├── server.py          # FastAPI server, routes, orchestration
│   ├── diff.py            # Hierarchical JSON diff engine
│   ├── features.py        # Variance feature extraction
│   ├── model.py           # QoE risk scoring + policy engine
│   ├── storage.py         # Scenario/run persistence (JSON files)
│   └── templates/
│       ├── index.html     # Main UI (forms, scenario repo, runs)
│       └── report.html    # Validation report UI
├── demo_target_service.py # Simulated streaming endpoint (v1/v2)
├── data/                  # Stored scenarios and runs (auto-created)
├── tests/
│   └── test_diff.py       # Unit tests for diff engine
├── requirements.txt       # Python dependencies
├── config.example.env     # Environment configuration template
├── README.md              # This file
├── README_PATENT_DEMO.md  # Original patent demo instructions
├── PATENT_REVISIT_PACKET.md    # Full technical appendix for counsel
├── EMAIL_TO_COUNSEL.md         # Ready-to-send email template
├── ONE_PAGE_101_DEFENSE.md     # Abstractness rebuttal
└── ATTORNEY_SCREENSHARE_SCRIPT.md  # 5-min demo script
```

---

## 🔧 Configuration

### Environment Variables

Copy `config.example.env` to `.env` and customize:

```bash
# Default target for demo mode
QOE_GUARD_TARGET_BASE_URL=http://127.0.0.1:8001
QOE_GUARD_ENDPOINT=/play

# HTTP timeout for fetching responses
QOE_GUARD_HTTP_TIMEOUT_SEC=15
```

### Policy Thresholds

Edit `qoe_guard/model.py` to customize:

```python
# Risk score thresholds
if risk >= 0.72:
    action = "FAIL"
elif risk >= 0.45:
    action = "WARN"
else:
    action = "PASS"

# Critical override rule
if features.critical_changes >= 3 and features.type_changes >= 1:
    action = "FAIL"
```

### Critical Paths

Edit `qoe_guard/features.py` to define which JSON paths are QoE-critical:

```python
CRITICAL_PATH_PREFIXES = [
    "$.playback",
    "$.entitlement",
    "$.drm",
    "$.ads",
]
```

---

## 📊 Variance Features

QoE-Guard extracts these signals from JSON diffs:

| Feature | Description |
|---------|-------------|
| `added_fields` | Count of new fields in candidate |
| `removed_fields` | Count of fields missing from candidate |
| `type_changes` | Count of fields with changed types (e.g., number → string) |
| `value_changes` | Count of fields with changed values |
| `numeric_delta_sum` | Sum of absolute numeric changes |
| `numeric_delta_max` | Maximum single numeric change |
| `array_len_changes` | Count of arrays with length changes |
| `critical_changes` | Count of changes under critical path prefixes |

---

## 🔌 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Main UI |
| `GET` | `/seed` | Seed demo baseline (v1) |
| `GET` | `/run?v=N` | Run demo validation against version N |
| `POST` | `/seed_custom` | Seed custom baseline (form data) |
| `POST` | `/run_custom` | Run custom validation (form data) |
| `GET` | `/runs/{run_id}/report` | View run report |
| `GET` | `/api/runs/{run_id}` | Get run data as JSON |

---

## 🧪 Testing

```bash
# Run unit tests
python3 -m unittest discover -s tests

# Compile check
python3 -m compileall qoe_guard/
```

---

## 📋 Demo Target Service

The `demo_target_service.py` simulates a streaming API with two versions:

### v1 (Baseline)
```json
{
  "playback": {
    "manifestUrl": "https://cdn.example.com/manifest.m3u8",
    "maxBitrateKbps": 8000,
    "startPositionSec": 0
  },
  "entitlement": { "allowed": true, "plan": "premium" },
  "ads": { "enabled": true, "adDecision": { "adTag": "..." } }
}
```

### v2 (Intentional drift)
- `maxBitrateKbps`: number → string (type change!)
- `manifestUrl`: URL changed (critical value change)
- `startPositionSec`: 0 → 12 (numeric delta)
- `playback.lowLatencyMode`: added
- `ads.adDecision`: removed
- `entitlement.regionPolicy`: added
- `metadata.audioTracks`: added

---

## 🛡️ Security Notes

- **Headers are not stored**: Auth tokens are used only for the request and never persisted to disk
- **Avoid long-lived tokens**: Use short-lived or scoped tokens when validating protected endpoints
- **Local storage**: Scenarios and runs are stored in `data/*.json` files (gitignored by default)

---

## 📜 Patent Documentation

This repository includes supporting documentation for patent filing:

| File | Purpose |
|------|---------|
| `EMAIL_TO_COUNSEL.md` | Ready-to-send email requesting filing reconsideration |
| `PATENT_REVISIT_PACKET.md` | Full technical appendix with claim skeletons |
| `ONE_PAGE_101_DEFENSE.md` | Focused 101/abstractness rebuttal |
| `ATTORNEY_SCREENSHARE_SCRIPT.md` | 5-minute demo script |

### Key inventive aspects:
1. Hierarchical JSON diff with path-level change records
2. Variance feature vector (structural drift + value drift signals)
3. QoE-aware risk scoring with critical path weighting
4. Policy engine with explicit PASS/WARN/FAIL gating
5. Explainable reports with top contributing signals
6. Audit trail with run persistence and evidence

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

[Your license here]

---

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) — Modern Python web framework
- [Jinja2](https://jinja.palletsprojects.com/) — Templating engine
- [Pydantic](https://pydantic-docs.helpmanual.io/) — Data validation

---

## 📞 Support

For questions or issues, please open a GitHub issue or contact the maintainers.

---

**QoE-Guard** — Catch QoE-impacting API drift before it reaches your users.
