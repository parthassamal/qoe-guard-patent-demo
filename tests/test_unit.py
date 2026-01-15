"""
Unit Tests for QoE-Guard Core Modules.

Tests cover:
- JSON diff engine
- Feature extraction
- Scoring algorithms
- Model classes
"""
import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qoe_guard.diff import json_diff, extract_features
from qoe_guard.model import DiffResult, FeatureVector, RiskAssessment


class TestJsonDiff(unittest.TestCase):
    """Test cases for JSON diff engine."""
    
    def test_identical_json_returns_no_changes(self):
        """Identical JSON objects should produce no changes."""
        obj = {"key": "value", "nested": {"a": 1}}
        result = json_diff(obj, obj)
        self.assertEqual(len(result.changes), 0)
        self.assertEqual(result.decision, "PASS")
    
    def test_value_change_detected(self):
        """Value changes should be detected."""
        old = {"quality": "HD"}
        new = {"quality": "4K"}
        result = json_diff(old, new)
        self.assertEqual(len(result.changes), 1)
        self.assertEqual(result.changes[0].change_type, "value_changed")
        self.assertEqual(result.changes[0].path, "$.quality")
    
    def test_field_added_detected(self):
        """Added fields should be detected."""
        old = {"a": 1}
        new = {"a": 1, "b": 2}
        result = json_diff(old, new)
        self.assertEqual(len(result.changes), 1)
        self.assertEqual(result.changes[0].change_type, "added")
        self.assertEqual(result.changes[0].path, "$.b")
    
    def test_field_removed_detected(self):
        """Removed fields should be detected."""
        old = {"a": 1, "b": 2}
        new = {"a": 1}
        result = json_diff(old, new)
        self.assertEqual(len(result.changes), 1)
        self.assertEqual(result.changes[0].change_type, "removed")
        self.assertEqual(result.changes[0].path, "$.b")
    
    def test_type_change_detected(self):
        """Type changes should be detected and flagged as critical."""
        old = {"value": 100}
        new = {"value": "100"}
        result = json_diff(old, new)
        self.assertEqual(len(result.changes), 1)
        self.assertEqual(result.changes[0].change_type, "type_changed")
        self.assertTrue(result.changes[0].is_breaking)
    
    def test_nested_changes_detected(self):
        """Changes in nested objects should be detected with full path."""
        old = {"level1": {"level2": {"value": 1}}}
        new = {"level1": {"level2": {"value": 2}}}
        result = json_diff(old, new)
        self.assertEqual(len(result.changes), 1)
        self.assertEqual(result.changes[0].path, "$.level1.level2.value")
    
    def test_array_item_added(self):
        """Added array items should be detected."""
        old = {"items": [1, 2]}
        new = {"items": [1, 2, 3]}
        result = json_diff(old, new)
        changes = [c for c in result.changes if c.change_type == "added"]
        self.assertGreater(len(changes), 0)
    
    def test_array_item_removed(self):
        """Removed array items should be detected."""
        old = {"items": [1, 2, 3]}
        new = {"items": [1, 2]}
        result = json_diff(old, new)
        changes = [c for c in result.changes if c.change_type == "removed"]
        self.assertGreater(len(changes), 0)
    
    def test_empty_objects(self):
        """Empty objects should diff correctly."""
        result = json_diff({}, {})
        self.assertEqual(len(result.changes), 0)
        
        result = json_diff({}, {"new": "field"})
        self.assertEqual(len(result.changes), 1)
    
    def test_null_handling(self):
        """Null values should be handled correctly."""
        old = {"value": None}
        new = {"value": "not_null"}
        result = json_diff(old, new)
        self.assertEqual(len(result.changes), 1)


class TestFeatureExtraction(unittest.TestCase):
    """Test cases for feature extraction."""
    
    def test_empty_changes_produce_zero_features(self):
        """No changes should produce zero/low features."""
        result = DiffResult(changes=[], decision="PASS", qoe_risk_score=0.0)
        features = extract_features(result)
        self.assertIsInstance(features, FeatureVector)
        self.assertEqual(features.total_changes, 0)
    
    def test_critical_changes_counted(self):
        """Critical changes should be counted in features."""
        from qoe_guard.model import Change
        changes = [
            Change(path="$.drm.licenseUrl", change_type="removed", is_breaking=True, is_critical=True),
            Change(path="$.playback.url", change_type="value_changed", is_breaking=False, is_critical=True),
        ]
        result = DiffResult(changes=changes, decision="WARN", qoe_risk_score=0.6)
        features = extract_features(result)
        self.assertEqual(features.critical_changes, 2)
    
    def test_type_changes_flagged(self):
        """Type changes should be counted separately."""
        from qoe_guard.model import Change
        changes = [
            Change(path="$.value", change_type="type_changed", old_type="integer", new_type="string", is_breaking=True),
        ]
        result = DiffResult(changes=changes, decision="FAIL", qoe_risk_score=0.8)
        features = extract_features(result)
        self.assertEqual(features.type_changes, 1)


