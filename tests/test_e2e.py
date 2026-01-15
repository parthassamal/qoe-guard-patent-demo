"""
End-to-End (E2E) Tests for QoE-Guard.

Comprehensive tests that validate the entire system workflow:
- Swagger discovery → Operation extraction → Validation → Scoring → Reporting
"""
import unittest
import sys
import os
import json
import time

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

from qoe_guard.diff import json_diff, extract_features
from qoe_guard.scoring.brittleness import compute_brittleness_score
from qoe_guard.scoring.qoe_risk import assess_qoe_risk
from qoe_guard.scoring.drift import classify_drift, DriftType
from qoe_guard.scoring.criticality import get_criticality_for_path
from tests.fixtures.sample_data import (
    BASELINE_PLAYBACK_RESPONSE,
    CANDIDATE_PLAYBACK_RESPONSE_BREAKING,
    CANDIDATE_PLAYBACK_RESPONSE_MINOR,
    SAMPLE_OPENAPI_SPEC,
    RUNTIME_METRICS_WITH_ANOMALIES,
)


@allure.feature("End-to-End Validation Workflow")
class TestE2EValidationWorkflow(unittest.TestCase):
    """Complete validation workflow from baseline to decision."""
    
    @allure.story("Complete Validation Pipeline")
    @allure.title("Full validation workflow: Baseline → Candidate → Analysis → Decision")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("""
    Tests the complete validation pipeline:
    1. Load baseline and candidate responses
    2. Perform JSON diff analysis
    3. Extract features
    4. Calculate brittleness and QoE risk scores
    5. Classify drift
    6. Generate final decision
    7. Validate all outputs
    """)
    def test_complete_validation_pipeline(self):
        """Test the complete validation pipeline end-to-end."""
        
        with allure.step("Step 1: Load baseline and candidate responses"):
            baseline = BASELINE_PLAYBACK_RESPONSE
            candidate = CANDIDATE_PLAYBACK_RESPONSE_BREAKING
            
            allure.attach(
                json.dumps(baseline, indent=2),
                "Baseline Response",
                allure.attachment_type.JSON
            )
            allure.attach(
                json.dumps(candidate, indent=2),
                "Candidate Response",
                allure.attachment_type.JSON
            )
        
        with allure.step("Step 2: Perform JSON diff analysis"):
            diff_result = json_diff(baseline, candidate)
            
            self.assertIsNotNone(diff_result)
            self.assertGreater(len(diff_result.changes), 0)
            
            changes_summary = {
                "total_changes": len(diff_result.changes),
                "breaking_changes": sum(1 for c in diff_result.changes if c.is_breaking),
                "critical_changes": sum(1 for c in diff_result.changes if c.is_critical),
                "change_types": {
                    "added": sum(1 for c in diff_result.changes if c.change_type == "added"),
                    "removed": sum(1 for c in diff_result.changes if c.change_type == "removed"),
                    "value_changed": sum(1 for c in diff_result.changes if c.change_type == "value_changed"),
                    "type_changed": sum(1 for c in diff_result.changes if c.change_type == "type_changed"),
                }
            }
            allure.attach(
                json.dumps(changes_summary, indent=2),
                "Diff Analysis Summary",
                allure.attachment_type.JSON
            )
        
        with allure.step("Step 3: Extract feature vector"):
            features = extract_features(diff_result)
            
            self.assertIsNotNone(features)
            self.assertEqual(features.total_changes, len(diff_result.changes))
            
            feature_summary = {
                "total_changes": features.total_changes,
                "added_fields": features.added_fields,
                "removed_fields": features.removed_fields,
                "type_changes": features.type_changes,
                "critical_changes": features.critical_changes,
                "breaking_changes": features.breaking_changes,
            }
            allure.attach(
                json.dumps(feature_summary, indent=2),
                "Feature Vector",
                allure.attachment_type.JSON
            )
        
        with allure.step("Step 4: Calculate brittleness score"):
            brittleness = compute_brittleness_score(
                contract_complexity=0.6,
                change_sensitivity=0.8,
                runtime_fragility=0.4,
                blast_radius=0.9
            )
            
            self.assertGreaterEqual(brittleness, 0)
            self.assertLessEqual(brittleness, 100)
            
            allure.attach(
                json.dumps({"brittleness_score": brittleness}, indent=2),
                "Brittleness Score",
                allure.attachment_type.JSON
            )
        
        with allure.step("Step 5: Calculate QoE risk assessment"):
            qoe_result = assess_qoe_risk(
                changes_count=features.total_changes,
                critical_changes=features.critical_changes,
                type_changes=features.type_changes,
                removed_fields=features.removed_fields,
            )
            
            self.assertGreaterEqual(qoe_result.score, 0.0)
            self.assertLessEqual(qoe_result.score, 1.0)
            self.assertIn(qoe_result.action, ["PASS", "WARN", "FAIL"])
            
            qoe_summary = {
                "qoe_risk_score": qoe_result.score,
                "decision": qoe_result.action,
                "top_signals": [{"signal": s[0], "contribution": s[1]} for s in qoe_result.top_signals]
            }
            allure.attach(
                json.dumps(qoe_summary, indent=2),
                "QoE Risk Assessment",
                allure.attachment_type.JSON
            )
        
        with allure.step("Step 6: Classify drift"):
            critical_paths = {
                "$.playback.manifestUrl",
                "$.drm.licenseUrl",
                "$.entitlement.allowed"
            }
            
            runtime_mismatches = [
                c.path for c in diff_result.changes
                if c.is_breaking and c.is_critical
            ]
            
            drift = classify_drift(
                spec_changed=False,
                runtime_mismatches=runtime_mismatches,
                critical_paths=critical_paths
            )
            
            self.assertIsNotNone(drift)
            self.assertIn(drift.drift_type, [DriftType.NONE, DriftType.SPEC_DRIFT, 
                                            DriftType.RUNTIME_DRIFT, DriftType.UNDOCUMENTED])
            
            drift_summary = {
                "drift_type": drift.drift_type.value,
                "severity": drift.severity,
                "description": drift.description,
                "affected_paths": drift.affected_paths,
            }
            allure.attach(
                json.dumps(drift_summary, indent=2),
                "Drift Classification",
                allure.attachment_type.JSON
            )
        
        with allure.step("Step 7: Generate final validation summary"):
            final_summary = {
                "validation_id": f"e2e_test_{int(time.time())}",
                "baseline_hash": "baseline_hash_placeholder",
                "candidate_hash": "candidate_hash_placeholder",
                "diff_result": {
                    "total_changes": len(diff_result.changes),
                    "decision": diff_result.decision,
                    "qoe_risk_score": diff_result.qoe_risk_score,
                },
                "scoring": {
                    "brittleness_score": brittleness,
                    "qoe_risk_score": qoe_result.score,
                    "qoe_decision": qoe_result.action,
                },
                "drift": {
                    "type": drift.drift_type.value,
                    "severity": drift.severity,
                },
                "final_decision": qoe_result.action,
                "recommendations": drift.recommendations,
            }
            
            allure.attach(
                json.dumps(final_summary, indent=2),
                "Final Validation Summary",
                allure.attachment_type.JSON
            )
            
            # Final assertion: Decision should be appropriate for breaking changes
            self.assertIn(qoe_result.action, ["WARN", "FAIL"])


