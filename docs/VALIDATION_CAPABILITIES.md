# QoE-Guard Validation Capabilities

> **Complete Guide: Swagger Page Validation, JSON Validation, and cURL Generation**

---

## ✅ Your Understanding is Correct!

QoE-Guard supports **three powerful validation methods**:

1. ✅ **Entire Swagger Page Validation** - Import and validate all endpoints from an OpenAPI spec
2. ✅ **Direct JSON Validation** - Validate JSON files or responses directly
3. ✅ **cURL Command Generation** - Generate executable cURL commands for testing

---

## 1. 🎯 Entire Swagger Page Validation

### Overview

Import a complete Swagger/OpenAPI specification and validate all or selected endpoints against a live API.

### How It Works

1. **Import Swagger Spec**
   - Enter Swagger/OpenAPI URL
   - System discovers all endpoints
   - Extracts operations, schemas, parameters

2. **Select Endpoints**
   - Choose specific endpoints or select all
   - Filter by HTTP method (GET, POST, etc.)
   - Filter by tags/categories

3. **Run Validation**
   - Configure target API URL
   - Set concurrency and rate limits
   - Execute validation jobs

4. **Get Results**
   - Brittleness scores per endpoint
   - QoE risk assessments
   - Schema conformance reports
   - Drift detection

### Example: Validating Entire Petstore API

```bash
# Step 1: Import via API
curl -X POST http://localhost:8010/specs/discover \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://petstore3.swagger.io/api/v3/openapi.json"
  }'

# Step 2: Get operations
curl http://localhost:8010/specs/{spec_id}/operations

# Step 3: Create validation job
curl -X POST http://localhost:8010/validations/ \
  -H "Content-Type: application/json" \
  -d '{
    "spec_id": "spec-id-here",
    "selected_operations": ["op1", "op2", "op3"],
    "environment": "dev",
    "concurrency": 5,
    "safe_methods_only": true
  }'
```

### UI Workflow

1. Go to **Endpoint Inventory** (`/inventory`)
2. Enter Swagger URL: `https://api.example.com/openapi.json`
3. Click **"Discover & Import"**
4. Click **"View"** to see all operations
5. Select endpoints (checkboxes)
6. Click **"Validate Selected"**
7. Configure and run validation

### What Gets Validated

- ✅ **Schema Conformance** - Response matches OpenAPI schema
- ✅ **Status Codes** - Expected vs actual HTTP codes
- ✅ **Response Times** - Latency measurements
- ✅ **Field Presence** - Required fields are present
- ✅ **Type Matching** - Values match expected types
- ✅ **Breaking Changes** - Detects breaking changes
- ✅ **Drift Detection** - Spec vs runtime drift

---

## 2. 📄 Direct JSON Validation

### Overview

Validate JSON directly without importing a Swagger spec. Compare baseline vs candidate JSON and get risk scores.

### Methods

#### Method 1: CLI (Command Line)

```bash
# Validate JSON files
qoe-guard validate \
  --baseline baseline.json \
  --candidate candidate.json

# Validate from URLs
qoe-guard validate \
  --baseline-url https://api.prod/v1/playback \
  --candidate-url https://api.staging/v1/playback \
  --header "Authorization: Bearer TOKEN"

# Output formats
qoe-guard validate -b baseline.json -c candidate.json --format json
qoe-guard validate -b baseline.json -c candidate.json --format summary
qoe-guard validate -b baseline.json -c candidate.json --format github
```

#### Method 2: API Endpoint

```bash
# Use the validation API with JSON payloads
curl -X POST http://localhost:8010/validations/ \
  -H "Content-Type: application/json" \
  -d '{
    "baseline_json": {...},
    "candidate_json": {...}
  }'
```

#### Method 3: Web UI (AI Analysis Page)

1. Go to **AI Analysis** (`/ai-analysis`)
2. Use **LLM Diff Analysis** or **Semantic Drift Detection**
3. Paste baseline and candidate JSON
4. Get detailed analysis

### Example: JSON Validation

**Baseline JSON:**
```json
{
  "playback": {
    "manifestUrl": "https://cdn.example.com/stream.m3u8",
    "quality": "HD",
    "maxBitrateKbps": 8000
  },
  "drm": {
    "licenseUrl": "https://drm.example.com/license",
    "type": "widevine"
  }
}
```

