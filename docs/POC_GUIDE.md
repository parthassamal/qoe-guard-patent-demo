# QoE-Aware JSON Variance Analytics System - POC Guide

## Overview

This guide provides a comprehensive walkthrough for demonstrating the QoE-Guard Proof of Concept (POC). The POC showcases a complete API validation system that uses QoE-aware scoring to assess the impact of API changes on end-user experience.

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Web browser (Chrome, Firefox, Safari, or Edge)
- Terminal/Command Prompt

### One-Command Setup

```bash
# From the project root directory
./scripts/poc_demo.sh
```

This script will:
1. Start all Docker services
2. Wait for services to be ready
3. Seed baseline scenarios
4. Optionally run automated validation scenarios
5. Display summary and next steps

### Manual Setup

If you prefer manual setup:

```bash
# 1. Start services
docker compose up -d --build

# 2. Wait for services (about 30 seconds)
# Check services are running:
curl http://localhost:8001/play?v=1  # Demo target
curl http://localhost:8010            # QoE-Guard UI

# 3. Open browser
# Navigate to: http://localhost:8010
```

## Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| QoE-Guard UI | http://localhost:8010 | Main web interface |
| Demo Target API | http://localhost:8001 | Demo streaming API |
| API Documentation | http://localhost:8010/docs | Swagger/OpenAPI docs |
| Demo OpenAPI Spec | http://localhost:8001/openapi.json | Demo API specification |

## Demo Flow

### Step 1: Access the Web UI

1. Open your browser and navigate to **http://localhost:8010**
2. You should see the QoE-Guard dashboard

### Step 2: Seed Baseline

The baseline represents the "known good" API response that we'll compare against.

**Option A: Via Web UI**
1. Click the "Seed Baseline" button on the dashboard
2. Or navigate to: http://localhost:8010/seed

**Option B: Via API**
```bash
curl http://localhost:8010/seed
```

This creates a baseline scenario from `http://localhost:8001/play?v=1`

### Step 3: Run Validation Scenarios

The demo includes four scenarios with different risk levels:

#### Scenario 1: Baseline (v=1) - Stable
- **URL**: http://localhost:8010/run?v=1
- **Expected**: No changes (identical to baseline)
- **Purpose**: Verify baseline is working

#### Scenario 2: PASS (v=3) - Minor Safe Changes
- **URL**: http://localhost:8010/run?v=3
- **Expected Result**: **PASS**
- **Changes**:
  - Small numeric increase: `maxBitrateKbps: 8000 → 8200`
  - New optional field: `metadata.year: 2024`
- **Risk Level**: Low
- **Impact**: Safe, backward-compatible changes

#### Scenario 3: WARN (v=2) - Moderate Changes
- **URL**: http://localhost:8010/run?v=2
- **Expected Result**: **WARN**
- **Changes**:
  - Type change: `maxBitrateKbps: 8000 (number) → "6000" (string)`
  - Critical field change: `manifestUrl` domain changed
  - Removed field: `ads.adDecision`
  - Added field: `playback.lowLatencyMode`
  - Numeric delta: `startPositionSec: 0 → 12`
- **Risk Level**: Medium
- **Impact**: Potentially breaking for some consumers

#### Scenario 4: FAIL (v=4) - Breaking Changes
- **URL**: http://localhost:8010/run?v=4
- **Expected Result**: **FAIL**
- **Changes**:
  - Major structural changes: All top-level objects renamed
  - `playback` → `stream`
  - `entitlement` → `access`
  - `ads` → `advertising`
  - `metadata` → `info`
  - Multiple field renames within objects
- **Risk Level**: High
- **Impact**: Breaking changes that will break consumers

### Step 4: Review Results

After running each validation:

1. **View the Report**
   - Reports are automatically generated
   - Navigate to: http://localhost:8010/runs/{run_id}/report
   - Or click the run ID from the dashboard

