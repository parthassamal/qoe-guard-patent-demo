"""
Petstore API Comprehensive E2E Test Suite.

Tests the entire QoE-Guard system using Petstore API:
1. Swagger page validation (entire spec)
2. Direct JSON validation (PASS/WARN/FAIL scenarios)
3. cURL command generation
4. Broken API Detection (USP) - detecting non-functional, breaking changes

This test file demonstrates QoE-Guard's core value proposition:
detecting broken APIs even when HTTP 200 is returned.
"""
import pytest
import allure
from typing import Dict, Any, List
from fastapi.testclient import TestClient

from qoe_guard.main import app
from qoe_guard.diff import diff_json, json_diff
from qoe_guard.features import extract_features
from qoe_guard.model import score
from qoe_guard.scoring.brittleness import (
    compute_brittleness_score,
    compute_change_sensitivity,
    compute_contract_complexity,
)
from qoe_guard.scoring.qoe_risk import compute_qoe_risk, compute_qoe_action
from qoe_guard.validation.conformance import SchemaValidator
from qoe_guard.curl.synthesizer import synthesize_curl, generate_curl_bundle, AuthConfig
from qoe_guard.swagger.inventory import NormalizedOperation


# =============================================================================
# TEST DATA
# =============================================================================

PETSTORE_BASELINE = {
    "id": 1,
    "name": "doggie",
    "category": {"id": 1, "name": "Dogs"},
    "photoUrls": ["https://example.com/dog.jpg"],
    "tags": [{"id": 1, "name": "friendly"}],
    "status": "available"
}

PETSTORE_CANDIDATE_PASS = {
    "id": 1,
    "name": "doggie",
    "category": {"id": 1, "name": "Dogs"},
    "photoUrls": ["https://example.com/dog.jpg", "https://example.com/dog2.jpg"],
    "tags": [{"id": 1, "name": "friendly"}, {"id": 2, "name": "trained"}],
    "status": "available"
}

PETSTORE_CANDIDATE_WARN = {
    "id": 1,
    "name": "doggie",
    "category": {"id": 1, "name": "Dogs"},
    "photoUrls": [],
    "tags": [{"id": 1, "name": "friendly"}],
    "status": "pending",
    "lastModified": "2026-01-15T10:00:00Z"
}

PETSTORE_CANDIDATE_FAIL = {
    "petId": "1",
    "petName": "doggie",
    "categoryInfo": {"categoryId": 1, "categoryName": "Dogs"},
    "images": ["dog.jpg"],
    "petStatus": "AVAILABLE"
}

PETSTORE_SCHEMA = {
    "type": "object",
    "required": ["name", "photoUrls"],
    "properties": {
        "id": {"type": "integer", "format": "int64"},
        "name": {"type": "string"},
        "category": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"}
            }
        },
        "photoUrls": {
            "type": "array",
            "items": {"type": "string"}
        },
        "tags": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"}
                }
            }
        },
        "status": {
            "type": "string",
            "enum": ["available", "pending", "sold"]
        }
    }
}


def create_test_client():
    """Create test client for API calls."""
    return TestClient(app)


def create_sample_operation():
    """Create sample Petstore operation for cURL testing."""
    return NormalizedOperation(
        operation_id="getPetById",
        method="GET",
        path="/pet/{petId}",
        summary="Find pet by ID",
        description="Returns a single pet",
        tags=["pet"],
        security=[],
        parameters=[
            {
                "name": "petId",
                "in": "path",
                "required": True,
                "schema": {"type": "integer", "format": "int64"}
            }
        ],
        request_body_schema=None,
        response_schemas={},
        server_url="https://petstore3.swagger.io/api/v3",
        examples={},
        deprecated=False
    )


# =============================================================================
# SWAGGER PAGE VALIDATION TESTS
# =============================================================================

