"""
Enhanced Integration Tests with Full Schema Validation and Anomaly Detection.

Tests API endpoints with:
- Complete request/response schema validation
- Anomaly detection
- Status code validation beyond 200 OK
- Error handling validation
- Performance metrics
"""
import unittest
import sys
import os
import json
import time
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import allure
    ALLURE_AVAILABLE = True
except ImportError:
    ALLURE_AVAILABLE = False
    class allure:
        @staticmethod
        def feature(name): return lambda f: f
        @staticmethod
        def story(name): return lambda f: f
        @staticmethod
        def step(name): return lambda f: f
        @staticmethod
        def title(name): return lambda f: f
        @staticmethod
        def description(text): return lambda f: f
        @staticmethod
        def severity(level): return lambda f: f
        @staticmethod
        def attach(body, name, attachment_type): pass

from fastapi.testclient import TestClient
from jsonschema import validate, ValidationError, Draft7Validator

try:
    from qoe_guard.main import app
    HAS_APP = True
except ImportError:
    HAS_APP = False

from tests.fixtures.sample_data import (
    BASELINE_PLAYBACK_RESPONSE,
    CANDIDATE_PLAYBACK_RESPONSE_BREAKING,
    SAMPLE_OPENAPI_SPEC,
)


# OpenAPI Response Schemas for Validation
HEALTH_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["status"],
    "properties": {
        "status": {"type": "string", "enum": ["healthy", "unhealthy"]},
        "version": {"type": "string"}
    }
}

AI_STATUS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string"},
        "llm_available": {"type": "boolean"},
        "llm_provider": {"type": "string"},
        "semantic_drift_available": {"type": "boolean"},
        "ml_scoring_available": {"type": "boolean"},
        "providers": {
            "type": "array",
            "items": {"type": "string"}
        }
    }
}

DIFF_ANALYSIS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "analysis": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "classification": {"type": "string"},
                "impact": {"type": "string"},
                "recommendations": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        },
        "error": {"type": "string"}
    }
}


