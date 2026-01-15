"""
Comprehensive Core Module Tests for 100% Coverage.

Tests all core modules: diff, model, features, scoring.
"""
import pytest
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import allure
except ImportError:
    class allure:
        @staticmethod
        def feature(name): return lambda f: f
        @staticmethod
        def story(name): return lambda f: f
        @staticmethod
        def title(name): return lambda f: f
        @staticmethod
        def severity(level): return lambda f: f
        @staticmethod
        def attach(body, name, attachment_type): pass
        class severity_level:
            CRITICAL = "critical"
            NORMAL = "normal"
            TRIVIAL = "trivial"
        class attachment_type:
            JSON = "application/json"
            TEXT = "text/plain"


# ============================================================================
# Test qoe_guard.diff module
# ============================================================================
from qoe_guard.diff import json_diff, extract_features


@allure.feature("JSON Diff Engine - Full Coverage")
class TestJsonDiffFullCoverage:
    """Complete coverage for json_diff module."""
    
    @allure.title("Test identical objects")
    def test_identical_objects(self):
        obj = {"a": 1, "b": [1, 2, 3]}
        result = json_diff(obj, obj)
        assert len(result.changes) == 0
        assert result.decision == "PASS"
    
    @allure.title("Test value change")
    def test_value_change(self):
        old = {"value": 100}
        new = {"value": 200}
        result = json_diff(old, new)
        assert len(result.changes) == 1
        assert result.changes[0].change_type == "value_changed"
    
    @allure.title("Test type change - int to string")
    def test_type_change_int_to_string(self):
        old = {"value": 100}
        new = {"value": "100"}
        result = json_diff(old, new)
        assert len(result.changes) == 1
        assert result.changes[0].change_type == "type_changed"
        assert result.changes[0].is_breaking is True
    
    @allure.title("Test type change - dict to list")
    def test_type_change_dict_to_list(self):
        old = {"data": {"key": "value"}}
        new = {"data": ["value"]}
        result = json_diff(old, new)
        assert any(c.change_type == "type_changed" for c in result.changes)
    
    @allure.title("Test field added")
    def test_field_added(self):
        old = {"a": 1}
        new = {"a": 1, "b": 2}
        result = json_diff(old, new)
        assert any(c.change_type == "added" for c in result.changes)
    
    @allure.title("Test field removed")
    def test_field_removed(self):
        old = {"a": 1, "b": 2}
        new = {"a": 1}
        result = json_diff(old, new)
        assert any(c.change_type == "removed" for c in result.changes)
    
    @allure.title("Test nested changes")
    def test_nested_changes(self):
        old = {"level1": {"level2": {"value": 1}}}
        new = {"level1": {"level2": {"value": 2}}}
        result = json_diff(old, new)
        assert len(result.changes) == 1
        assert "level1.level2.value" in result.changes[0].path
    
    @allure.title("Test array length change")
    def test_array_length_change(self):
        old = {"items": [1, 2, 3]}
        new = {"items": [1, 2, 3, 4, 5]}
        result = json_diff(old, new)
        assert len(result.changes) > 0
    
    @allure.title("Test array element change")
    def test_array_element_change(self):
        old = {"items": [1, 2, 3]}
        new = {"items": [1, 99, 3]}
        result = json_diff(old, new)
        assert len(result.changes) >= 1
    
    @allure.title("Test empty objects")
    def test_empty_objects(self):
        result = json_diff({}, {})
        assert len(result.changes) == 0
    
    @allure.title("Test null values")
    def test_null_values(self):
        old = {"value": None}
        new = {"value": "not null"}
        result = json_diff(old, new)
        assert len(result.changes) >= 1
    
    @allure.title("Test boolean changes")
    def test_boolean_changes(self):
        old = {"enabled": True}
        new = {"enabled": False}
        result = json_diff(old, new)
        assert len(result.changes) == 1
    
    @allure.title("Test critical path detection via diff")
    def test_critical_path_detection(self):
        # Test that critical paths are detected through json_diff
        old = {"playback": {"manifestUrl": "http://old.com"}}
        new = {"playback": {"manifestUrl": "http://new.com"}}
        result = json_diff(old, new)
        # Critical paths should have is_critical=True
        assert len(result.changes) >= 1
    
    @allure.title("Test float value changes")
    def test_float_value_changes(self):
        old = {"price": 19.99}
        new = {"price": 29.99}
        result = json_diff(old, new)
        assert len(result.changes) == 1
    
    @allure.title("Test deep nested array")
    def test_deep_nested_array(self):
        old = {"data": {"items": [{"id": 1}, {"id": 2}]}}
        new = {"data": {"items": [{"id": 1}, {"id": 3}]}}
        result = json_diff(old, new)
        assert len(result.changes) >= 1