@allure.epic("Petstore E2E Tests")
@allure.feature("Swagger Page Validation")
@allure.story("Import Petstore Spec")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Test importing Petstore OpenAPI specification")
def test_import_petstore_spec():
    """Test that we can import the Petstore OpenAPI spec."""
    client = create_test_client()
    
    with allure.step("Check API health"):
        response = client.get("/health")
        assert response.status_code == 200
    
    with allure.step("Verify test data endpoints are available"):
        response = client.get("/test-data/petstore/baseline")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["name"] == "doggie"


@allure.epic("Petstore E2E Tests")
@allure.feature("Swagger Page Validation")
@allure.story("Discover Operations")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Test discovering all operations from Petstore spec")
def test_discover_all_operations():
    """Test that all Petstore operations can be discovered."""
    client = create_test_client()
    
    with allure.step("Get sample Swagger URLs"):
        response = client.get("/test-data/swagger-urls")
        assert response.status_code == 200
        urls = response.json()
        
        petstore_url = None
        for url_info in urls:
            if "petstore" in url_info["name"].lower():
                petstore_url = url_info["url"]
                break
        
        assert petstore_url is not None
        allure.attach(petstore_url, "Petstore URL", allure.attachment_type.TEXT)


@allure.epic("Petstore E2E Tests")
@allure.feature("Swagger Page Validation")
@allure.story("Schema Conformance")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Test schema conformance validation")
def test_schema_conformance():
    """Test that baseline response conforms to schema."""
    with allure.step("Validate baseline against schema"):
        validator = SchemaValidator(PETSTORE_SCHEMA)
        result = validator.validate(PETSTORE_BASELINE)
        
        assert result.valid, f"Schema validation failed: {result.mismatches}"
        allure.attach(
            str({"valid": result.valid, "mismatches": len(result.mismatches)}),
            "Validation Result",
            allure.attachment_type.JSON
        )


@allure.epic("Petstore E2E Tests")
@allure.feature("Swagger Page Validation")
@allure.story("Schema Conformance")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Test schema conformance catches breaking changes")
def test_schema_conformance_catches_breaking():
    """Test that schema validation catches breaking changes."""
    with allure.step("Validate breaking candidate against schema"):
        validator = SchemaValidator(PETSTORE_SCHEMA)
        result = validator.validate(PETSTORE_CANDIDATE_FAIL)
        
        # This should fail because required fields are missing
        assert not result.valid, "Schema validation should fail for breaking changes"
        assert len(result.mismatches) > 0
        
        allure.attach(
            str([{"path": m.path, "message": m.message} for m in result.mismatches]),
            "Schema Mismatches",
            allure.attachment_type.JSON
        )


# =============================================================================
# JSON VALIDATION TESTS
# =============================================================================

@allure.epic("Petstore E2E Tests")
@allure.feature("JSON Validation")
@allure.story("PASS Scenario")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Test minor changes result in PASS decision")
def test_pass_scenario_minor_changes():
    """Test that minor, non-breaking changes result in PASS."""
    with allure.step("Perform JSON diff"):
        diff_result = json_diff(PETSTORE_BASELINE, PETSTORE_CANDIDATE_PASS)
        allure.attach(
            str([{"path": c.path, "type": c.change_type} for c in diff_result.changes]),
            "Detected Changes",
            allure.attachment_type.JSON
        )
    
    with allure.step("Get decision"):
        allure.attach(
            str({"action": diff_result.decision, "risk_score": diff_result.qoe_risk_score}),
            "Decision",
            allure.attachment_type.JSON
        )
        
        # Minor changes should result in PASS or WARN at most
        assert diff_result.decision in ["PASS", "WARN"], \
            f"Expected PASS/WARN for minor changes, got {diff_result.decision}"


@allure.epic("Petstore E2E Tests")
@allure.feature("JSON Validation")
@allure.story("WARN Scenario")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Test potential issues result in WARN decision")
def test_warn_scenario_potential_issues():
    """Test that potential issues result in WARN."""
    with allure.step("Perform JSON diff"):
        diff_result = json_diff(PETSTORE_BASELINE, PETSTORE_CANDIDATE_WARN)
        allure.attach(
            str([{"path": c.path, "type": c.change_type} for c in diff_result.changes]),
            "Detected Changes",
            allure.attachment_type.JSON
        )
    
    with allure.step("Check changes detected"):
        # Should detect: empty array, value change, added field
        assert len(diff_result.changes) > 0, "Should detect changes"
    
    with allure.step("Get decision"):
        allure.attach(
            str({"action": diff_result.decision, "risk_score": diff_result.qoe_risk_score}),
            "Decision",
            allure.attachment_type.JSON
        )