**Candidate JSON:**
```json
{
  "playback": {
    "url": "https://cdn-new.example.com/manifest.mpd",
    "resolution": "1080p",
    "maxBitrate": "6000"
  },
  "drm": {
    "license": "https://drm-v2.example.com/license",
    "provider": "widevine"
  }
}
```

**CLI Command:**
```bash
# Save JSONs to files
echo '{"playback": {...}}' > baseline.json
echo '{"playback": {...}}' > candidate.json

# Validate
qoe-guard validate -b baseline.json -c candidate.json
```

**Output:**
```
╔══════════════════════════════════════════╗
║        QoE-Guard Validation Report       ║
╠══════════════════════════════════════════╣
║  Decision:                          FAIL ║
║  Risk Score:                      0.8523 ║
║  Changes:                              8 ║
╠══════════════════════════════════════════╣
║  Top Signals:                            ║
║    Field removed:                       3 ║
║    Type changed:                        2 ║
║    Field renamed:                       3 ║
╚══════════════════════════════════════════╝

Path-level changes:
  [removed] $.playback.manifestUrl
  [added] $.playback.url
  [type_changed] $.playback.maxBitrateKbps: integer → string
  [removed] $.drm.licenseUrl
  [added] $.drm.license
  ...
```

### Exit Codes (CLI)

- `0` = **PASS** (safe to deploy)
- `1` = **WARN** (review recommended)
- `2` = **FAIL** (do not deploy)
- `3` = **ERROR** (validation failed)

### Use Cases

- ✅ **CI/CD Integration** - Validate API responses in pipelines
- ✅ **Local Testing** - Compare JSON files before deployment
- ✅ **API Versioning** - Compare old vs new API responses
- ✅ **Regression Testing** - Detect breaking changes

---

## 3. 🔧 cURL Command Generation

### Overview

Generate executable cURL commands from OpenAPI operations with authentication, parameters, and request bodies.

### Features

- ✅ **Parameterization** - Auto-fills path and query parameters
- ✅ **Secret Redaction** - Redacts sensitive headers/tokens
- ✅ **Environment Variables** - Uses env vars for secrets
- ✅ **Multiple Formats** - Script, JSON, Markdown
- ✅ **Authentication** - Supports Bearer, API Key, Basic Auth

### How to Generate cURL

#### Method 1: UI (Endpoint Inventory)

1. Go to **Endpoint Inventory** (`/inventory`)
2. Import Swagger spec
3. Select operations (checkboxes)
4. Click **"Generate cURL"** button
5. Copy generated commands

#### Method 2: API Endpoint

```bash
# Get cURL commands for operations
curl http://localhost:8010/specs/{spec_id}/operations/{op_id}/curl

# Get validation artifacts (includes cURL)
curl http://localhost:8010/validations/{run_id}/artifacts
```

#### Method 3: Python API

```python
from qoe_guard.curl import synthesize_curl, AuthConfig
from qoe_guard.swagger.inventory import NormalizedOperation

# Create auth config
auth = AuthConfig(
    auth_type="bearer",
    token_env_var="API_TOKEN",
    prefix="Bearer"
)

# Generate cURL
curl_cmd = synthesize_curl(
    operation=operation,
    base_url="https://api.example.com",
    auth_config=auth,
    param_values={"petId": "123"},
    redact_secrets=True
)

print(curl_cmd.command)
# curl -X GET 'https://api.example.com/pet/123' \
#   -H 'Authorization: Bearer [REDACTED]'
```

### Example: Generated cURL Commands

#### Basic GET Request

```bash
curl -X GET 'https://petstore3.swagger.io/api/v3/pet/findByStatus?status=available' \
  -H 'Accept: application/json'
```

#### POST Request with Body

```bash
curl -X POST 'https://petstore3.swagger.io/api/v3/pet' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ${API_TOKEN}' \
  -d '{
  "id": 1,
  "name": "doggie",
  "status": "available"
}'
```

#### With Environment Variables

```bash
#!/bin/bash
export API_TOKEN='your-token-here'

curl -X GET 'https://api.example.com/pet/123' \
  -H 'Authorization: Bearer ${API_TOKEN}'
```

### cURL Bundle Generation

Generate multiple cURL commands at once:

```python
from qoe_guard.curl import generate_curl_bundle

# Generate bash script
bundle = generate_curl_bundle(
    operations=selected_operations,
    base_url="https://api.example.com",
    auth_config=auth,
    output_format="script"  # or "json", "markdown"
)

print(bundle)
```