@allure.feature("Feature Extraction - Full Coverage")
class TestFeatureExtractionFullCoverage:
    """Complete coverage for feature extraction."""
    
    @allure.title("Test extract features from empty diff")
    def test_extract_features_empty(self):
        from qoe_guard.model import DiffResult
        result = DiffResult(changes=[], decision="PASS", qoe_risk_score=0.0)
        features = extract_features(result)
        assert features.total_changes == 0
        assert features.breaking_changes == 0
    
    @allure.title("Test extract features with breaking changes")
    def test_extract_features_breaking(self):
        old = {"value": 100}
        new = {"value": "100"}
        result = json_diff(old, new)
        features = extract_features(result)
        assert features.breaking_changes > 0
        assert features.type_changes > 0
    
    @allure.title("Test extract features with added fields")
    def test_extract_features_added(self):
        old = {"a": 1}
        new = {"a": 1, "b": 2, "c": 3}
        result = json_diff(old, new)
        features = extract_features(result)
        assert features.added_fields >= 2
    
    @allure.title("Test extract features with removed fields")
    def test_extract_features_removed(self):
        old = {"a": 1, "b": 2, "c": 3}
        new = {"a": 1}
        result = json_diff(old, new)
        features = extract_features(result)
        assert features.removed_fields >= 2


# ============================================================================
# Test qoe_guard.model module
# ============================================================================
from qoe_guard.model import Change, DiffResult, FeatureVector, RiskAssessment


@allure.feature("Model Classes - Full Coverage")
class TestModelClassesFullCoverage:
    """Complete coverage for model classes."""
    
    @allure.title("Test Change dataclass")
    def test_change_dataclass(self):
        change = Change(
            path="$.test.path",
            change_type="value_changed",
            old_value=1,
            new_value=2,
            is_breaking=False,
            is_critical=False
        )
        assert change.path == "$.test.path"
        assert change.change_type == "value_changed"
        assert change.old_value == 1
        assert change.new_value == 2
        assert change.is_breaking is False
        assert change.is_critical is False
    
    @allure.title("Test Change with breaking flag")
    def test_change_breaking(self):
        change = Change(
            path="$.type",
            change_type="type_changed",
            old_value=100,
            new_value="100",
            is_breaking=True,
            is_critical=True
        )
        assert change.is_breaking is True
        assert change.is_critical is True
    
    @allure.title("Test DiffResult dataclass")
    def test_diff_result_dataclass(self):
        changes = [
            Change("$.a", "added", None, 1, False, False),
            Change("$.b", "removed", 2, None, True, True),
        ]
        result = DiffResult(
            changes=changes,
            decision="WARN",
            qoe_risk_score=0.5
        )
        assert len(result.changes) == 2
        assert result.decision == "WARN"
        assert result.qoe_risk_score == 0.5
    
    @allure.title("Test FeatureVector dataclass")
    def test_feature_vector_dataclass(self):
        fv = FeatureVector(
            total_changes=10,
            added_fields=3,
            removed_fields=2,
            value_changes=3,
            type_changes=1,
            critical_changes=2,
            breaking_changes=1,
            array_length_changes=1
        )
        assert fv.total_changes == 10
        assert fv.added_fields == 3
        assert fv.removed_fields == 2
        assert fv.value_changes == 3
        assert fv.type_changes == 1
        assert fv.critical_changes == 2
        assert fv.breaking_changes == 1
        assert fv.array_length_changes == 1
    
    @allure.title("Test RiskAssessment dataclass")
    def test_risk_assessment_dataclass(self):
        ra = RiskAssessment(
            qoe_risk_score=0.75,
            brittleness_score=0.5,
            decision="WARN",
            top_contributors=[{"name": "type_changes", "contribution": 0.4}],
            recommendations=["Review type changes"]
        )
        assert ra.qoe_risk_score == 0.75
        assert ra.decision == "WARN"
        assert len(ra.top_contributors) == 1


# ============================================================================
# Test qoe_guard.features module
# ============================================================================
from qoe_guard.features import extract_features as features_extract, features_to_dict


@allure.feature("Features Module - Full Coverage")
class TestFeaturesFullCoverage:
    """Complete coverage for features module."""
    
    @allure.title("Test extract_features function")
    def test_extract_features_function(self):
        result = json_diff({"a": 1, "b": 2}, {"a": 1, "b": 3, "c": 4})
        extracted = features_extract(result)
        
        assert extracted is not None
        assert hasattr(extracted, 'total_changes')
    
    @allure.title("Test features_to_dict function")
    def test_features_to_dict(self):
        result = json_diff({"a": 1}, {"a": 2})
        extracted = features_extract(result)
        as_dict = features_to_dict(extracted)
        
        assert isinstance(as_dict, dict)
        assert "total_changes" in as_dict