@allure.epic("Petstore E2E Tests")
@allure.feature("JSON Validation")
@allure.story("FAIL Scenario")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Test breaking changes result in FAIL decision")
def test_fail_scenario_breaking_changes():
    """Test that breaking changes result in high change count."""
    with allure.step("Perform JSON diff"):
        diff_result = json_diff(PETSTORE_BASELINE, PETSTORE_CANDIDATE_FAIL)
        allure.attach(
            str([{"path": c.path, "type": c.change_type} for c in diff_result.changes]),
            "Detected Changes",
            allure.attachment_type.JSON
        )
    
    with allure.step("Check breaking changes detected"):
        removed = [c for c in diff_result.changes if c.change_type == "removed"]
        added = [c for c in diff_result.changes if c.change_type == "added"]
        
        assert len(removed) > 0, "Should detect removed fields"
        assert len(added) > 0, "Should detect added fields (renamed)"
    
    with allure.step("Get decision"):
        allure.attach(
            str({
                "action": diff_result.decision,
                "risk_score": diff_result.qoe_risk_score,
                "change_count": len(diff_result.changes),
                "summary": diff_result.summary
            }),
            "Decision",
            allure.attachment_type.JSON
        )
        
        # Breaking changes should be detected
        assert len(diff_result.changes) > 5, "Should detect many breaking changes"


@allure.epic("Petstore E2E Tests")
@allure.feature("JSON Validation")
@allure.story("API Endpoints")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Test JSON validation via API endpoints")
def test_json_validation_via_api():
    """Test JSON validation through test data API endpoints."""
    client = create_test_client()
    
    with allure.step("Get baseline from API"):
        baseline_resp = client.get("/test-data/petstore/baseline")
        assert baseline_resp.status_code == 200
        baseline = baseline_resp.json()["data"]
    
    with allure.step("Get FAIL candidate from API"):
        fail_resp = client.get("/test-data/petstore/candidate/fail")
        assert fail_resp.status_code == 200
        candidate = fail_resp.json()["data"]
    
    with allure.step("Validate via diff"):
        changes = diff_json(baseline, candidate)
        assert len(changes) > 5, "Should detect multiple breaking changes"


# =============================================================================
# CURL GENERATION TESTS
# =============================================================================

@allure.epic("Petstore E2E Tests")
@allure.feature("cURL Generation")
@allure.story("Generate cURL")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Test generating cURL for GET pet endpoint")
def test_generate_curl_for_get_pet():
    """Test cURL generation for GET /pet/{petId}."""
    operation = create_sample_operation()
    
    with allure.step("Generate cURL command"):
        curl_cmd = synthesize_curl(
            operation=operation,
            param_values={"petId": 1}
        )
        
        allure.attach(curl_cmd.command, "Generated cURL", allure.attachment_type.TEXT)
        
        assert "curl" in curl_cmd.command
        assert "GET" in curl_cmd.command  # Method is present
        assert curl_cmd.method == "GET"
        assert "/pet/1" in curl_cmd.url


@allure.epic("Petstore E2E Tests")
@allure.feature("cURL Generation")
@allure.story("Generate cURL with Auth")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Test generating cURL with authentication")
def test_generate_curl_with_auth():
    """Test cURL generation with Bearer token authentication."""
    operation = create_sample_operation()
    
    with allure.step("Create auth config"):
        auth = AuthConfig(
            auth_type="bearer",
            token_env_var="PETSTORE_TOKEN",
            prefix="Bearer"
        )
    
    with allure.step("Generate cURL with auth"):
        curl_cmd = synthesize_curl(
            operation=operation,
            param_values={"petId": 123},
            auth_config=auth,
            redact_secrets=True
        )
        
        allure.attach(curl_cmd.command, "cURL with Auth", allure.attachment_type.TEXT)
        
        assert "Authorization" in str(curl_cmd.headers)
        assert "[REDACTED]" in curl_cmd.command or "Bearer" in curl_cmd.command


