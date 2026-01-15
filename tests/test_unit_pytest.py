"""
Unit Tests in Pure Pytest Style with Allure.

These tests use pytest fixtures and Allure annotations for better integration.
"""
import pytest
import json
import sys
import os

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
        def severity(level): return lambda f: f
        @staticmethod
        def attach(body, name, attachment_type): pass

from qoe_guard.diff import json_diff, extract_features
from qoe_guard.model import DiffResult, FeatureVector, Change
from qoe_guard.scoring.brittleness import compute_brittleness_score
from qoe_guard.scoring.qoe_risk import assess_qoe_risk
from qoe_guard.scoring.criticality import get_criticality_for_path
from qoe_guard.scoring.drift import classify_drift, DriftType
from tests.fixtures.sample_data import (
    BASELINE_PLAYBACK_RESPONSE,
    CANDIDATE_PLAYBACK_RESPONSE_BREAKING,
    CANDIDATE_PLAYBACK_RESPONSE_MINOR,
)


@allure.feature("JSON Diff Engine")
class TestJsonDiffPytest:
    """Pytest-style tests for JSON diff engine."""
    
    @allure.story("Basic Diff Operations")
    @allure.title("Identical JSON should produce no changes")
    @allure.severity(allure.severity_level.TRIVIAL)
    def test_identical_json_returns_no_changes(self):
        """Identical JSON objects should produce no changes."""
        obj = {"key": "value", "nested": {"a": 1}}
        result = json_diff(obj, obj)
        
        assert len(result.changes) == 0
        assert result.decision == "PASS"
        
        allure.attach(
            json.dumps({"changes_count": len(result.changes), "decision": result.decision}, indent=2),
            "Diff Result",
            allure.attachment_type.JSON
        )
    
    @allure.story("Value Change Detection")
    @allure.title("Value changes should be detected and classified")
    @allure.severity(allure.severity_level.NORMAL)
    def test_value_change_detected(self):
        """Value changes should be detected."""
        old = {"quality": "HD"}
        new = {"quality": "4K"}
        
        allure.attach(
            json.dumps({"baseline": old, "candidate": new}, indent=2),
            "Input JSON",
            allure.attachment_type.JSON
        )
        
        result = json_diff(old, new)
        
        assert len(result.changes) == 1
        assert result.changes[0].change_type == "value_changed"
        assert result.changes[0].path == "$.quality"
        
        change_details = {
            "path": result.changes[0].path,
            "type": result.changes[0].change_type,
            "old_value": result.changes[0].old_value,
            "new_value": result.changes[0].new_value,
        }
        allure.attach(
            json.dumps(change_details, indent=2),
            "Detected Change",
            allure.attachment_type.JSON
        )
    
    @allure.story("Breaking Change Detection")
    @allure.title("Type changes should be flagged as breaking")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_type_change_detected(self):
        """Type changes should be detected and flagged as critical."""
        old = {"value": 100}
        new = {"value": "100"}
        
        result = json_diff(old, new)
        
        assert len(result.changes) == 1
        assert result.changes[0].change_type == "type_changed"
        assert result.changes[0].is_breaking is True
        
        allure.attach(
            json.dumps({
                "change": {
                    "path": result.changes[0].path,
                    "type": result.changes[0].change_type,
                    "is_breaking": result.changes[0].is_breaking,
                },
                "decision": result.decision,
                "qoe_risk": result.qoe_risk_score
            }, indent=2),
            "Breaking Change Analysis",
            allure.attachment_type.JSON
        )


@allure.feature("Feature Extraction")
class TestFeatureExtractionPytest:
    """Pytest-style tests for feature extraction."""
    
    @allure.story("Feature Vector Generation")
    @allure.title("Empty changes should produce zero features")
    @allure.severity(allure.severity_level.TRIVIAL)
    def test_empty_changes_produce_zero_features(self):
        """No changes should produce zero/low features."""
        result = DiffResult(changes=[], decision="PASS", qoe_risk_score=0.0)
        features = extract_features(result)
        
        assert isinstance(features, FeatureVector)
        assert features.total_changes == 0
        
        allure.attach(
            json.dumps({
                "total_changes": features.total_changes,
                "added_fields": features.added_fields,
                "removed_fields": features.removed_fields,
            }, indent=2),
            "Feature Vector",
            allure.attachment_type.JSON
        )