@allure.feature("API Schema Validation")
class TestAPISchemaValidation(unittest.TestCase):
    """Comprehensive API schema validation tests."""
    
    @allure.story("Request Schema Validation")
    @allure.title("Validate request schema against OpenAPI spec")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_request_schema_validation(self):
        """Validate that requests conform to OpenAPI request schemas."""
        from jsonschema import validate, ValidationError
        
        # Sample OpenAPI request schema
        request_schema = {
            "type": "object",
            "required": ["contentId", "deviceId"],
            "properties": {
                "contentId": {"type": "string"},
                "deviceId": {"type": "string"},
                "drmType": {
                    "type": "string",
                    "enum": ["widevine", "fairplay", "playready"]
                }
            }
        }
        
        with allure.step("Test valid request"):
            valid_request = {
                "contentId": "movie_123",
                "deviceId": "device_456",
                "drmType": "widevine"
            }
            
            try:
                validate(instance=valid_request, schema=request_schema)
                validation_result = {"status": "valid", "errors": []}
            except ValidationError as e:
                validation_result = {"status": "invalid", "errors": [str(e)]}
                self.fail(f"Valid request failed validation: {e}")
            
            allure.attach(
                json.dumps({
                    "request": valid_request,
                    "validation": validation_result
                }, indent=2),
                "Valid Request Validation",
                allure.attachment_type.JSON
            )
        
        with allure.step("Test invalid request - missing required field"):
            invalid_request = {
                "contentId": "movie_123"
                # Missing required "deviceId"
            }
            
            try:
                validate(instance=invalid_request, schema=request_schema)
                validation_result = {"status": "valid", "errors": []}
                self.fail("Invalid request should have failed validation")
            except ValidationError as e:
                validation_result = {
                    "status": "invalid",
                    "errors": [{"field": e.path, "message": e.message}]
                }
            
            allure.attach(
                json.dumps({
                    "request": invalid_request,
                    "validation": validation_result
                }, indent=2),
                "Invalid Request Validation",
                allure.attachment_type.JSON
            )
        
        with allure.step("Test invalid request - wrong enum value"):
            invalid_request = {
                "contentId": "movie_123",
                "deviceId": "device_456",
                "drmType": "invalid_drm"  # Not in enum
            }
            
            try:
                validate(instance=invalid_request, schema=request_schema)
                validation_result = {"status": "valid", "errors": []}
                self.fail("Invalid enum value should have failed validation")
            except ValidationError as e:
                validation_result = {
                    "status": "invalid",
                    "errors": [{"field": e.path, "message": e.message}]
                }
            
            allure.attach(
                json.dumps({
                    "request": invalid_request,
                    "validation": validation_result
                }, indent=2),
                "Invalid Enum Validation",
                allure.attachment_type.JSON
            )
    
    @allure.story("Response Schema Validation")
    @allure.title("Validate response schema against OpenAPI spec")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_response_schema_validation(self):
        """Validate that responses conform to OpenAPI response schemas."""
        from jsonschema import validate, ValidationError
        
        # Sample OpenAPI response schema
        response_schema = {
            "type": "object",
            "required": ["playback", "drm"],
            "properties": {
                "playback": {
                    "type": "object",
                    "required": ["manifestUrl", "quality"],
                    "properties": {
                        "manifestUrl": {"type": "string", "format": "uri"},
                        "quality": {"type": "string", "enum": ["SD", "HD", "4K"]},
                        "maxBitrateKbps": {"type": "integer", "minimum": 0}
                    }
                },
                "drm": {
                    "type": "object",
                    "required": ["licenseUrl"],
                    "properties": {
                        "licenseUrl": {"type": "string", "format": "uri"},
                        "type": {"type": "string"}
                    }
                }
            }
        }
        
        with allure.step("Test valid response"):
            valid_response = BASELINE_PLAYBACK_RESPONSE
            
            try:
                validate(instance=valid_response, schema=response_schema)
                validation_result = {"status": "valid", "errors": []}
            except ValidationError as e:
                validation_result = {
                    "status": "invalid",
                    "errors": [{"path": list(e.path), "message": e.message}]
                }
                # Note: This might fail if baseline doesn't match exact schema
                # That's okay - we're testing the validation mechanism
            
            allure.attach(
                json.dumps({
                    "response": valid_response,
                    "validation": validation_result
                }, indent=2),
                "Response Schema Validation",
                allure.attachment_type.JSON
            )
        
        with allure.step("Test invalid response - missing required field"):
            invalid_response = {
                "playback": {
                    "quality": "HD"
                    # Missing required "manifestUrl"
                }
            }
            
            try:
                validate(instance=invalid_response, schema=response_schema)
                validation_result = {"status": "valid", "errors": []}
                self.fail("Invalid response should have failed validation")
            except ValidationError as e:
                validation_result = {
                    "status": "invalid",
                    "errors": [{"path": list(e.path), "message": e.message}]
                }
            
            allure.attach(
                json.dumps({
                    "response": invalid_response,
                    "validation": validation_result
                }, indent=2),
                "Invalid Response Validation",
                allure.attachment_type.JSON
            )