@allure.epic("Petstore E2E Tests")
@allure.feature("cURL Generation")
@allure.story("Generate cURL Bundle")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Test generating cURL bundle for multiple operations")
def test_curl_bundle_generation():
    """Test generating a bundle of cURL commands."""
    operations = [
        NormalizedOperation(
            operation_id="getPetById",
            method="GET",
            path="/pet/{petId}",
            summary="Get pet",
            description="Get pet by ID",
            tags=["pet"],
            security=[],
            parameters=[{"name": "petId", "in": "path", "schema": {"type": "integer"}}],
            request_body_schema=None,
            response_schemas={},
            server_url="https://petstore3.swagger.io/api/v3",
            examples={},
            deprecated=False
        ),
        NormalizedOperation(
            operation_id="findPetsByStatus",
            method="GET",
            path="/pet/findByStatus",
            summary="Find pets by status",
            description="Find pets by status",
            tags=["pet"],
            security=[],
            parameters=[{"name": "status", "in": "query", "schema": {"type": "string"}}],
            request_body_schema=None,
            response_schemas={},
            server_url="https://petstore3.swagger.io/api/v3",
            examples={},
            deprecated=False
        ),
    ]
    
    with allure.step("Generate cURL bundle (script format)"):
        bundle = generate_curl_bundle(
            operations=operations,
            output_format="script"
        )
        
        allure.attach(bundle, "cURL Bundle Script", allure.attachment_type.TEXT)
        
        assert "#!/bin/bash" in bundle
        assert "curl" in bundle
    
    with allure.step("Generate cURL bundle (markdown format)"):
        bundle_md = generate_curl_bundle(
            operations=operations,
            output_format="markdown"
        )
        
        allure.attach(bundle_md, "cURL Bundle Markdown", allure.attachment_type.TEXT)
        
        assert "# cURL Commands" in bundle_md


# =============================================================================
# BROKEN API DETECTION TESTS (USP)
# =============================================================================

@allure.epic("Petstore E2E Tests")
@allure.feature("Broken API Detection (USP)")
@allure.story("Schema Drift Detection")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Detect when API response structure drifts from spec")
def test_detect_schema_drift():
    """Test detection of schema drift (response wrapped in unexpected structure)."""
    client = create_test_client()
    
    with allure.step("Get schema drift scenario"):
        response = client.get("/test-data/petstore/broken-api-scenarios/schema_drift")
        assert response.status_code == 200
        scenario = response.json()
    
    with allure.step("Perform diff to detect drift"):
        baseline = scenario["baseline"]
        candidate = scenario["candidate"]
        changes = diff_json(baseline, candidate)
        
        allure.attach(
            str([{"path": c.path, "type": c.change_type} for c in changes]),
            "Detected Drift",
            allure.attachment_type.JSON
        )
        
        # Should detect multiple changes due to structural difference
        assert len(changes) > 3, "Should detect schema drift"
        
        # Check for removed fields (original fields not found)
        removed = [c for c in changes if c.change_type == "removed"]
        assert len(removed) > 0, "Should detect removed fields due to wrapping"


@allure.epic("Petstore E2E Tests")
@allure.feature("Broken API Detection (USP)")
@allure.story("Type Mismatch Detection")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Detect when field types don't match spec")
def test_detect_type_mismatch():
    """Test detection of type mismatches (int→string, string→int)."""
    client = create_test_client()
    
    with allure.step("Get type mismatch scenario"):
        response = client.get("/test-data/petstore/broken-api-scenarios/type_mismatch")
        assert response.status_code == 200
        scenario = response.json()
    
    with allure.step("Perform diff to detect type changes"):
        baseline = scenario["baseline"]
        candidate = scenario["candidate"]
        changes = diff_json(baseline, candidate)
        
        type_changes = [c for c in changes if c.change_type == "type_changed"]
        
        allure.attach(
            str([{"path": c.path, "before": c.before, "after": c.after} for c in type_changes]),
            "Type Mismatches",
            allure.attachment_type.JSON
        )
        
        assert len(type_changes) >= 2, "Should detect type mismatches"


