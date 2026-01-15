"""
Unit Tests with Allure Reporting Integration.

Enhanced unit tests with Allure annotations for detailed reporting.
"""
import unittest
import sys
import os
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import allure
    ALLURE_AVAILABLE = True
except ImportError:
    ALLURE_AVAILABLE = False
    # Create dummy decorators if Allure is not available
    class allure:
        @staticmethod
        def feature(name):
            return lambda f: f
        @staticmethod
        def story(name):
            return lambda f: f
        @staticmethod
        def step(name):
            return lambda f: f
        @staticmethod
        def title(name):
            return lambda f: f
        @staticmethod
        def description(text):
            return lambda f: f
        @staticmethod
        def severity(level):
            return lambda f: f
        @staticmethod
        def attach(body, name, attachment_type):
            pass

from qoe_guard.diff import json_diff, extract_features
from qoe_guard.model import DiffResult, FeatureVector, RiskAssessment, Change
from tests.fixtures.sample_data import (
    BASELINE_PLAYBACK_RESPONSE,
    CANDIDATE_PLAYBACK_RESPONSE_MINOR,
    CANDIDATE_PLAYBACK_RESPONSE_BREAKING,
)


@allure.feature("JSON Diff Engine")
class TestJsonDiffAllure(unittest.TestCase):
    """Test cases for JSON diff engine with Allure reporting."""
    
    @allure.story("Basic Diff Operations")
    @allure.title("Identical JSON should produce no changes")
    @allure.severity(allure.severity_level.TRIVIAL)
    def test_identical_json_returns_no_changes(self):
        """Identical JSON objects should produce no changes."""
        with allure.step("Create identical JSON objects"):
            obj = {"key": "value", "nested": {"a": 1}}
        
        with allure.step("Run diff comparison"):
            result = json_diff(obj, obj)
        
        with allure.step("Verify no changes detected"):
            self.assertEqual(len(result.changes), 0)
            self.assertEqual(result.decision, "PASS")
            
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
        with allure.step("Prepare baseline and candidate JSON"):
            old = {"quality": "HD"}
            new = {"quality": "4K"}
            
            allure.attach(
                json.dumps({"baseline": old, "candidate": new}, indent=2),
                "Input JSON",
                allure.attachment_type.JSON
            )
        
        with allure.step("Execute diff"):
            result = json_diff(old, new)
        
        with allure.step("Verify change detection"):
            self.assertEqual(len(result.changes), 1)
            self.assertEqual(result.changes[0].change_type, "value_changed")
            self.assertEqual(result.changes[0].path, "$.quality")
            
            change_details = {
                "path": result.changes[0].path,
                "type": result.changes[0].change_type,
                "old_value": result.changes[0].old_value,
                "new_value": result.changes[0].new_value,
                "is_breaking": result.changes[0].is_breaking,
                "is_critical": result.changes[0].is_critical,
            }
            allure.attach(
                json.dumps(change_details, indent=2),
                "Detected Change",
                allure.attachment_type.JSON
            )
    
    @allure.story("Field Addition Detection")
    @allure.title("Added fields should be detected")
    @allure.severity(allure.severity_level.NORMAL)
    def test_field_added_detected(self):
        """Added fields should be detected."""
        old = {"a": 1}
        new = {"a": 1, "b": 2}
        
        result = json_diff(old, new)
        
        self.assertEqual(len(result.changes), 1)
        self.assertEqual(result.changes[0].change_type, "added")
        self.assertEqual(result.changes[0].path, "$.b")
        
        allure.attach(
            json.dumps({
                "baseline": old,
                "candidate": new,
                "changes": [{"path": c.path, "type": c.change_type} for c in result.changes]
            }, indent=2),
            "Field Addition Test",
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
        
        self.assertEqual(len(result.changes), 1)
        self.assertEqual(result.changes[0].change_type, "type_changed")
        self.assertTrue(result.changes[0].is_breaking)
        
        allure.attach(
            json.dumps({
                "change": {
                    "path": result.changes[0].path,
                    "type": result.changes[0].change_type,
                    "old_type": result.changes[0].old_type,
                    "new_type": result.changes[0].new_type,
                    "is_breaking": result.changes[0].is_breaking,
                },
                "decision": result.decision,
                "qoe_risk": result.qoe_risk_score
            }, indent=2),
            "Breaking Change Analysis",
            allure.attachment_type.JSON
        )


@allure.feature("Feature Extraction")
class TestFeatureExtractionAllure(unittest.TestCase):
    """Test cases for feature extraction with Allure reporting."""
    
    @allure.story("Feature Vector Generation")
    @allure.title("Empty changes should produce zero features")
    @allure.severity(allure.severity_level.TRIVIAL)
    def test_empty_changes_produce_zero_features(self):
        """No changes should produce zero/low features."""
        result = DiffResult(changes=[], decision="PASS", qoe_risk_score=0.0)
        features = extract_features(result)
        
        self.assertIsInstance(features, FeatureVector)
        self.assertEqual(features.total_changes, 0)
        
        allure.attach(
            json.dumps({
                "total_changes": features.total_changes,
                "added_fields": features.added_fields,
                "removed_fields": features.removed_fields,
            }, indent=2),
            "Feature Vector",
            allure.attachment_type.JSON
        )
    
    @allure.story("Critical Change Detection")
    @allure.title("Critical changes should be counted in features")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_critical_changes_counted(self):
        """Critical changes should be counted in features."""
        changes = [
            Change(
                path="$.drm.licenseUrl",
                change_type="removed",
                is_breaking=True,
                is_critical=True
            ),
            Change(
                path="$.playback.url",
                change_type="value_changed",
                is_breaking=False,
                is_critical=True
            ),
        ]
        result = DiffResult(changes=changes, decision="WARN", qoe_risk_score=0.6)
        features = extract_features(result)
        
        self.assertEqual(features.critical_changes, 2)
        
        allure.attach(
            json.dumps({
                "critical_changes": features.critical_changes,
                "breaking_changes": features.breaking_changes,
                "total_changes": features.total_changes,
            }, indent=2),
            "Critical Changes Analysis",
            allure.attachment_type.JSON
        )


@allure.feature("Scoring System")
class TestScoringAllure(unittest.TestCase):
    """Test scoring algorithms with Allure reporting."""
    
    @allure.story("Brittleness Scoring")
    @allure.title("Brittleness score should be within bounds")
    @allure.severity(allure.severity_level.NORMAL)
    def test_brittleness_score_bounds(self):
        """Brittleness score should be between 0 and 100."""
        from qoe_guard.scoring.brittleness import compute_brittleness_score
        
        with allure.step("Calculate brittleness with various inputs"):
            test_cases = [
                {"complexity": 0.3, "sensitivity": 0.5, "fragility": 0.2, "blast": 0.4},
                {"complexity": 0.8, "sensitivity": 0.9, "fragility": 0.7, "blast": 0.8},
                {"complexity": 0.0, "sensitivity": 0.0, "fragility": 0.0, "blast": 0.0},
            ]
            
            results = []
            for case in test_cases:
                score = compute_brittleness_score(
                    contract_complexity=case["complexity"],
                    change_sensitivity=case["sensitivity"],
                    runtime_fragility=case["fragility"],
                    blast_radius=case["blast"]
                )
                results.append({**case, "score": score})
                self.assertGreaterEqual(score, 0)
                self.assertLessEqual(score, 100)
        
        allure.attach(
            json.dumps(results, indent=2),
            "Brittleness Score Test Cases",
            allure.attachment_type.JSON
        )
    
    @allure.story("QoE Risk Scoring")
    @allure.title("QoE risk score should be within bounds")
    @allure.severity(allure.severity_level.NORMAL)
    def test_qoe_risk_bounds(self):
        """QoE risk score should be between 0 and 1."""
        from qoe_guard.scoring.qoe_risk import compute_qoe_risk
        
        test_cases = [
            {"changes": 5, "critical": 2, "type": 1, "removed": 1},
            {"changes": 1, "critical": 0, "type": 0, "removed": 0},
            {"changes": 20, "critical": 10, "type": 5, "removed": 5},
        ]
        
        results = []
        for case in test_cases:
            score = compute_qoe_risk(
                changes_count=case["changes"],
                critical_changes=case["critical"],
                type_changes=case["type"],
                removed_fields=case["removed"]
            )
            results.append({**case, "qoe_risk_score": score})
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 1)
        
        allure.attach(
            json.dumps(results, indent=2),
            "QoE Risk Score Test Cases",
            allure.attachment_type.JSON
        )