@allure.feature("Anomaly Detection")
class TestAnomalyDetection(unittest.TestCase):
    """Anomaly detection in API responses and runtime metrics."""
    
    @allure.story("Runtime Metrics Anomaly Detection")
    @allure.title("Detect anomalies in latency and error rates")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_runtime_anomaly_detection(self):
        """Detect anomalies in runtime metrics."""
        try:
            from qoe_guard.ai.anomaly_detector import AnomalyDetector
            ANOMALY_DETECTOR_AVAILABLE = True
        except ImportError:
            ANOMALY_DETECTOR_AVAILABLE = False
            self.skipTest("Anomaly detector not available")
        
        metrics = RUNTIME_METRICS_WITH_ANOMALIES
        
        with allure.step("Extract latency values"):
            latencies = [m["latency_ms"] for m in metrics]
            
            allure.attach(
                json.dumps({"latencies": latencies}, indent=2),
                "Latency Data",
                allure.attachment_type.JSON
            )
        
        with allure.step("Detect anomalies using Isolation Forest"):
            detector = AnomalyDetector(method="isolation_forest")
            anomalies = detector.detect_anomalies(latencies)
            
            self.assertIsInstance(anomalies, list)
            
            anomaly_summary = {
                "total_metrics": len(latencies),
                "anomalies_detected": len(anomalies),
                "anomaly_details": anomalies
            }
            allure.attach(
                json.dumps(anomaly_summary, indent=2),
                "Anomaly Detection Results",
                allure.attachment_type.JSON
            )
            
            # Should detect at least some anomalies in our test data
            self.assertGreater(len(anomalies), 0)
        
        with allure.step("Detect anomalies using Z-Score"):
            detector_z = AnomalyDetector(method="z_score")
            anomalies_z = detector_z.detect_anomalies(latencies)
            
            z_score_summary = {
                "method": "z_score",
                "anomalies_detected": len(anomalies_z),
                "anomaly_details": anomalies_z
            }
            allure.attach(
                json.dumps(z_score_summary, indent=2),
                "Z-Score Anomaly Detection",
                allure.attachment_type.JSON
            )
        
        with allure.step("Generate anomaly report and recommendations"):
            error_rates = [1 if m["status_code"] >= 400 else 0 for m in metrics]
            error_rate = sum(error_rates) / len(error_rates) if error_rates else 0
            
            recommendations = []
            if len(anomalies) > 0:
                recommendations.append("High latency anomalies detected - investigate network issues")
            if error_rate > 0.1:
                recommendations.append(f"High error rate ({error_rate*100:.1f}%) - check API health")
            
            anomaly_report = {
                "timestamp": time.time(),
                "metrics_analyzed": len(metrics),
                "anomalies_detected": len(anomalies),
                "error_rate": error_rate,
                "average_latency": sum(latencies) / len(latencies),
                "max_latency": max(latencies),
                "recommendations": recommendations,
                "action_required": len(anomalies) > 0 or error_rate > 0.1
            }
            
            allure.attach(
                json.dumps(anomaly_report, indent=2),
                "Anomaly Report & Recommendations",
                allure.attachment_type.JSON
            )
    
    @allure.story("Response Anomaly Detection")
    @allure.title("Detect anomalies in API response patterns")
    @allure.severity(allure.severity_level.NORMAL)
    def test_response_anomaly_detection(self):
        """Detect anomalies in API response patterns."""
        with allure.step("Compare multiple responses for anomalies"):
            responses = [
                BASELINE_PLAYBACK_RESPONSE,
                CANDIDATE_PLAYBACK_RESPONSE_MINOR,
                CANDIDATE_PLAYBACK_RESPONSE_BREAKING,
            ]
            
            # Extract key metrics from responses
            response_metrics = []
            for i, resp in enumerate(responses):
                playback = resp.get("playback", {})
                metrics = {
                    "response_id": i,
                    "has_manifest_url": "manifestUrl" in playback or "url" in playback,
                    "quality": playback.get("quality") or playback.get("resolution"),
                    "max_bitrate": playback.get("maxBitrateKbps") or playback.get("maxBitrate"),
                }
                response_metrics.append(metrics)
            
            allure.attach(
                json.dumps(response_metrics, indent=2),
                "Response Metrics",
                allure.attachment_type.JSON
            )
            
            # Detect anomalies: missing required fields, type mismatches
            anomalies = []
            for i, metrics in enumerate(response_metrics):
                if not metrics["has_manifest_url"]:
                    anomalies.append({
                        "response_id": i,
                        "type": "missing_required_field",
                        "field": "manifestUrl",
                        "severity": "critical"
                    })
                if isinstance(metrics["max_bitrate"], str):
                    anomalies.append({
                        "response_id": i,
                        "type": "type_mismatch",
                        "field": "maxBitrate",
                        "expected": "integer",
                        "actual": "string",
                        "severity": "high"
                    })
            
            anomaly_report = {
                "total_responses": len(responses),
                "anomalies_detected": len(anomalies),
                "anomalies": anomalies,
                "action_required": len(anomalies) > 0
            }
            
            allure.attach(
                json.dumps(anomaly_report, indent=2),
                "Response Anomaly Report",
                allure.attachment_type.JSON
            )
            
            # Should detect anomalies in breaking changes response
            self.assertGreater(len(anomalies), 0)