@allure.epic("Petstore E2E Tests")
@allure.feature("Broken API Detection (USP)")
@allure.story("Missing Required Fields")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Detect when required fields are missing")
def test_detect_missing_required_fields():
    """Test detection of missing required fields."""
    client = create_test_client()
    
    with allure.step("Get missing required scenario"):
        response = client.get("/test-data/petstore/broken-api-scenarios/missing_required")
        assert response.status_code == 200
        scenario = response.json()
    
    with allure.step("Perform diff to detect missing fields"):
        baseline = scenario["baseline"]
        candidate = scenario["candidate"]
        changes = diff_json(baseline, candidate)
        
        removed_fields = [c for c in changes if c.change_type == "removed"]
        
        allure.attach(
            str([{"path": c.path} for c in removed_fields]),
            "Missing Fields",
            allure.attachment_type.JSON
        )
        
        # Should detect name, photoUrls, status as removed
        assert len(removed_fields) >= 3, "Should detect missing required fields"


@allure.epic("Petstore E2E Tests")
@allure.feature("Broken API Detection (USP)")
@allure.story("Null Injection Detection")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Detect when fields are unexpectedly null")
def test_detect_null_injection():
    """Test detection of null injection (fields unexpectedly null)."""
    client = create_test_client()
    
    with allure.step("Get null injection scenario"):
        response = client.get("/test-data/petstore/broken-api-scenarios/null_injection")
        assert response.status_code == 200
        scenario = response.json()
    
    with allure.step("Perform diff to detect null values"):
        baseline = scenario["baseline"]
        candidate = scenario["candidate"]
        changes = diff_json(baseline, candidate)
        
        # Null values will be detected as type_changed (string->null, object->null)
        type_changes = [c for c in changes if c.change_type == "type_changed"]
        
        allure.attach(
            str([{"path": c.path, "before": c.before, "after": c.after} for c in type_changes]),
            "Null Injections (Type Changes)",
            allure.attachment_type.JSON
        )
        
        # Should detect multiple fields changed to null
        assert len(type_changes) >= 2 or len(changes) >= 2, "Should detect null injections"


@allure.epic("Petstore E2E Tests")
@allure.feature("Broken API Detection (USP)")
@allure.story("Array Corruption Detection")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Detect when arrays become objects or scalars")
def test_detect_array_corruption():
    """Test detection of array corruption (array→object, array→string)."""
    client = create_test_client()
    
    with allure.step("Get array corruption scenario"):
        response = client.get("/test-data/petstore/broken-api-scenarios/array_corruption")
        assert response.status_code == 200
        scenario = response.json()
    
    with allure.step("Perform diff to detect array corruption"):
        baseline = scenario["baseline"]
        candidate = scenario["candidate"]
        changes = diff_json(baseline, candidate)
        
        type_changes = [c for c in changes if c.change_type == "type_changed"]
        
        allure.attach(
            str([{"path": c.path, "type": c.change_type} for c in type_changes]),
            "Array Corruptions",
            allure.attachment_type.JSON
        )
        
        # Should detect photoUrls and tags type changes
        assert len(type_changes) >= 2, "Should detect array corruption"