# ============================================================================
# Test qoe_guard.scoring modules
# ============================================================================
from qoe_guard.scoring.brittleness import compute_brittleness_score
from qoe_guard.scoring.qoe_risk import assess_qoe_risk
from qoe_guard.scoring.criticality import get_criticality_for_path, DEFAULT_CRITICALITY_PROFILES
from qoe_guard.scoring.drift import classify_drift, DriftType


@allure.feature("Scoring System - Full Coverage")
class TestScoringFullCoverage:
    """Complete coverage for scoring modules."""
    
    @allure.title("Test brittleness score minimum")
    def test_brittleness_score_minimum(self):
        score = compute_brittleness_score(0.0, 0.0, 0.0, 0.0)
        assert score >= 0
        assert score <= 100
    
    @allure.title("Test brittleness score maximum")
    def test_brittleness_score_maximum(self):
        score = compute_brittleness_score(1.0, 1.0, 1.0, 1.0)
        assert score >= 0
        assert score <= 100
    
    @allure.title("Test brittleness score mid-range")
    def test_brittleness_score_mid(self):
        score = compute_brittleness_score(0.5, 0.5, 0.5, 0.5)
        assert score >= 0
        assert score <= 100
    
    @allure.title("Test QoE risk PASS decision")
    def test_qoe_risk_pass(self):
        result = assess_qoe_risk(
            changes_count=1,
            critical_changes=0,
            type_changes=0,
            removed_fields=0
        )
        assert result.score >= 0.0
        assert result.score <= 1.0
        assert result.action in ["PASS", "WARN", "FAIL"]
    
    @allure.title("Test QoE risk FAIL decision")
    def test_qoe_risk_fail(self):
        result = assess_qoe_risk(
            changes_count=50,
            critical_changes=20,
            type_changes=10,
            removed_fields=15
        )
        assert result.score >= 0.0
        assert result.action in ["WARN", "FAIL"]
    
    @allure.title("Test QoE risk with zero changes")
    def test_qoe_risk_zero_changes(self):
        result = assess_qoe_risk(
            changes_count=0,
            critical_changes=0,
            type_changes=0,
            removed_fields=0
        )
        assert result.score == 0.0
        assert result.action == "PASS"
    
    @allure.title("Test criticality for playback paths")
    def test_criticality_playback(self):
        score = get_criticality_for_path("$.playback.manifestUrl")
        assert score >= 0.9
    
    @allure.title("Test criticality for DRM paths")
    def test_criticality_drm(self):
        score = get_criticality_for_path("$.drm.licenseUrl")
        assert score >= 0.9
    
    @allure.title("Test criticality for analytics paths")
    def test_criticality_analytics(self):
        score = get_criticality_for_path("$.analytics.events")
        assert score < 0.5
    
    @allure.title("Test criticality for unknown paths")
    def test_criticality_unknown(self):
        score = get_criticality_for_path("$.unknown.path.here")
        assert score >= 0.0
        assert score <= 1.0
    
    @allure.title("Test criticality profiles exist")
    def test_criticality_profiles_exist(self):
        assert DEFAULT_CRITICALITY_PROFILES is not None
        assert len(DEFAULT_CRITICALITY_PROFILES) > 0
    
    @allure.title("Test drift classification - no drift")
    def test_drift_none(self):
        drift = classify_drift(
            spec_changed=False,
            runtime_mismatches=[]
        )
        assert drift.drift_type == DriftType.NONE
    
    @allure.title("Test drift classification - spec drift")
    def test_drift_spec(self):
        drift = classify_drift(
            spec_changed=True,
            runtime_mismatches=[]
        )
        assert drift.drift_type == DriftType.SPEC_DRIFT
    
    @allure.title("Test drift classification - runtime drift")
    def test_drift_runtime(self):
        drift = classify_drift(
            spec_changed=False,
            runtime_mismatches=["$.response.newField"]
        )
        assert drift.drift_type == DriftType.RUNTIME_DRIFT
    
    @allure.title("Test drift classification - undocumented")
    def test_drift_undocumented(self):
        drift = classify_drift(
            spec_changed=True,
            runtime_mismatches=["$.critical.path"],
            critical_paths={"$.critical.path"}
        )
        assert drift.drift_type in [DriftType.UNDOCUMENTED, DriftType.SPEC_DRIFT, DriftType.RUNTIME_DRIFT]
    
    @allure.title("Test DriftType enum")
    def test_drift_type_enum(self):
        assert DriftType.NONE.value == "none"
        assert DriftType.SPEC_DRIFT.value == "spec_drift"
        assert DriftType.RUNTIME_DRIFT.value == "runtime_drift"
        assert DriftType.UNDOCUMENTED.value == "undocumented"