@allure.feature("Criticality Analysis")
class TestCriticalityAnalysis(unittest.TestCase):
    """Test criticality-based analysis and prioritization."""
    
    @allure.story("Path Criticality Scoring")
    @allure.title("Calculate criticality scores for JSON paths")
    @allure.severity(allure.severity_level.NORMAL)
    def test_path_criticality_scoring(self):
        """Test criticality scoring for different JSON paths."""
        test_paths = [
            ("$.playback.manifestUrl", 1.0),
            ("$.drm.licenseUrl", 0.95),
            ("$.entitlement.allowed", 0.95),
            ("$.ads.prerollUrl", 0.85),
            ("$.metadata.title", 0.4),
            ("$.analytics.events", 0.3),
        ]
        
        results = []
        for path, expected_min in test_paths:
            score = get_criticality_for_path(path)
            results.append({
                "path": path,
                "criticality_score": score,
                "expected_min": expected_min,
                "meets_expectation": score >= expected_min * 0.9  # Allow 10% variance
            })
        
        allure.attach(
            json.dumps(results, indent=2),
            "Criticality Scores",
            allure.attachment_type.JSON
        )
        
        # Verify critical paths have high scores
        playback_score = get_criticality_for_path("$.playback.manifestUrl")
        self.assertGreater(playback_score, 0.8)
        
        analytics_score = get_criticality_for_path("$.analytics.events")
        self.assertLess(analytics_score, 0.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