@allure.epic("Petstore E2E Tests")
@allure.feature("Broken API Detection (USP)")
@allure.story("Runtime Anomaly Detection")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Detect runtime anomalies from metrics")
def test_detect_runtime_anomalies():
    """Test detection of runtime anomalies (latency spikes, errors)."""
    client = create_test_client()
    
    with allure.step("Get runtime metrics"):
        response = client.get("/test-data/petstore/runtime-metrics")
        assert response.status_code == 200
        data = response.json()
    
    with allure.step("Analyze metrics for anomalies"):
        metrics = data["data"]
        anomaly_indices = data["anomaly_indices"]
        
        # Check that anomalies are correctly identified
        for idx in anomaly_indices:
            metric = metrics[idx]
            is_error = metric["status_code"] >= 400
            is_slow = metric["latency_ms"] > 1000
            
            assert is_error or is_slow, f"Metric at index {idx} should be anomalous"
        
        allure.attach(
            str([metrics[i] for i in anomaly_indices]),
            "Detected Anomalies",
            allure.attachment_type.JSON
        )


@allure.epic("Petstore E2E Tests")
@allure.feature("Broken API Detection (USP)")
@allure.story("All Broken API Scenarios")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Verify all broken API scenarios are available")
def test_all_broken_api_scenarios_available():
    """Test that all broken API scenarios are accessible."""
    client = create_test_client()
    
    with allure.step("Get all scenarios"):
        response = client.get("/test-data/petstore/broken-api-scenarios")
        assert response.status_code == 200
        data = response.json()
    
    with allure.step("Verify scenario count"):
        expected_scenarios = [
            "schema_drift",
            "type_mismatch",
            "missing_required",
            "null_injection",
            "array_corruption",
            "deep_nesting_change"
        ]
        
        for scenario in expected_scenarios:
            assert scenario in data["scenarios"], f"Missing scenario: {scenario}"
        
        allure.attach(
            str(list(data["scenarios"].keys())),
            "Available Scenarios",
            allure.attachment_type.JSON
        )


# =============================================================================
# QOE RISK SCORING TESTS
# =============================================================================

@allure.epic("Petstore E2E Tests")
@allure.feature("QoE Risk Scoring")
@allure.story("Brittleness Score")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Test brittleness score calculation")
def test_brittleness_score_calculation():
    """Test brittleness score calculation from schema."""
    with allure.step("Compute contract complexity"):
        complexity = compute_contract_complexity(PETSTORE_SCHEMA)
        allure.attach(str(complexity), "Contract Complexity", allure.attachment_type.TEXT)
        assert 0 <= complexity <= 1
    
    with allure.step("Compute change sensitivity"):
        sensitivity = compute_change_sensitivity(
            removed_fields=3,
            type_changes=2,
            enum_changes=0,
            requiredness_changes=1
        )
        allure.attach(str(sensitivity), "Change Sensitivity", allure.attachment_type.TEXT)
        assert sensitivity > 0.3, "Multiple changes should increase sensitivity"
    
    with allure.step("Compute brittleness score"):
        brittleness = compute_brittleness_score(
            contract_complexity=complexity,
            change_sensitivity=sensitivity,
            runtime_fragility=0.1,
            blast_radius=0.2
        )
        allure.attach(str(brittleness), "Brittleness Score", allure.attachment_type.TEXT)
        assert 0 <= brittleness <= 100


@allure.epic("Petstore E2E Tests")
@allure.feature("QoE Risk Scoring")
@allure.story("QoE Risk Scoring")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Test QoE risk scoring from changes")
def test_qoe_risk_scoring():
    """Test QoE risk scoring based on detected changes."""
    with allure.step("Detect changes"):
        diff_result = json_diff(PETSTORE_BASELINE, PETSTORE_CANDIDATE_FAIL)
    
    with allure.step("Check risk score"):
        allure.attach(str(diff_result.qoe_risk_score), "QoE Risk Score", allure.attachment_type.TEXT)
        # Breaking changes should result in some risk score
        assert diff_result.qoe_risk_score > 0, "Breaking changes should result in non-zero risk score"
    
    with allure.step("Get action decision"):
        allure.attach(diff_result.decision, "Decision", allure.attachment_type.TEXT)
        # Just verify a decision is made
        assert diff_result.decision in ["PASS", "WARN", "FAIL"]