**Output (Script Format):**
```bash
#!/bin/bash
# QoE-Guard cURL Bundle
# Generated automatically

# Set these environment variables before running:
# export API_TOKEN='your-token-here'

set -e

# GET /pet/findByStatus
curl -X GET 'https://api.example.com/pet/findByStatus?status=available' \
  -H 'Authorization: Bearer ${API_TOKEN}'

# GET /pet/{petId}
curl -X GET 'https://api.example.com/pet/123' \
  -H 'Authorization: Bearer ${API_TOKEN}'
```

### Use Cases

- ✅ **API Testing** - Generate test commands quickly
- ✅ **Documentation** - Include cURL examples in docs
- ✅ **Postman Import** - Convert to Postman collections
- ✅ **CI/CD Scripts** - Use in automated testing
- ✅ **Developer Onboarding** - Provide ready-to-use commands

---

## 🎯 Complete Validation Workflow

### Scenario: Validate Entire API with JSON Comparison

1. **Import Swagger**
   ```bash
   # Import entire Swagger spec
   POST /specs/discover
   {
     "url": "https://api.example.com/openapi.json"
   }
   ```

2. **Generate cURL Commands**
   ```bash
   # Get cURL for all operations
   GET /specs/{id}/operations
   # Click "Generate cURL" in UI
   ```

3. **Run Validation**
   ```bash
   # Validate selected endpoints
   POST /validations/
   {
     "spec_id": "...",
     "selected_operations": ["op1", "op2"],
     "environment": "staging"
   }
   ```

4. **Compare JSON Responses**
   ```bash
   # Use CLI to compare responses
   qoe-guard validate \
     --baseline-url https://api.prod/v1/endpoint \
     --candidate-url https://api.staging/v1/endpoint
   ```

5. **Review Results**
   - Brittleness scores
   - QoE risk assessments
   - Breaking change detection
   - Schema conformance

---

## 📊 Comparison Table

| Feature | Swagger Validation | JSON Validation | cURL Generation |
|---------|-------------------|-----------------|-----------------|
| **Input** | OpenAPI URL | JSON files/URLs | OpenAPI operations |
| **Output** | Validation report | Risk score | Executable commands |
| **Use Case** | Full API testing | Quick comparison | API testing |
| **CI/CD** | ✅ Yes | ✅ Yes | ✅ Yes |
| **UI Support** | ✅ Yes | ✅ Yes | ✅ Yes |
| **CLI Support** | ❌ No | ✅ Yes | ❌ No |
| **Schema Validation** | ✅ Yes | ❌ No | ❌ No |
| **Authentication** | ✅ Yes | ✅ Yes | ✅ Yes |

---

## 🚀 Quick Start Examples

### Example 1: Validate Entire Swagger Page

```bash
# 1. Import
curl -X POST http://localhost:8010/specs/discover \
  -d '{"url": "https://petstore3.swagger.io/api/v3/openapi.json"}'

# 2. Get spec ID from response, then validate
curl -X POST http://localhost:8010/validations/ \
  -d '{
    "spec_id": "spec-id",
    "selected_operations": ["all"],
    "environment": "dev"
  }'
```

### Example 2: Validate JSON Files

```bash
# Create test files
cat > baseline.json << EOF
{"status": "ok", "data": {"id": 1}}
EOF

cat > candidate.json << EOF
{"status": "ok", "data": {"id": "1"}}
EOF

# Validate
qoe-guard validate -b baseline.json -c candidate.json
```

### Example 3: Generate cURL Commands

```python
from qoe_guard.curl import synthesize_curl

# Generate cURL for an operation
curl = synthesize_curl(
    operation=operation,
    base_url="https://api.example.com",
    auth_config=AuthConfig(auth_type="bearer")
)

print(curl.command)
```

---

## ✅ Summary

**Yes, your understanding is 100% correct!** QoE-Guard supports:

1. ✅ **Entire Swagger Page Validation** - Import and validate all endpoints
2. ✅ **Direct JSON Validation** - Validate JSON files/URLs via CLI or API
3. ✅ **cURL Command Generation** - Generate executable cURL commands

All three methods work together to provide comprehensive API validation capabilities!

---

## 📚 Related Documentation

- **Testing Guide:** `docs/TESTING_GUIDE.md`
- **E2E Test Results:** `docs/E2E_TEST_RESULTS.md`
- **App Walkthrough:** `docs/APP_WALKTHROUGH.md`
- **API Reference:** `http://localhost:8010/docs`

---

**Ready to validate?** Start with the Swagger Petstore API and explore all three validation methods! 🚀