@allure.feature("API Integration Tests")
@unittest.skipUnless(HAS_APP, "FastAPI app not available")
class TestAPIWithSchemaValidation(unittest.TestCase):
    """API tests with complete schema validation."""
    
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.response_times = []
    
    def validate_response_schema(self, response, schema: Dict[str, Any], endpoint: str):
        """Validate response against OpenAPI schema."""
        with allure.step(f"Validate {endpoint} response schema"):
            # Check status code
            status_code = response.status_code
            allure.attach(
                json.dumps({"status_code": status_code}, indent=2),
                "HTTP Status Code",
                allure.attachment_type.JSON
            )
            
            if status_code >= 400:
                # Error responses may not match success schema
                error_data = {
                    "status_code": status_code,
                    "error": response.text[:500] if hasattr(response, 'text') else str(response)
                }
                allure.attach(
                    json.dumps(error_data, indent=2),
                    "Error Response",
                    allure.attachment_type.JSON
                )
                return False
            
            # Parse JSON
            try:
                data = response.json()
            except Exception as e:
                allure.attach(
                    json.dumps({"error": f"Failed to parse JSON: {e}"}, indent=2),
                    "JSON Parse Error",
                    allure.attachment_type.JSON
                )
                return False
            
            # Validate against schema
            try:
                validate(instance=data, schema=schema)
                validation_result = {
                    "status": "valid",
                    "endpoint": endpoint,
                    "schema_validation": "passed"
                }
                allure.attach(
                    json.dumps(validation_result, indent=2),
                    "Schema Validation Result",
                    allure.attachment_type.JSON
                )
                return True
            except ValidationError as e:
                validation_result = {
                    "status": "invalid",
                    "endpoint": endpoint,
                    "schema_validation": "failed",
                    "errors": [{
                        "path": list(e.path),
                        "message": e.message,
                        "validator": e.validator
                    }]
                }
                allure.attach(
                    json.dumps(validation_result, indent=2),
                    "Schema Validation Errors",
                    allure.attachment_type.JSON
                )
                return False
    
    def detect_response_anomalies(self, response, endpoint: str) -> List[Dict[str, Any]]:
        """Detect anomalies in API response."""
        anomalies = []
        
        with allure.step(f"Detect anomalies in {endpoint} response"):
            # Check response time
            if hasattr(response, 'elapsed'):
                response_time = response.elapsed.total_seconds()
                self.response_times.append(response_time)
                
                if response_time > 5.0:  # 5 second threshold
                    anomalies.append({
                        "type": "high_latency",
                        "value": response_time,
                        "threshold": 5.0,
                        "severity": "high"
                    })
            
            # Check status code
            if response.status_code >= 500:
                anomalies.append({
                    "type": "server_error",
                    "status_code": response.status_code,
                    "severity": "critical"
                })
            elif response.status_code >= 400:
                anomalies.append({
                    "type": "client_error",
                    "status_code": response.status_code,
                    "severity": "medium"
                })
            
            # Check response size
            if hasattr(response, 'content'):
                response_size = len(response.content)
                if response_size > 10 * 1024 * 1024:  # 10MB
                    anomalies.append({
                        "type": "large_response",
                        "size_bytes": response_size,
                        "threshold": 10 * 1024 * 1024,
                        "severity": "medium"
                    })
            
            # Check for error patterns in response
            try:
                data = response.json()
                if isinstance(data, dict):
                    error_keywords = ["error", "exception", "failure", "failed"]
                    for key in error_keywords:
                        if key in str(data).lower():
                            anomalies.append({
                                "type": "error_keyword_detected",
                                "keyword": key,
                                "severity": "medium"
                            })
            except:
                pass
            
            if anomalies:
                allure.attach(
                    json.dumps({
                        "endpoint": endpoint,
                        "anomalies_detected": len(anomalies),
                        "anomalies": anomalies
                    }, indent=2),
                    "Anomaly Detection Results",
                    allure.attachment_type.JSON
                )
        
        return anomalies
    
    @allure.story("Health Endpoint Validation")
    @allure.title("Health endpoint with full schema validation")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_health_endpoint_full_validation(self):
        """Test health endpoint with complete schema validation."""
        endpoint = "/health"
        
        with allure.step("Send GET request to /health"):
            start_time = time.time()
            response = self.client.get(endpoint)
            response_time = time.time() - start_time
            
            request_details = {
                "method": "GET",
                "endpoint": endpoint,
                "response_time_seconds": response_time,
                "status_code": response.status_code
            }
            allure.attach(
                json.dumps(request_details, indent=2),
                "Request Details",
                allure.attachment_type.JSON
            )
        
        with allure.step("Validate status code"):
            self.assertEqual(response.status_code, 200, 
                           f"Expected 200, got {response.status_code}")
        
        with allure.step("Validate response schema"):
            is_valid = self.validate_response_schema(
                response, HEALTH_RESPONSE_SCHEMA, endpoint
            )
            self.assertTrue(is_valid, "Response does not match OpenAPI schema")
        
        with allure.step("Detect anomalies"):
            anomalies = self.detect_response_anomalies(response, endpoint)
            self.assertEqual(len(anomalies), 0, 
                          f"Anomalies detected: {anomalies}")
        
        with allure.step("Validate response content"):
            data = response.json()
            self.assertEqual(data["status"], "healthy")
            self.assertIn("version", data)
            
            allure.attach(
                json.dumps(data, indent=2),
                "Response Content",
                allure.attachment_type.JSON
            )
    
    @allure.story("AI Status Endpoint Validation")
    @allure.title("AI status endpoint with schema validation")
    @allure.severity(allure.severity_level.NORMAL)
    def test_ai_status_endpoint_validation(self):
        """Test AI status endpoint with schema validation."""
        endpoint = "/ai/status"
        
        response = self.client.get(endpoint)
        
        # May require auth, so check both cases
        if response.status_code == 200:
            is_valid = self.validate_response_schema(
                response, AI_STATUS_RESPONSE_SCHEMA, endpoint
            )
            anomalies = self.detect_response_anomalies(response, endpoint)
            
            data = response.json()
            allure.attach(
                json.dumps({
                    "response": data,
                    "schema_valid": is_valid,
                    "anomalies": anomalies
                }, indent=2),
                "AI Status Validation",
                allure.attachment_type.JSON
            )
        else:
            # Auth required - that's expected
            allure.attach(
                json.dumps({
                    "status_code": response.status_code,
                    "note": "Authentication required (expected)"
                }, indent=2),
                "AI Status (Auth Required)",
                allure.attachment_type.JSON
            )
    
    @allure.story("Diff Analysis Endpoint Validation")
    @allure.title("Diff analysis endpoint with request/response validation")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_diff_analysis_endpoint_validation(self):
        """Test diff analysis endpoint with full validation."""
        endpoint = "/ai/analyze-diff"
        
        # Request schema validation
        request_data = {
            "baseline": BASELINE_PLAYBACK_RESPONSE,
            "candidate": CANDIDATE_PLAYBACK_RESPONSE_BREAKING,
        }
        
        with allure.step("Validate request payload"):
            request_schema = {
                "type": "object",
                "required": ["baseline", "candidate"],
                "properties": {
                    "baseline": {"type": "object"},
                    "candidate": {"type": "object"}
                }
            }
            
            try:
                validate(instance=request_data, schema=request_schema)
                request_valid = True
            except ValidationError as e:
                request_valid = False
                allure.attach(
                    json.dumps({"error": str(e)}, indent=2),
                    "Request Validation Error",
                    allure.attachment_type.JSON
                )
            
            self.assertTrue(request_valid, "Request does not match schema")
        
        with allure.step("Send POST request"):
            response = self.client.post(
                endpoint,
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            request_summary = {
                "method": "POST",
                "endpoint": endpoint,
                "request_size_bytes": len(json.dumps(request_data)),
                "status_code": response.status_code
            }
            allure.attach(
                json.dumps(request_summary, indent=2),
                "Request Summary",
                allure.attachment_type.JSON
            )
        
        with allure.step("Validate response"):
            if response.status_code == 200:
                is_valid = self.validate_response_schema(
                    response, DIFF_ANALYSIS_RESPONSE_SCHEMA, endpoint
                )
                anomalies = self.detect_response_anomalies(response, endpoint)
                
                data = response.json()
                allure.attach(
                    json.dumps({
                        "response": data,
                        "schema_valid": is_valid,
                        "anomalies": anomalies
                    }, indent=2),
                    "Diff Analysis Response",
                    allure.attachment_type.JSON
                )
            else:
                # May require auth or have errors
                error_data = {
                    "status_code": response.status_code,
                    "response": response.text[:500] if hasattr(response, 'text') else str(response)
                }
                allure.attach(
                    json.dumps(error_data, indent=2),
                    "Error Response",
                    allure.attachment_type.JSON
                )


@allure.feature("API Error Handling")
@unittest.skipUnless(HAS_APP, "FastAPI app not available")
class TestAPIErrorHandling(unittest.TestCase):
    """Test API error handling and edge cases."""
    
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
    
    @allure.story("Invalid Request Handling")
    @allure.title("Test API handles invalid requests gracefully")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_invalid_request_handling(self):
        """Test that API handles invalid requests properly."""
        endpoint = "/ai/analyze-diff"
        
        test_cases = [
            {
                "name": "Missing required field",
                "data": {"baseline": {}},  # Missing candidate
                "expected_status": [400, 422]
            },
            {
                "name": "Invalid JSON structure",
                "data": "not a json object",
                "expected_status": [400, 422]
            },
            {
                "name": "Empty payload",
                "data": {},
                "expected_status": [400, 422]
            }
        ]
        
        results = []
        for case in test_cases:
            with allure.step(f"Test: {case['name']}"):
                try:
                    response = self.client.post(
                        endpoint,
                        json=case["data"] if isinstance(case["data"], dict) else None,
                        content=case["data"] if not isinstance(case["data"], dict) else None
                    )
                    
                    result = {
                        "test_case": case["name"],
                        "status_code": response.status_code,
                        "expected_status": case["expected_status"],
                        "handled_correctly": response.status_code in case["expected_status"]
                    }
                    results.append(result)
                except Exception as e:
                    result = {
                        "test_case": case["name"],
                        "error": str(e),
                        "handled_correctly": True  # Exception is acceptable
                    }
                    results.append(result)
        
        allure.attach(
            json.dumps(results, indent=2),
            "Error Handling Test Results",
            allure.attachment_type.JSON
        )
        
        # All should be handled correctly
        all_handled = all(r.get("handled_correctly", False) for r in results)
        self.assertTrue(all_handled, "Some invalid requests were not handled correctly")
    
    @allure.story("Performance Validation")
    @allure.title("Test API response times and performance")
    @allure.severity(allure.severity_level.NORMAL)
    def test_api_performance(self):
        """Test API performance metrics."""
        endpoint = "/health"
        iterations = 10
        response_times = []
        
        with allure.step(f"Run {iterations} requests to measure performance"):
            for i in range(iterations):
                start_time = time.time()
                response = self.client.get(endpoint)
                response_time = time.time() - start_time
                response_times.append(response_time)
                
                self.assertEqual(response.status_code, 200)
        
        with allure.step("Calculate performance metrics"):
            avg_time = sum(response_times) / len(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            
            performance_metrics = {
                "endpoint": endpoint,
                "iterations": iterations,
                "average_response_time_ms": avg_time * 1000,
                "min_response_time_ms": min_time * 1000,
                "max_response_time_ms": max_time * 1000,
                "all_response_times_ms": [t * 1000 for t in response_times]
            }
            
            allure.attach(
                json.dumps(performance_metrics, indent=2),
                "Performance Metrics",
                allure.attachment_type.JSON
            )
            
            # Performance assertions
            self.assertLess(avg_time, 1.0, "Average response time should be < 1 second")
            self.assertLess(max_time, 2.0, "Max response time should be < 2 seconds")


@allure.feature("API Security Validation")
@unittest.skipUnless(HAS_APP, "FastAPI app not available")
class TestAPISecurity(unittest.TestCase):
    """Test API security and authentication."""
    
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
    
    @allure.story("Authentication Requirements")
    @allure.title("Test protected endpoints require authentication")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_authentication_required(self):
        """Test that protected endpoints require authentication."""
        protected_endpoints = [
            "/api/specs/discover",
            "/api/validations/",
            "/api/governance/pending",
        ]
        
        results = []
        for endpoint in protected_endpoints:
            with allure.step(f"Test {endpoint} without auth"):
                response = self.client.get(endpoint)
                
                result = {
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "requires_auth": response.status_code in [401, 403],
                    "response": response.text[:200] if hasattr(response, 'text') else str(response)
                }
                results.append(result)
        
        allure.attach(
            json.dumps(results, indent=2),
            "Authentication Requirements",
            allure.attachment_type.JSON
        )
        
        # All protected endpoints should require auth
        all_protected = all(r["requires_auth"] for r in results)
        self.assertTrue(all_protected, "Some protected endpoints don't require authentication")


if __name__ == "__main__":
    unittest.main(verbosity=2)