@allure.feature("Scoring System")
class TestScoringPytest:
    """Pytest-style tests for scoring algorithms."""
    
    @allure.story("Brittleness Scoring")
    @allure.title("Brittleness score should be within bounds")
    @allure.severity(allure.severity_level.NORMAL)
    def test_brittleness_score_bounds(self):
        """Brittleness score should be between 0 and 100."""
        score = compute_brittleness_score(
            contract_complexity=0.3,
            change_sensitivity=0.5,
            runtime_fragility=0.2,
            blast_radius=0.4
        )
        
        assert score >= 0
        assert score <= 100
        
        allure.attach(
            json.dumps({"brittleness_score": score}, indent=2),
            "Brittleness Score",
            allure.attachment_type.JSON
        )
    
    @allure.story("QoE Risk Scoring")
    @allure.title("QoE risk score should be within bounds")
    @allure.severity(allure.severity_level.NORMAL)
    def test_qoe_risk_bounds(self):
        """QoE risk score should be between 0 and 1."""
        result = assess_qoe_risk(
            changes_count=5,
            critical_changes=2,
            type_changes=1,
            removed_fields=1
        )
        
        assert result.score >= 0.0
        assert result.score <= 1.0
        assert result.action in ["PASS", "WARN", "FAIL"]
        
        allure.attach(
            json.dumps({
                "qoe_risk_score": result.score,
                "decision": result.action,
                "top_signals": [{"signal": s[0], "contribution": s[1]} for s in result.top_signals]
            }, indent=2),
            "QoE Risk Assessment",
            allure.attachment_type.JSON
        )


@allure.feature("Real-World Scenarios")
class TestRealWorldScenariosPytest:
    """Pytest-style tests for real-world scenarios."""
    
    @allure.story("Minor Changes Scenario")
    @allure.title("Minor changes should result in PASS decision")
    @allure.severity(allure.severity_level.NORMAL)
    def test_minor_changes_scenario(self):
        """Test minor changes scenario from sample data."""
        baseline = BASELINE_PLAYBACK_RESPONSE
        candidate = CANDIDATE_PLAYBACK_RESPONSE_MINOR
        
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
        
        result = json_diff(baseline, candidate)
        features = extract_features(result)
        
        assert result.decision in ["PASS", "WARN"]
        assert result.qoe_risk_score < 0.72  # Should not be FAIL
        
        summary = {
            "decision": result.decision,
            "qoe_risk_score": result.qoe_risk_score,
            "total_changes": len(result.changes),
            "critical_changes": features.critical_changes,
        }
        allure.attach(
            json.dumps(summary, indent=2),
            "Analysis Summary",
            allure.attachment_type.JSON
        )
    
    @allure.story("Breaking Changes Scenario")
    @allure.title("Breaking changes should result in FAIL decision")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_breaking_changes_scenario(self):
        """Test breaking changes scenario from sample data."""
        baseline = BASELINE_PLAYBACK_RESPONSE
        candidate = CANDIDATE_PLAYBACK_RESPONSE_BREAKING
        
        result = json_diff(baseline, candidate)
        features = extract_features(result)
        
        assert result.decision in ["WARN", "FAIL"]
        assert features.breaking_changes > 0
        
        summary = {
            "decision": result.decision,
            "qoe_risk_score": result.qoe_risk_score,
            "breaking_changes": features.breaking_changes,
            "type_changes": features.type_changes,
        }
        allure.attach(
            json.dumps(summary, indent=2),
            "Breaking Changes Analysis",
            allure.attachment_type.JSON
        )


@allure.feature("Criticality Analysis")
class TestCriticalityPytest:
    """Pytest-style tests for criticality analysis."""
    
    @allure.story("Path Criticality Scoring")
    @allure.title("Calculate criticality scores for JSON paths")
    @allure.severity(allure.severity_level.NORMAL)
    def test_path_criticality_scoring(self):
        """Test criticality scoring for different JSON paths."""
        playback_score = get_criticality_for_path("$.playback.manifestUrl")
        analytics_score = get_criticality_for_path("$.analytics.events")
        
        assert playback_score > 0.8
        assert analytics_score < 0.5
        
        results = [
            {"path": "$.playback.manifestUrl", "score": playback_score},
            {"path": "$.analytics.events", "score": analytics_score},
        ]
        allure.attach(
            json.dumps(results, indent=2),
            "Criticality Scores",
            allure.attachment_type.JSON
        )


@allure.feature("Drift Classification")
class TestDriftClassificationPytest:
    """Pytest-style tests for drift classification."""
    
    @allure.story("Drift Detection")
    @allure.title("Classify different types of drift")
    @allure.severity(allure.severity_level.NORMAL)
    def test_drift_classification(self):
        """Test drift classification logic."""
        # Test no drift
        drift_none = classify_drift(
            spec_changed=False,
            runtime_mismatches=[]
        )
        assert drift_none.drift_type == DriftType.NONE
        
        # Test spec drift
        drift_spec = classify_drift(
            spec_changed=True,
            runtime_mismatches=[]
        )
        assert drift_spec.drift_type == DriftType.SPEC_DRIFT
        
        # Test runtime drift
        drift_runtime = classify_drift(
            spec_changed=False,
            runtime_mismatches=["$.response.newField"]
        )
        assert drift_runtime.drift_type == DriftType.RUNTIME_DRIFT
        
        results = [
            {"type": "none", "drift_type": drift_none.drift_type.value},
            {"type": "spec", "drift_type": drift_spec.drift_type.value},
            {"type": "runtime", "drift_type": drift_runtime.drift_type.value},
        ]
        allure.attach(
            json.dumps(results, indent=2),
            "Drift Classification Results",
            allure.attachment_type.JSON
        )