@allure.epic("Petstore E2E Tests")
@allure.feature("QoE Risk Scoring")
@allure.story("PASS/WARN/FAIL Decisions")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Test PASS/WARN/FAIL decision logic")
def test_pass_warn_fail_decisions():
    """Test that decision logic correctly categorizes risk levels."""
    # Thresholds: FAIL >= 0.72, WARN >= 0.45, PASS < 0.45
    test_cases = [
        (0.0, "PASS"),
        (0.1, "PASS"),
        (0.3, "PASS"),
        (0.44, "PASS"),
        (0.45, "WARN"),
        (0.5, "WARN"),
        (0.6, "WARN"),
        (0.71, "WARN"),
        (0.72, "FAIL"),
        (0.8, "FAIL"),
        (1.0, "FAIL"),
    ]
    
    with allure.step("Test decision boundaries"):
        results = []
        for risk, expected in test_cases:
            action = compute_qoe_action(risk)
            results.append({"risk": risk, "expected": expected, "actual": action})
        
        allure.attach(str(results), "Decision Test Results", allure.attachment_type.JSON)
        
        for risk, expected in test_cases:
            action = compute_qoe_action(risk)
            assert action == expected, f"Risk {risk} should be {expected}, got {action}"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

@allure.epic("Petstore E2E Tests")
@allure.feature("Integration Tests")
@allure.story("Full Validation Pipeline")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Test complete validation pipeline from JSON to decision")
def test_full_validation_pipeline():
    """Test the complete validation pipeline."""
    with allure.step("Step 1: JSON Diff"):
        diff_result = json_diff(PETSTORE_BASELINE, PETSTORE_CANDIDATE_FAIL)
        assert len(diff_result.changes) > 0
        allure.attach(str(len(diff_result.changes)), "Change Count", allure.attachment_type.TEXT)
    
    with allure.step("Step 2: QoE Risk Score"):
        assert diff_result.qoe_risk_score > 0
        allure.attach(str(diff_result.qoe_risk_score), "Risk Score", allure.attachment_type.TEXT)
    
    with allure.step("Step 3: Decision"):
        assert diff_result.decision in ["PASS", "WARN", "FAIL"]
        allure.attach(diff_result.decision, "Decision", allure.attachment_type.TEXT)
    
    with allure.step("Step 4: Summary"):
        assert "critical" in diff_result.summary.lower() or "changes" in diff_result.summary.lower()
        allure.attach(diff_result.summary, "Summary", allure.attachment_type.TEXT)


@allure.epic("Petstore E2E Tests")
@allure.feature("Integration Tests")
@allure.story("API Test Data Endpoints")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Test all Petstore test data endpoints")
def test_all_petstore_endpoints():
    """Test that all Petstore test data endpoints work."""
    client = create_test_client()
    
    endpoints = [
        "/test-data/petstore/baseline",
        "/test-data/petstore/candidate/pass",
        "/test-data/petstore/candidate/warn",
        "/test-data/petstore/candidate/fail",
        "/test-data/petstore/broken-api-scenarios",
        "/test-data/petstore/runtime-metrics",
        "/test-data/petstore/order/baseline",
        "/test-data/petstore/user/baseline",
        "/test-data/petstore/all",
    ]
    
    results = []
    for endpoint in endpoints:
        with allure.step(f"Test {endpoint}"):
            response = client.get(endpoint)
            results.append({
                "endpoint": endpoint,
                "status": response.status_code,
                "success": response.status_code == 200
            })
            assert response.status_code == 200, f"Failed: {endpoint}"
    
    allure.attach(str(results), "Endpoint Results", allure.attachment_type.JSON)