2. **Key Metrics to Review**:
   - **Risk Score** (0.0-1.0): Overall risk assessment
   - **Brittleness Score** (0-100): Likelihood of consumer breakage
   - **QoE Risk Score** (0.0-1.0): Impact on Quality of Experience
   - **Decision**: PASS / WARN / FAIL
   - **Change Details**: Hierarchical diff showing all changes

3. **Change Analysis**:
   - View path-level changes
   - See before/after values
   - Identify critical paths affected

## Automated Scenario Runner

For automated testing and validation:

```bash
# Run all scenarios and generate report
python scripts/poc_scenarios.py
```

This will:
- Run all three validation scenarios (PASS, WARN, FAIL)
- Calculate scores for each
- Generate a summary report
- Save results to `data/poc_report.json`

## Key Features Demonstration

### 1. Hierarchical JSON Diff

The system performs deep comparison of JSON structures:

- Detects changes at any nesting level
- Tracks path information (e.g., `$.playback.maxBitrateKbps`)
- Classifies change types: added, removed, value_changed, type_changed

**Example Output**:
```
Path: $.playback.maxBitrateKbps
Type: type_changed
Before: 8000 (number)
After: "6000" (string)
```

### 2. QoE-Aware Scoring

The system uses domain-aware criticality weighting:

- **Critical Paths**: Fields that directly impact user experience
  - `playback.manifestUrl` - Video playback URL
  - `drm.licenseUrl` - DRM license server
  - `entitlement.allowed` - Access control

- **Scoring Factors**:
  - Critical changes: Higher weight (0.18)
  - Type changes: Breaking changes (0.14)
  - Removed fields: Consumer breakage (0.10)
  - Added fields: Lower risk (0.05)

### 3. Brittleness Scoring

Measures API fragility based on:
- Contract complexity
- Change sensitivity
- Runtime fragility
- Blast radius (impact scope)

**Score Range**: 0-100
- 0-30: Low brittleness (stable API)
- 31-60: Medium brittleness
- 61-100: High brittleness (fragile API)

### 4. Drift Classification

Categorizes changes as:
- **Spec Drift**: Changes documented in OpenAPI spec
- **Runtime Drift**: Changes in actual responses vs spec
- **Undocumented Drift**: Dangerous - changes not in spec

### 5. Policy Engine

Configurable thresholds determine PASS/WARN/FAIL:

- **FAIL**: Risk ≥ 0.72 OR (≥3 critical + ≥1 type change)
- **WARN**: Risk ≥ 0.45 OR ≥2 critical changes
- **PASS**: Otherwise

## Advanced Features

### Swagger/OpenAPI Discovery

1. Navigate to: http://localhost:8010/swagger
2. Enter OpenAPI URL: http://localhost:8001/openapi.json
3. Click "Analyze Swagger"
4. View discovered endpoints and operations

### Multi-Endpoint Validation

1. Import OpenAPI specification
2. Select multiple endpoints
3. Run parallel validation
4. View aggregated results

### Baseline Governance

1. Create baseline from current API response
2. Promote baseline through approval workflow
3. Track baseline versions
4. Audit trail of all changes

### AI-Powered Analysis (Optional)

If AI features are configured:

1. **LLM Diff Analysis**: Natural language explanations
2. **Semantic Drift Detection**: Detect field renames via embeddings
3. **Anomaly Detection**: ML-based outlier detection
4. **NLP Classification**: Auto-classify endpoints

## Expected Outputs

### PASS Scenario (v=3)

```
Risk Score: 0.15-0.25
Decision: PASS
Changes: 1-2 (minor additions)
Brittleness: 10-20
QoE Risk: 0.10-0.20
```

### WARN Scenario (v=2)

```
Risk Score: 0.45-0.65
Decision: WARN
Changes: 5-7 (type changes, removals)
Brittleness: 40-60
QoE Risk: 0.45-0.60
```

### FAIL Scenario (v=4)

