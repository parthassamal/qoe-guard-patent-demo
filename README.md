# QoE-Guard Enterprise

**Swagger-to-Scenario Validation with Brittleness Scoring and QoE-Aware CI Gating**

[![CI/CD](https://github.com/parthassamal/qoe-guard-patent-demo/actions/workflows/qoe-guard.yml/badge.svg)](https://github.com/parthassamal/qoe-guard-patent-demo/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A comprehensive API validation system that ingests any Swagger/OpenAPI specification, extracts operations, generates executable requests, computes **brittleness scores** and **QoE-impact risk scores**, and applies policy-driven CI gates with auditable baseline governance.

---

## Core Differentiators

Most solutions do one of these in isolation: lint specs, generate tests, do contract testing, check links. **QoE-Guard unifies them** and adds high-leverage, defensible layers:

1. **Brittleness Quantification** — Likelihood of consumer breakage + operational fragility
2. **QoE-Aware Prioritization** — Changes weighted by downstream playback/ads/entitlement impact
3. **AI/ML-Powered Analysis** — LLM explanations, semantic drift detection, anomaly detection, explainable ML scoring

---

## Key Inventive Concepts

| Concept | Description |
|---------|-------------|
| **Swagger Page → Executable Validation Pipeline** | Discover OpenAPI from Swagger UI, normalize operations, generate cURL commands |
| **Multi-Select Endpoint Orchestration** | Select operations, execute with rate limiting, apply per-endpoint policies |
| **Brittleness Scoring** | Static + Runtime + Change sensitivity + Blast radius = 0-100 score |
| **QoE-Aware Criticality Weighting** | Weight changes by playback/entitlement/ads/DRM criticality |
| **Drift Classification** | Spec drift vs Runtime drift vs Undocumented (dangerous) drift |
| **Baseline Governance** | Promote baselines only via approvals with audit trail and rollback |
| **AI/ML Analysis Suite** | LLM explanations (Groq/GPT-4/Claude), semantic drift, anomaly detection, SHAP explanations |

---

## Quick Start

### Option 1: Local Development

```bash
# Clone and setup
git clone https://github.com/parthassamal/qoe-guard-patent-demo.git
cd qoe-guard-patent-demo

# Create virtual environment
python3 -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run enterprise server
python -m qoe_guard.main
# Open http://localhost:8010
```

### Option 2: Docker

```bash
docker-compose up
# Enterprise UI: http://localhost:8010
# Demo API: http://localhost:8001
```

### Option 3: Legacy Demo Mode

```bash
# Run original demo server
uvicorn qoe_guard.server:app --reload --port 8010
```

---

## System Architecture

```mermaid
flowchart TB
    subgraph intake [1. Swagger Intake]
        SwaggerURL[Swagger URL Input]
        Discovery[OpenAPI Discovery]
        Normalizer[Schema Normalizer]
    end

    subgraph catalog [2. Endpoint Catalog]
        OperationInventory[Operation Inventory]
        MultiSelect[Multi-Select API]
        FilterEngine[Filter Engine]
    end

    subgraph generation [3. Scenario Generation]
        ScenarioGen[Scenario Generator]
        CurlEngine[cURL Synthesis Engine]
        ArtifactStore[Artifact Store]
    end

    subgraph validation [4. Validation Engine]
        Orchestrator[Validation Orchestrator]
        StaticAnalyzer[Static Analyzer]
        RuntimeRunner[Runtime Conformance]
    end

    subgraph scoring [5. Scoring Engine]
        BrittlenessCalc[Brittleness Calculator]
        QoERiskCalc[QoE Risk Calculator]
        DriftClassifier[Drift Classifier]
    end

    subgraph governance [6. Governance Layer]
        PolicyEngine[Policy Engine]
        BaselineManager[Baseline Manager]
        AuditTrail[Audit Trail]
    end

    subgraph auth [7. Auth and Users]
        AuthService[JWT Auth Service]
        RoleManager[Role Manager]
        ApprovalWorkflow[Approval Workflow]
    end

    SwaggerURL --> Discovery --> Normalizer --> OperationInventory
    OperationInventory --> MultiSelect --> ScenarioGen
    ScenarioGen --> CurlEngine --> ArtifactStore
    MultiSelect --> Orchestrator
    Orchestrator --> StaticAnalyzer
    Orchestrator --> RuntimeRunner
    StaticAnalyzer --> BrittlenessCalc
    RuntimeRunner --> BrittlenessCalc
    RuntimeRunner --> QoERiskCalc
    BrittlenessCalc --> DriftClassifier
    DriftClassifier --> PolicyEngine
    QoERiskCalc --> PolicyEngine
    PolicyEngine --> BaselineManager
    BaselineManager --> AuditTrail
    AuthService --> ApprovalWorkflow
    ApprovalWorkflow --> BaselineManager
```

---

## Brittleness Scoring (0-100)

Computed from four signal families:

### 1. Contract Complexity (25%)
- Schema depth and branching
- anyOf/oneOf union types
- Required fields count
- Free-form objects (additionalProperties)
- Parameter count and constraint tightness

### 2. Change Sensitivity (30%)
- Removed fields/paths (breaking)
- Type changes (incompatible)
- Enum value changes
- Response code changes
- Requiredness changes (optional→required)

### 3. Runtime Fragility (25%)
- Timeout rate
- 5xx error rate
- Latency variance (stddev)
- Schema mismatch rate
- Nondeterminism (optional fields flapping)

### 4. Blast Radius (20%)
- Tag criticality (playback=1.0, ads=0.85, metadata=0.4)
- Environment weight (prod=1.0, stage=0.5, dev=0.2)
- Dependency count (downstream consumers)

```python
# Example brittleness computation
from qoe_guard.scoring import compute_brittleness_score

result = compute_brittleness_score(
    operation_schema={"type": "object", "properties": {...}},
    parameters=[...],
    runtime_results=[...],
    tag_criticality=0.9,
    environment="prod",
)

print(f"Score: {result.score}")
# Score: 67.5

print(f"Top contributors:")
for c in result.top_contributors:
    print(f"  - {c.path}: {c.reason} (impact: {c.impact})")
```

---

## QoE Risk Scoring (0.0-1.0)

Changes weighted by criticality profiles:

```python
# Default tag criticality
playback: 1.0
entitlement: 0.95
drm: 0.95
ads: 0.85
auth: 0.80
session: 0.75
metadata: 0.40
analytics: 0.30

# Default path criticality
$.playback.manifestUrl: 1.0
$.drm.licenseUrl: 1.0
$.entitlement.allowed: 0.95
$.ads.adDecision: 0.85
$.playback.maxBitrateKbps: 0.70
```

### Decision Thresholds

| Score | Decision | CI Gate |
|-------|----------|---------|
| < 0.45 | **PASS** | Allow deployment |
| 0.45 - 0.72 | **WARN** | Review recommended |
| > 0.72 | **FAIL** | Block deployment |

---

## Drift Classification

```mermaid
flowchart TD
    A[Compare Spec + Runtime] --> B{Spec hash changed?}
    B -->|Yes| C{Runtime mismatches?}
    B -->|No| D{Runtime mismatches?}
    
    C -->|No| E[SPEC_DRIFT<br/>Update baselines]
    C -->|Yes| F{Critical paths?}
    
    D -->|No| G[NONE<br/>All good]
    D -->|Yes| H{Critical paths?}
    
    F -->|No| I[SPEC_DRIFT + RUNTIME_DRIFT]
    F -->|Yes| J[UNDOCUMENTED<br/>⚠️ CRITICAL]
    
    H -->|No| K[RUNTIME_DRIFT<br/>Investigate]
    H -->|Yes| L[UNDOCUMENTED<br/>⚠️ CRITICAL]
```

---

## 🧠 AI/ML-Powered Analysis

QoE-Guard integrates advanced AI/ML capabilities for intelligent analysis:

### LLM-Powered Diff Analysis

Supports **Groq** (fastest), **OpenAI GPT-4**, and **Anthropic Claude**:

```python
from qoe_guard.ai import LLMAnalyzer, LLMProvider

# Auto-detects available provider (Groq > OpenAI > Anthropic)
analyzer = LLMAnalyzer()

# Or specify provider
analyzer = LLMAnalyzer(provider=LLMProvider.GROQ)

result = analyzer.analyze_diff(
    baseline={"playback": {"url": "old.m3u8"}},
    candidate={"playback": {"url": "new.m3u8", "drm": "removed"}},
    changes=[{"path": "$.playback.drm", "change_type": "removed"}],
)

print(result.summary)          # Natural language summary
print(result.breaking_changes) # ["$.playback.drm: removed"]
print(result.risk_assessment)  # "HIGH: DRM removal affects entitlement"
print(result.recommendations)  # ["Verify DRM fallback", "Update clients"]
```

### Semantic Drift Detection

Uses **sentence-transformers** to detect field renames and semantic changes:

```python
from qoe_guard.ai import SemanticDriftDetector

detector = SemanticDriftDetector(similarity_threshold=0.75)

result = detector.detect_drift(
    baseline={"playback_url": "https://cdn.example.com"},
    candidate={"manifest_url": "https://cdn.example.com"},
)

# Detects that playback_url → manifest_url is a rename
print(result.potential_renames)
# [SemanticMatch(source="playback_url", target="manifest_url", similarity=0.89)]
```

### ML Anomaly Detection

Uses **Isolation Forest** / **One-Class SVM** to detect runtime anomalies:

```python
from qoe_guard.ai import AnomalyDetector, RuntimeMetrics
from datetime import datetime

detector = AnomalyDetector(algorithm="isolation_forest")

# Fit on historical data
detector.fit(historical_metrics)

# Detect anomalies in new data
metrics = [
    RuntimeMetrics(latency_ms=150, status_code=200, endpoint="/playback"),
    RuntimeMetrics(latency_ms=5200, status_code=500, endpoint="/playback"),  # Anomaly!
]

report = detector.detect_batch(metrics)
print(report.anomaly_rate)       # 0.5 (50%)
print(report.patterns_detected)  # ["Latency spike: 1 requests > 5s"]
```

### NLP Endpoint Classification

Auto-classifies endpoints by intent and criticality:

```python
from qoe_guard.ai import NLPAnalyzer

analyzer = NLPAnalyzer()

intent = analyzer.extract_intent(
    endpoint_path="/api/v1/playback/manifest/{contentId}",
    method="GET",
    description="Retrieves playback manifest with DRM license info",
)

print(intent.primary_intent)    # "playback"
print(intent.business_domain)   # "content_delivery"

criticality = analyzer.classify_criticality(
    endpoint_path="/api/v1/playback/manifest/{contentId}",
    method="GET",
)

print(criticality.level)        # "critical"
print(criticality.qoe_impact)   # "Direct impact on playback"
```

### Explainable ML Risk Scoring

Uses **XGBoost** with **SHAP explanations**:

```python
from qoe_guard.ai import MLRiskScorer, extract_features_from_changes

scorer = MLRiskScorer(model_type="xgboost")

# Extract features from changes
features = extract_features_from_changes(
    changes=[{"change_type": "removed", "path": "$.drm.license"}],
    criticality_profiles={"$.drm": 0.95},
)

# Get prediction with explanation
prediction = scorer.predict(features)
print(prediction.risk_score)    # 0.78
print(prediction.decision)      # "FAIL"
print(prediction.explanation)   # "High risk (78%). Top contributor: critical_path_changes"

# Get SHAP explanation
shap = scorer.explain(features)
print(shap.top_positive)  # Features pushing toward high risk
print(shap.top_negative)  # Features pushing toward low risk
```

### AI API Endpoints

```bash
# Check AI component status
GET /ai/status

# LLM diff analysis
POST /ai/analyze-diff
{
  "baseline": {...},
  "candidate": {...},
  "llm_provider": "groq"  # or "openai", "anthropic"
}

# Semantic drift detection
POST /ai/semantic-drift
{
  "baseline": {...},
  "candidate": {...},
  "similarity_threshold": 0.75
}

# Anomaly detection
POST /ai/detect-anomalies
{
  "algorithm": "isolation_forest",
  "metrics": [...]
}

# Endpoint classification
POST /ai/classify-endpoint
{
  "endpoint_path": "/api/playback",
  "method": "GET",
  "description": "..."
}

# ML risk scoring
POST /ai/ml-score
{
  "changes": [...],
  "criticality_profiles": {...}
}
```

### Environment Variables for AI

```bash
# LLM Providers (at least one required for LLM features)
GROQ_API_KEY=gsk_...           # Groq (recommended - fastest)
OPENAI_API_KEY=sk-...          # OpenAI GPT-4
ANTHROPIC_API_KEY=sk-ant-...   # Anthropic Claude

# Optional: Override default models
GROQ_MODEL=llama-3.1-70b-versatile
OPENAI_MODEL=gpt-4-turbo-preview
ANTHROPIC_MODEL=claude-3-sonnet-20240229
```

---

## Policy Engine

Configure thresholds and override rules:

```python
# qoe_guard/policy/config.py
PolicyConfig(
    # Thresholds
    brittleness_fail_threshold=75.0,
    brittleness_warn_threshold=50.0,
    qoe_fail_threshold=0.72,
    qoe_warn_threshold=0.45,
    
    # Override rules
    fail_on_critical_type_changes=True,
    fail_on_undocumented_drift=True,
    warn_on_spec_drift=True,
    
    # CI behavior
    ci_hard_gate=True,
    require_approval_on_warn=False,
)
```

---

## Baseline Governance

### Promotion Workflow

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant QG as QoE-Guard
    participant App as Approver
    participant DB as Database

    Dev->>QG: Request promotion
    QG->>QG: Check eligibility
    Note over QG: - Min stable runs<br/>- No QoE degradation<br/>- No pending requests
    QG->>DB: Create PromotionRequest
    QG-->>Dev: Request submitted
    
    App->>QG: Review request
    App->>QG: Approve (with reason)
    QG->>DB: Update scenario baseline
    QG->>DB: Create BaselinePromotion
    QG->>DB: Log to AuditTrail
    QG-->>App: Approved (version N)
```

### Eligibility Requirements

- **Stable runs**: Minimum N successful runs with PASS decision
- **QoE non-degradation**: Risk score not increasing beyond threshold
- **No pending requests**: Only one promotion request per scenario

---

## API Reference

### Authentication

```bash
# Register (first user becomes admin)
POST /auth/register
{
  "email": "admin@example.com",
  "password": "secret",
  "name": "Admin"
}

# Login
POST /auth/login
{
  "email": "admin@example.com",
  "password": "secret"
}
# Returns JWT token
```

### Specifications

```bash
# Discover OpenAPI from Swagger UI
POST /specs/discover
{
  "url": "https://api.example.com/docs",
  "headers": {"Authorization": "Bearer token"}
}

# List specs
GET /specs/

# Get operations
GET /specs/{spec_id}/operations?tag=playback&method=GET
```

### Validations

```bash
# Create validation job
POST /validations/
{
  "spec_id": "uuid",
  "selected_operations": ["op1", "op2"],
  "environment": "prod",
  "concurrency": 5,
  "safe_methods_only": true
}

# Get results
GET /validations/{run_id}
```

### Governance

```bash
# Request promotion
POST /governance/promotions
{
  "scenario_id": "uuid",
  "new_baseline": {...},
  "justification": "Updated API version"
}

# Approve (approvers only)
POST /governance/promotions/{request_id}/approve
{"reason": "Reviewed and approved"}

# Get policy
GET /governance/policy

# Update policy (admin only)
PUT /governance/policy
{
  "brittleness_fail_threshold": 70.0
}
```

---

## Project Structure

```
qoe_guard/
├── main.py                    # FastAPI app entry point
├── server.py                  # Legacy demo server
│
├── auth/                      # JWT authentication
│   ├── service.py            # Token generation/validation
│   └── middleware.py         # Auth middleware
│
├── db/                        # Database layer
│   ├── database.py           # SQLAlchemy setup
│   └── models.py             # All DB models
│
├── swagger/                   # OpenAPI processing
│   ├── discovery.py          # Swagger UI → OpenAPI
│   ├── normalizer.py         # $ref dereferencing
│   └── inventory.py          # Operation extraction
│
├── curl/                      # cURL generation
│   └── synthesizer.py        # Parameterized cURL
│
├── scoring/                   # Scoring engines
│   ├── brittleness.py        # 4-family scoring
│   ├── qoe_risk.py           # QoE impact scoring
│   ├── drift.py              # Drift classification
│   └── criticality.py        # Weight profiles
│
├── validation/                # Validation execution
│   ├── orchestrator.py       # Job orchestration
│   ├── runner.py             # HTTP execution
│   └── conformance.py        # Schema validation
│
├── governance/                # Baseline management
│   ├── baseline.py           # Promotion workflow
│   └── audit.py              # Audit trail
│
├── policy/                    # Policy engine
│   ├── engine.py             # Policy evaluation
│   └── config.py             # Policy configuration
│
├── api/                       # REST API routes
│   ├── auth.py
│   ├── specs.py
│   ├── scenarios.py
│   ├── validations.py
│   └── governance.py
│
└── templates/                 # Web UI
    ├── base.html
    ├── dashboard.html
    ├── inventory.html
    ├── validation.html
    ├── governance.html
    └── settings.html
```

---

## Environment Configuration

```bash
# Database (SQLite for demo, PostgreSQL for production)
QOE_GUARD_DATABASE_URL=sqlite:///./qoe_guard_enterprise.db
# or: postgresql://user:pass@host:5432/qoe_guard

# JWT Secret (change in production!)
QOE_GUARD_JWT_SECRET=your-secret-key-here
QOE_GUARD_TOKEN_EXPIRE_MINUTES=1440

# Notifications
QOE_GUARD_SLACK_WEBHOOK=https://hooks.slack.com/services/...
QOE_GUARD_GMAIL_USER=your-email@gmail.com
QOE_GUARD_GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
QOE_GUARD_EMAIL_RECIPIENTS=team@example.com
```

---

## CLI Usage

```bash
# Validate JSON files
python -m qoe_guard.cli validate \
  -b baseline.json \
  -c candidate.json

# Validate URLs
python -m qoe_guard.cli validate \
  --baseline-url http://api.prod/v1/play \
  --candidate-url http://api.staging/v1/play \
  --header "Authorization: Bearer $TOKEN"

# Exit codes
# 0 = PASS (safe to deploy)
# 1 = WARN (review recommended)
# 2 = FAIL (block deployment)
# 3 = ERROR (validation failed)
```

---

## Testing

```bash
# Activate virtual environment
source .venv/bin/activate

# Run unit tests
python -m pytest tests/ -v

# Test scoring modules
python -c "
from qoe_guard.scoring import compute_brittleness_score, compute_qoe_risk
print('Brittleness:', compute_brittleness_score(tag_criticality=0.8).score)
print('QoE Risk:', compute_qoe_risk([]).risk_score)
"
```

---

## Patent Defensibility

This system addresses six claimable inventive concepts:

1. **Swagger Page → Executable Validation Pipeline** (Concept A)
2. **Multi-Select Endpoint Orchestration + Policy Gating** (Concept B)
3. **Brittleness Scoring (Static + Dynamic + Drift-aware)** (Concept C)
4. **QoE-Aware Criticality Weighting** (Concept D)
5. **Drift Classification (Spec vs Runtime vs Undocumented)** (Concept E)
6. **Baseline Governance with Auditability** (Concept F)

Together, these form a coherent "system claim" with multiple "method claims" and dependent claims around cURL synthesis, multi-select orchestration, QoE weighting, and drift classification.

---

## License

MIT

---

<p align="center">
  <b>QoE-Guard Enterprise</b> — Don't let API drift break your users' experience.
</p>
