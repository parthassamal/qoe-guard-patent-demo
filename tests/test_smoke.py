"""
Smoke Tests for QoE-Guard.

Quick sanity checks to verify the application starts and basic functionality works.
Run these first to catch obvious issues before deeper testing.
"""
import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestImports(unittest.TestCase):
    """Test that all modules can be imported."""
    
    def test_import_main(self):
        """Main module should import without errors."""
        try:
            from qoe_guard import main
            self.assertTrue(hasattr(main, 'app'))
        except ImportError as e:
            self.skipTest(f"Could not import main: {e}")
        except PermissionError as e:
            self.skipTest(f"Permission error (sandbox): {e}")
    
    def test_import_diff(self):
        """Diff module should import."""
        from qoe_guard import diff
        self.assertTrue(hasattr(diff, 'json_diff'))
    
    def test_import_model(self):
        """Model module should import."""
        from qoe_guard import model
        self.assertTrue(hasattr(model, 'DiffResult'))
    
    def test_import_features(self):
        """Features module should import."""
        from qoe_guard import features
        self.assertTrue(callable(features.extract_features))
    
    def test_import_scoring_brittleness(self):
        """Brittleness scoring should import."""
        try:
            from qoe_guard.scoring import brittleness
            self.assertTrue(hasattr(brittleness, 'compute_brittleness_score'))
        except ImportError:
            self.skipTest("Brittleness module not available")
    
    def test_import_scoring_qoe_risk(self):
        """QoE risk scoring should import."""
        try:
            from qoe_guard.scoring import qoe_risk
            self.assertTrue(hasattr(qoe_risk, 'compute_qoe_risk'))
        except ImportError:
            self.skipTest("QoE risk module not available")
    
    def test_import_ai_modules(self):
        """AI modules should import (may require dependencies)."""
        try:
            from qoe_guard.ai import llm_analyzer
            from qoe_guard.ai import semantic_drift
            from qoe_guard.ai import anomaly_detector
            self.assertTrue(True)
        except ImportError as e:
            self.skipTest(f"AI modules require dependencies: {e}")


class TestBasicDiff(unittest.TestCase):
    """Test basic diff functionality."""
    
    def test_diff_empty_objects(self):
        """Empty objects should diff to no changes."""
        from qoe_guard.diff import json_diff
        result = json_diff({}, {})
        self.assertEqual(len(result.changes), 0)
    
    def test_diff_identical_objects(self):
        """Identical objects should diff to no changes."""
        from qoe_guard.diff import json_diff
        obj = {"key": "value", "num": 123}
        result = json_diff(obj, obj)
        self.assertEqual(len(result.changes), 0)
    
    def test_diff_detects_change(self):
        """Should detect a simple value change."""
        from qoe_guard.diff import json_diff
        old = {"status": "active"}
        new = {"status": "inactive"}
        result = json_diff(old, new)
        self.assertGreater(len(result.changes), 0)
    
    def test_diff_returns_valid_result(self):
        """Diff should return a valid DiffResult object."""
        from qoe_guard.diff import json_diff
        from qoe_guard.model import DiffResult
        
        result = json_diff({"a": 1}, {"a": 2})
        self.assertIsInstance(result, DiffResult)
        self.assertIn(result.decision, ["PASS", "WARN", "FAIL"])


class TestBasicFeatures(unittest.TestCase):
    """Test basic feature extraction."""
    
    def test_extract_features_from_diff(self):
        """Should extract features from a diff result."""
        from qoe_guard.diff import json_diff, extract_features
        from qoe_guard.model import FeatureVector
        
        result = json_diff({"a": 1}, {"a": 2, "b": 3})
        features = extract_features(result)
        self.assertIsInstance(features, FeatureVector)
    
    def test_features_have_expected_fields(self):
        """Feature vector should have expected fields."""
        from qoe_guard.diff import json_diff, extract_features
        
        result = json_diff({}, {"new": "field"})
        features = extract_features(result)
        
        self.assertTrue(hasattr(features, 'total_changes'))
        self.assertTrue(hasattr(features, 'added_fields'))