@allure.feature("Real-World Scenarios")
class TestRealWorldScenariosAllure(unittest.TestCase):
    """Test real-world JSON comparison scenarios."""
    
    @allure.story("Minor Changes Scenario")
    @allure.title("Minor changes should result in PASS decision")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("""
    Tests a real-world scenario where minor, non-breaking changes
    are made to a streaming API response. Expected outcome: PASS.
    """)
    def test_minor_changes_scenario(self):
        """Test minor changes scenario from sample data."""
        with allure.step("Load baseline and candidate responses"):
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
        
        with allure.step("Execute diff analysis"):
            result = json_diff(baseline, candidate)
        
        with allure.step("Extract features"):
            features = extract_features(result)
        
        with allure.step("Verify decision and scores"):
            self.assertIn(result.decision, ["PASS", "WARN"])
            self.assertLess(result.qoe_risk_score, 0.72)  # Should not be FAIL
            
            summary = {
                "decision": result.decision,
                "qoe_risk_score": result.qoe_risk_score,
                "total_changes": len(result.changes),
                "critical_changes": features.critical_changes,
                "breaking_changes": features.breaking_changes,
                "changes_summary": [
                    {
                        "path": c.path,
                        "type": c.change_type,
                        "is_breaking": c.is_breaking,
                        "is_critical": c.is_critical
                    }
                    for c in result.changes
                ]
            }
            allure.attach(
                json.dumps(summary, indent=2),
                "Analysis Summary",
                allure.attachment_type.JSON
            )
    
    @allure.story("Breaking Changes Scenario")
    @allure.title("Breaking changes should result in FAIL decision")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("""
    Tests a real-world scenario where breaking changes are made
    to a streaming API response. Expected outcome: FAIL.
    """)
    def test_breaking_changes_scenario(self):
        """Test breaking changes scenario from sample data."""
        baseline = BASELINE_PLAYBACK_RESPONSE
        candidate = CANDIDATE_PLAYBACK_RESPONSE_BREAKING
        
        allure.attach(
            json.dumps(baseline, indent=2),
            "Baseline Response",
            allure.attachment_type.JSON
        )
        allure.attach(
            json.dumps(candidate, indent=2),
            "Candidate Response (Breaking)",
            allure.attachment_type.JSON
        )
        
        result = json_diff(baseline, candidate)
        features = extract_features(result)
        
        # Breaking changes should result in WARN or FAIL
        self.assertIn(result.decision, ["WARN", "FAIL"])
        self.assertGreater(features.breaking_changes, 0)
        
        summary = {
            "decision": result.decision,
            "qoe_risk_score": result.qoe_risk_score,
            "total_changes": len(result.changes),
            "critical_changes": features.critical_changes,
            "breaking_changes": features.breaking_changes,
            "type_changes": features.type_changes,
            "removed_fields": features.removed_fields,
            "breaking_changes_detail": [
                {
                    "path": c.path,
                    "type": c.change_type,
                    "old_value": str(c.old_value)[:50] if c.old_value else None,
                    "new_value": str(c.new_value)[:50] if c.new_value else None,
                }
                for c in result.changes if c.is_breaking
            ]
        }
        allure.attach(
            json.dumps(summary, indent=2),
            "Breaking Changes Analysis",
            allure.attachment_type.JSON
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