```
Risk Score: 0.75-0.95
Decision: FAIL
Changes: 15+ (major structural changes)
Brittleness: 70-90
QoE Risk: 0.75-0.90
```

## Troubleshooting

### Services Not Starting

**Problem**: Docker services fail to start

**Solutions**:
```bash
# Check Docker is running
docker ps

# View logs
docker compose logs

# Rebuild containers
docker compose up -d --build --force-recreate

# Check ports are available
lsof -i :8010
lsof -i :8001
```

### Connection Refused Errors

**Problem**: Cannot connect to services

**Solutions**:
1. Wait 30-60 seconds after starting services
2. Check services are healthy:
   ```bash
   docker compose ps
   ```
3. Verify URLs:
   - QoE-Guard: http://localhost:8010
   - Demo Target: http://localhost:8001

### Validation Errors

**Problem**: Internal Server Error during validation

**Solutions**:
1. Check service logs:
   ```bash
   docker compose logs qoe-guard
   ```
2. Verify baseline is seeded:
   ```bash
   curl http://localhost:8010/seed
   ```
3. Check demo target is responding:
   ```bash
   curl http://localhost:8001/play?v=1
   ```

### Baseline Not Found

**Problem**: "No scenarios found" error

**Solution**:
```bash
# Seed baseline
curl http://localhost:8010/seed

# Or via browser
# Navigate to: http://localhost:8010/seed
```

## API Endpoints Reference

### QoE-Guard API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard |
| `/seed` | GET | Seed baseline scenario |
| `/run?v={n}` | GET | Run validation (v=1,2,3,4) |
| `/runs` | GET | List all validation runs |
| `/runs/{id}/report` | GET | View validation report |
| `/swagger` | GET | Swagger analyzer page |
| `/docs` | GET | API documentation |
| `/api/specs` | GET | List OpenAPI specs |
| `/api/validations` | GET | List validations |

### Demo Target API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/play?v={n}` | GET | Get playback config (v=1,2,3,4) |
| `/openapi.json` | GET | OpenAPI specification |

## Presentation Tips

### 15-Minute Demo Flow

1. **Introduction** (2 min)
   - Explain QoE-aware validation concept
   - Show dashboard

2. **Baseline Setup** (1 min)
   - Seed baseline
   - Explain what it represents

3. **PASS Scenario** (2 min)
   - Run v=3
   - Show low risk score
   - Explain safe changes

4. **WARN Scenario** (3 min)
   - Run v=2
   - Show moderate risk
   - Highlight type changes

5. **FAIL Scenario** (3 min)
   - Run v=4
   - Show high risk
   - Explain breaking changes

6. **Advanced Features** (2 min)
   - Swagger discovery
   - Multi-endpoint validation
   - Reports and analytics

7. **Q&A** (2 min)

### Key Points to Emphasize

1. **QoE-Aware**: Not just schema validation, but impact on user experience
2. **Quantified Risk**: Numeric scores for objective decision-making
3. **Hierarchical Analysis**: Deep understanding of changes
4. **Policy-Based Gating**: Automated PASS/WARN/FAIL decisions
5. **Enterprise Ready**: Governance, audit trails, approvals

## Next Steps

After the POC:

1. **Explore Advanced Features**:
   - AI/ML analysis (if configured)
   - Baseline governance workflows
   - Policy configuration

2. **Integration**:
   - CI/CD pipeline integration
   - Webhook notifications
   - Custom scoring models

3. **Customization**:
   - Define critical paths for your domain
   - Adjust policy thresholds
   - Configure notification channels

## Support

For issues or questions:
- Check logs: `docker compose logs`
- Review documentation: `docs/APP_WALKTHROUGH.md`
- API docs: http://localhost:8010/docs

## Cleanup

To stop all services:

```bash
docker compose down
```

To remove all data:

```bash
docker compose down -v
rm -rf data/*.json
```