class TestBasicScoring(unittest.TestCase):
    """Test basic scoring functions."""
    
    def test_brittleness_score_is_numeric(self):
        """Brittleness score should be a number."""
        try:
            from qoe_guard.scoring.brittleness import compute_brittleness_score
            score = compute_brittleness_score(0.5, 0.5, 0.5, 0.5)
            self.assertIsInstance(score, (int, float))
        except ImportError:
            self.skipTest("Brittleness module not available")
    
    def test_qoe_risk_is_numeric(self):
        """QoE risk score should be a number."""
        try:
            from qoe_guard.scoring.qoe_risk import compute_qoe_risk
            score = compute_qoe_risk(5, 2, 1, 1)
            self.assertIsInstance(score, (int, float))
        except ImportError:
            self.skipTest("QoE risk module not available")


class TestConfiguration(unittest.TestCase):
    """Test configuration and environment."""
    
    def test_templates_directory_exists(self):
        """Templates directory should exist."""
        import os
        templates_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "qoe_guard", "templates"
        )
        self.assertTrue(os.path.isdir(templates_dir))
    
    def test_base_template_exists(self):
        """Base template should exist."""
        import os
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "qoe_guard", "templates", "base.html"
        )
        self.assertTrue(os.path.isfile(template_path))
    
    def test_help_template_exists(self):
        """Help template should exist."""
        import os
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "qoe_guard", "templates", "help.html"
        )
        self.assertTrue(os.path.isfile(template_path))


class TestModelDataClasses(unittest.TestCase):
    """Test model data classes."""
    
    def test_change_dataclass(self):
        """Change dataclass should work correctly."""
        from qoe_guard.model import Change
        
        change = Change(
            path="$.test.path",
            change_type="value_changed",
            old_value="old",
            new_value="new"
        )
        self.assertEqual(change.path, "$.test.path")
        self.assertEqual(change.change_type, "value_changed")
    
    def test_diff_result_dataclass(self):
        """DiffResult dataclass should work correctly."""
        from qoe_guard.model import DiffResult, Change
        
        result = DiffResult(
            changes=[Change(path="$.a", change_type="added")],
            decision="PASS",
            qoe_risk_score=0.1
        )
        self.assertEqual(len(result.changes), 1)
        self.assertEqual(result.decision, "PASS")
    
    def test_feature_vector_dataclass(self):
        """FeatureVector dataclass should work correctly."""
        from qoe_guard.model import FeatureVector
        
        features = FeatureVector(
            total_changes=5,
            added_fields=2,
            removed_fields=1,
            value_changes=2
        )
        self.assertEqual(features.total_changes, 5)


class TestSampleData(unittest.TestCase):
    """Test that sample data fixtures are valid."""
    
    def test_sample_openapi_spec_valid(self):
        """Sample OpenAPI spec should be valid JSON structure."""
        from tests.fixtures.sample_data import SAMPLE_OPENAPI_SPEC
        
        self.assertIn("openapi", SAMPLE_OPENAPI_SPEC)
        self.assertIn("info", SAMPLE_OPENAPI_SPEC)
        self.assertIn("paths", SAMPLE_OPENAPI_SPEC)
    
    def test_sample_responses_valid(self):
        """Sample responses should be valid JSON structures."""
        from tests.fixtures.sample_data import (
            BASELINE_PLAYBACK_RESPONSE,
            CANDIDATE_PLAYBACK_RESPONSE_MINOR,
            CANDIDATE_PLAYBACK_RESPONSE_BREAKING
        )
        
        self.assertIn("playback", BASELINE_PLAYBACK_RESPONSE)
        self.assertIn("playback", CANDIDATE_PLAYBACK_RESPONSE_MINOR)
        self.assertIn("playback", CANDIDATE_PLAYBACK_RESPONSE_BREAKING)
    
    def test_sample_metrics_valid(self):
        """Sample runtime metrics should be valid."""
        from tests.fixtures.sample_data import (
            RUNTIME_METRICS_NORMAL,
            RUNTIME_METRICS_WITH_ANOMALIES
        )
        
        self.assertIsInstance(RUNTIME_METRICS_NORMAL, list)
        self.assertIsInstance(RUNTIME_METRICS_WITH_ANOMALIES, list)
        self.assertGreater(len(RUNTIME_METRICS_NORMAL), 0)


if __name__ == "__main__":
    # Run smoke tests with quick output
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