class TestRiskAssessment(unittest.TestCase):
    """Test cases for risk assessment model."""
    
    def test_low_risk_assessment(self):
        """Low risk should produce PASS decision."""
        assessment = RiskAssessment(
            qoe_risk_score=0.2,
            brittleness_score=30,
            decision="PASS"
        )
        self.assertEqual(assessment.decision, "PASS")
        self.assertLess(assessment.qoe_risk_score, 0.45)
    
    def test_high_risk_assessment(self):
        """High risk should produce FAIL decision."""
        assessment = RiskAssessment(
            qoe_risk_score=0.85,
            brittleness_score=80,
            decision="FAIL"
        )
        self.assertEqual(assessment.decision, "FAIL")
        self.assertGreater(assessment.qoe_risk_score, 0.72)
    
    def test_medium_risk_assessment(self):
        """Medium risk should produce WARN decision."""
        assessment = RiskAssessment(
            qoe_risk_score=0.55,
            brittleness_score=60,
            decision="WARN"
        )
        self.assertEqual(assessment.decision, "WARN")


class TestScoringLogic(unittest.TestCase):
    """Test scoring calculation logic."""
    
    def test_brittleness_score_bounds(self):
        """Brittleness score should be between 0 and 100."""
        from qoe_guard.scoring.brittleness import compute_brittleness_score
        
        # Mock minimal inputs
        score = compute_brittleness_score(
            contract_complexity=0.3,
            change_sensitivity=0.5,
            runtime_fragility=0.2,
            blast_radius=0.4
        )
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
    
    def test_qoe_risk_bounds(self):
        """QoE risk score should be between 0 and 1."""
        from qoe_guard.scoring.qoe_risk import compute_qoe_risk
        
        score = compute_qoe_risk(
            changes_count=5,
            critical_changes=2,
            type_changes=1,
            removed_fields=1
        )
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1)


class TestCriticalityProfiles(unittest.TestCase):
    """Test criticality profile logic."""
    
    def test_playback_is_critical(self):
        """Playback-related paths should have high criticality."""
        from qoe_guard.scoring.criticality import get_criticality_for_path
        
        score = get_criticality_for_path("$.playback.manifestUrl")
        self.assertGreater(score, 0.8)
    
    def test_analytics_is_low_criticality(self):
        """Analytics paths should have low criticality."""
        from qoe_guard.scoring.criticality import get_criticality_for_path
        
        score = get_criticality_for_path("$.analytics.events")
        self.assertLess(score, 0.5)
    
    def test_drm_is_critical(self):
        """DRM-related paths should have high criticality."""
        from qoe_guard.scoring.criticality import get_criticality_for_path
        
        score = get_criticality_for_path("$.drm.licenseUrl")
        self.assertGreater(score, 0.9)


class TestDriftClassification(unittest.TestCase):
    """Test drift classification logic."""
    
    def test_no_drift_when_specs_match(self):
        """No drift when specs match and no runtime mismatches."""
        from qoe_guard.scoring.drift import classify_drift, DriftType
        
        result = classify_drift(
            spec_changed=False,
            runtime_mismatches=[]
        )
        self.assertEqual(result.drift_type, DriftType.NONE)
    
    def test_spec_drift_detected(self):
        """Spec drift when spec changed."""
        from qoe_guard.scoring.drift import classify_drift, DriftType
        
        result = classify_drift(
            spec_changed=True,
            runtime_mismatches=[]
        )
        self.assertEqual(result.drift_type, DriftType.SPEC_DRIFT)
    
    def test_runtime_drift_detected(self):
        """Runtime drift when implementation differs from spec."""
        from qoe_guard.scoring.drift import classify_drift, DriftType
        
        result = classify_drift(
            spec_changed=False,
            runtime_mismatches=["$.response.newField"]
        )
        self.assertEqual(result.drift_type, DriftType.RUNTIME_DRIFT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