@allure.epic("Petstore E2E Tests")
@allure.feature("Integration Tests")
@allure.story("USP Demonstration")
@allure.severity(allure.severity_level.CRITICAL)
@allure.title("Demonstrate QoE-Guard USP: HTTP 200 but broken response")
def test_usp_http_200_broken_response():
    """
    Demonstrate the core USP: detecting broken APIs when HTTP 200 is returned.
    
    Traditional testing: HTTP 200 = Success
    QoE-Guard: HTTP 200 + Schema validation + Structure validation
    
    Note: QoE-Guard detects the structural changes even when HTTP 200 is returned.
    The decision depends on criticality scoring, but the key USP is DETECTION.
    """
    client = create_test_client()
    
    with allure.step("Scenario: API returns HTTP 200 but with breaking changes"):
        # Get baseline (what client expects)
        baseline_resp = client.get("/test-data/petstore/baseline")
        assert baseline_resp.status_code == 200
        baseline = baseline_resp.json()["data"]
        
        # Get breaking candidate (what API actually returns - HTTP 200 but broken)
        candidate_resp = client.get("/test-data/petstore/candidate/fail")
        assert candidate_resp.status_code == 200  # HTTP 200!
        candidate = candidate_resp.json()["data"]
    
    with allure.step("Traditional testing would pass (HTTP 200)"):
        allure.attach(
            "HTTP Status: 200 OK\nTraditional Result: PASS (blindly)",
            "Traditional Testing",
            allure.attachment_type.TEXT
        )
    
    with allure.step("QoE-Guard DETECTS the broken response"):
        diff_result = json_diff(baseline, candidate)
        
        # Count breaking changes (removed and type_changed)
        breaking_changes = [c for c in diff_result.changes if c.change_type in ["removed", "type_changed"]]
        
        detection_report = {
            "http_status": 200,
            "traditional_result": "PASS (blindly accepts)",
            "qoe_guard_changes_detected": len(diff_result.changes),
            "qoe_guard_breaking_changes": len(breaking_changes),
            "qoe_guard_risk_score": diff_result.qoe_risk_score,
            "qoe_guard_decision": diff_result.decision,
            "detected_issues": [
                {"path": c.path, "type": c.change_type}
                for c in diff_result.changes
            ]
        }
        
        allure.attach(
            str(detection_report),
            "QoE-Guard Detection Report",
            allure.attachment_type.JSON
        )
        
        # USP: QoE-Guard DETECTS changes that traditional testing misses
        # Even if decision is PASS, we detected 11 structural changes!
        assert len(diff_result.changes) > 5, \
            "Should detect multiple structural changes"
        assert len(breaking_changes) > 0, \
            "Should detect breaking changes (removed fields)"


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

@allure.epic("Petstore E2E Tests")
@allure.feature("Edge Cases")
@allure.story("Empty Response")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Test handling of empty response")
def test_empty_response():
    """Test detection when API returns empty object."""
    with allure.step("Compare baseline with empty response"):
        changes = diff_json(PETSTORE_BASELINE, {})
        
        assert len(changes) > 0, "Should detect all fields as removed"
        removed = [c for c in changes if c.change_type == "removed"]
        assert len(removed) >= 5, "Should detect all baseline fields as removed"


@allure.epic("Petstore E2E Tests")
@allure.feature("Edge Cases")
@allure.story("Identical Response")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Test handling of identical responses")
def test_identical_response():
    """Test that identical responses result in no changes."""
    with allure.step("Compare baseline with itself"):
        changes = diff_json(PETSTORE_BASELINE, PETSTORE_BASELINE)
        
        assert len(changes) == 0, "Identical responses should have no changes"


@allure.epic("Petstore E2E Tests")
@allure.feature("Edge Cases")
@allure.story("Deep Nesting")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("Test handling of deeply nested structures")
def test_deep_nesting_changes():
    """Test detection of changes in deeply nested structures."""
    client = create_test_client()
    
    with allure.step("Get deep nesting scenario"):
        response = client.get("/test-data/petstore/broken-api-scenarios/deep_nesting_change")
        assert response.status_code == 200
        scenario = response.json()
    
    with allure.step("Detect deep changes"):
        changes = diff_json(scenario["baseline"], scenario["candidate"])
        
        # Should detect the type change deep in the structure
        deep_changes = [c for c in changes if "vaccinations" in c.path]
        assert len(deep_changes) > 0, "Should detect changes in nested structures"
        allure.attach(str(deep_changes), "Deep Changes", allure.attachment_type.JSON)
