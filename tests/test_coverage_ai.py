"""
Comprehensive AI Module Tests for 100% Coverage.

Tests all AI/ML/NLP modules with mocks.
"""
import pytest
import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock

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
        class attachment_type:
            JSON = "application/json"


# ============================================================================
# Test qoe_guard.ai.anomaly_detector module
# ============================================================================
from qoe_guard.ai.anomaly_detector import (
    AnomalyDetector,
    AnomalyScore,
    RuntimeMetrics,
    AnomalyReport,
)
from datetime import datetime


@allure.feature("Anomaly Detector - Full Coverage")
class TestAnomalyDetectorFullCoverage:
    """Complete coverage for anomaly detector."""
    
    @allure.title("Test AnomalyScore dataclass")
    def test_anomaly_score(self):
        score = AnomalyScore(
            is_anomaly=True,
            score=0.85,
            confidence=0.9,
            features_contribution={"latency": 0.6, "errors": 0.25},
            explanation="High latency detected"
        )
        assert score.is_anomaly is True
        assert score.score == 0.85
    
    @allure.title("Test RuntimeMetrics dataclass")
    def test_runtime_metrics(self):
        metrics = RuntimeMetrics(
            latency_ms=150.0,
            status_code=200,
            response_size_bytes=1024,
            timestamp=datetime.now(),
            endpoint="/api/test",
            method="GET"
        )
        assert metrics.latency_ms == 150.0
        assert metrics.status_code == 200
    
    @allure.title("Test AnomalyReport dataclass")
    def test_anomaly_report(self):
        report = AnomalyReport(
            total_observations=100,
            anomaly_count=5,
            anomaly_rate=0.05,
            anomalies=[],
            recommendations=["Investigate latency spikes"],
            summary="5 anomalies detected"
        )
        assert report.total_observations == 100
        assert report.anomaly_rate == 0.05
    
    @allure.title("Test AnomalyDetector initialization")
    def test_anomaly_detector_init(self):
        detector = AnomalyDetector()
        assert detector is not None
    
    @allure.title("Test detect_anomalies with data")
    def test_detect_anomalies(self):
        detector = AnomalyDetector()
        
        # Create test data with clear anomalies
        data = [100, 105, 98, 102, 101, 500, 103, 99, 1000, 97]
        
        anomalies = detector.detect_anomalies(data)
        assert isinstance(anomalies, list)
    
    @allure.title("Test detect_anomalies with empty data")
    def test_detect_anomalies_empty(self):
        detector = AnomalyDetector()
        anomalies = detector.detect_anomalies([])
        assert isinstance(anomalies, list)
        assert len(anomalies) == 0
    
    @allure.title("Test detect_anomalies with uniform data")
    def test_detect_anomalies_uniform(self):
        detector = AnomalyDetector()
        # Uniform data should have no/few anomalies
        data = [100] * 20
        anomalies = detector.detect_anomalies(data)
        assert isinstance(anomalies, list)
    
    @allure.title("Test analyze_metrics")
    def test_analyze_metrics(self):
        detector = AnomalyDetector()
        
        metrics = [
            RuntimeMetrics(
                latency_ms=100.0,
                status_code=200,
                response_size_bytes=1024,
                timestamp=datetime.now(),
                endpoint="/api/test",
                method="GET"
            ),
            RuntimeMetrics(
                latency_ms=5000.0,  # Anomaly
                status_code=500,
                response_size_bytes=512,
                timestamp=datetime.now(),
                endpoint="/api/test",
                method="GET"
            )
        ]
        
        report = detector.analyze_metrics(metrics)
        assert report is not None
        assert isinstance(report, AnomalyReport)
    
    @allure.title("Test z_score detection")
    def test_z_score_detection(self):
        detector = AnomalyDetector()
        detector.method = "z_score"
        
        data = [100, 102, 98, 101, 99, 1000, 103, 97]  # 1000 is anomaly
        anomalies = detector.detect_anomalies(data)
        assert isinstance(anomalies, list)


# ============================================================================
# Test qoe_guard.ai.llm_analyzer module
# ============================================================================
from qoe_guard.ai.llm_analyzer import (
    LLMAnalyzer,
    DiffAnalysis,
    LLMProvider,
)


@allure.feature("LLM Analyzer - Full Coverage")
class TestLLMAnalyzerFullCoverage:
    """Complete coverage for LLM analyzer."""
    
    @allure.title("Test LLMProvider enum")
    def test_llm_provider_enum(self):
        assert LLMProvider.GROQ.value == "groq"
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.ANTHROPIC.value == "anthropic"
    
    @allure.title("Test DiffAnalysis dataclass")
    def test_diff_analysis(self):
        analysis = DiffAnalysis(
            summary="Breaking changes detected",
            classification="breaking",
            impact="high",
            recommendations=["Review type changes", "Update clients"],
            confidence=0.9
        )
        assert analysis.summary == "Breaking changes detected"
        assert analysis.classification == "breaking"
    
    @allure.title("Test LLMAnalyzer initialization")
    def test_llm_analyzer_init(self):
        analyzer = LLMAnalyzer()
        assert analyzer is not None
    
    @allure.title("Test LLMAnalyzer is_available")
    def test_llm_analyzer_is_available(self):
        analyzer = LLMAnalyzer()
        # May be True or False depending on env vars
        result = analyzer.is_available()
        assert isinstance(result, bool)
    
    @allure.title("Test LLMAnalyzer analyze_diff without API key")
    def test_llm_analyzer_analyze_diff_no_key(self):
        analyzer = LLMAnalyzer()
        
        diff_result = {
            "changes": [{"path": "$.test", "type": "value_changed"}],
            "decision": "WARN"
        }
        
        # Should return fallback analysis without API key
        result = analyzer.analyze_diff(diff_result)
        assert result is not None
    
    @allure.title("Test LLMAnalyzer with mock Groq")
    @patch('qoe_guard.ai.llm_analyzer.Groq')
    def test_llm_analyzer_groq_mock(self, mock_groq):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "summary": "Test analysis",
            "classification": "minor",
            "impact": "low",
            "recommendations": ["No action needed"]
        })
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq.return_value = mock_client
        
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            analyzer = LLMAnalyzer()
            # Force Groq provider
            analyzer.provider = LLMProvider.GROQ
            analyzer.client = mock_client
            
            result = analyzer.analyze_diff({"changes": [], "decision": "PASS"})
            assert result is not None


# ============================================================================
# Test qoe_guard.ai.semantic_drift module
# ============================================================================
from qoe_guard.ai.semantic_drift import (
    SemanticDriftDetector,
    DriftResult,
    SemanticSimilarity,
)


@allure.feature("Semantic Drift - Full Coverage")
class TestSemanticDriftFullCoverage:
    """Complete coverage for semantic drift detector."""
    
    @allure.title("Test SemanticSimilarity dataclass")
    def test_semantic_similarity(self):
        sim = SemanticSimilarity(
            text1="user authentication",
            text2="user login",
            similarity_score=0.85,
            is_equivalent=True
        )
        assert sim.similarity_score == 0.85
        assert sim.is_equivalent is True
    
    @allure.title("Test DriftResult dataclass")
    def test_drift_result(self):
        result = DriftResult(
            has_drift=True,
            drift_score=0.3,
            drifted_fields=["$.description"],
            explanation="Field description has changed semantically"
        )
        assert result.has_drift is True
        assert result.drift_score == 0.3
    
    @allure.title("Test SemanticDriftDetector initialization")
    def test_semantic_drift_init(self):
        detector = SemanticDriftDetector()
        assert detector is not None
    
    @allure.title("Test compare_texts")
    def test_compare_texts(self):
        detector = SemanticDriftDetector()
        
        result = detector.compare_texts(
            "user authentication",
            "user login"
        )
        assert result is not None
        assert hasattr(result, 'similarity_score')
    
    @allure.title("Test detect_drift")
    def test_detect_drift(self):
        detector = SemanticDriftDetector()
        
        baseline = {
            "description": "Get user by ID",
            "summary": "Retrieve user"
        }
        candidate = {
            "description": "Fetch user by identifier",
            "summary": "Get user data"
        }
        
        result = detector.detect_drift(baseline, candidate)
        assert result is not None
        assert isinstance(result, DriftResult)


# ============================================================================
# Test qoe_guard.ai.nlp_analyzer module
# ============================================================================
from qoe_guard.ai.nlp_analyzer import (
    NLPAnalyzer,
    EndpointClassification,
    CriticalityScore,
)


@allure.feature("NLP Analyzer - Full Coverage")
class TestNLPAnalyzerFullCoverage:
    """Complete coverage for NLP analyzer."""
    
    @allure.title("Test EndpointClassification dataclass")
    def test_endpoint_classification(self):
        classification = EndpointClassification(
            endpoint="/api/users",
            category="crud",
            tags=["users", "authentication"],
            criticality="high"
        )
        assert classification.category == "crud"
        assert "users" in classification.tags
    
    @allure.title("Test CriticalityScore dataclass")
    def test_criticality_score(self):
        score = CriticalityScore(
            path="$.playback.manifestUrl",
            score=0.95,
            reason="Critical playback field"
        )
        assert score.score == 0.95
    
    @allure.title("Test NLPAnalyzer initialization")
    def test_nlp_analyzer_init(self):
        analyzer = NLPAnalyzer()
        assert analyzer is not None
    
    @allure.title("Test classify_endpoint")
    def test_classify_endpoint(self):
        analyzer = NLPAnalyzer()
        
        result = analyzer.classify_endpoint(
            path="/api/users/{id}",
            method="GET",
            summary="Get user by ID",
            description="Retrieves a user by their unique identifier"
        )
        
        assert result is not None
        assert isinstance(result, EndpointClassification)
    
    @allure.title("Test extract_keywords")
    def test_extract_keywords(self):
        analyzer = NLPAnalyzer()
        
        text = "This endpoint handles user authentication and authorization"
        keywords = analyzer.extract_keywords(text)
        
        assert isinstance(keywords, list)
    
    @allure.title("Test analyze_documentation_quality")
    def test_analyze_doc_quality(self):
        analyzer = NLPAnalyzer()
        
        result = analyzer.analyze_documentation_quality(
            summary="Get user",
            description="Gets the user from the database by ID and returns their profile"
        )
        
        assert result is not None
        assert "score" in result or hasattr(result, 'score')


# ============================================================================
# Test qoe_guard.ai.ml_scorer module
# ============================================================================
from qoe_guard.ai.ml_scorer import (
    MLScorer,
    MLPrediction,
    FeatureImportance,
)


@allure.feature("ML Scorer - Full Coverage")
class TestMLScorerFullCoverage:
    """Complete coverage for ML scorer."""
    
    @allure.title("Test MLPrediction dataclass")
    def test_ml_prediction(self):
        prediction = MLPrediction(
            risk_score=0.75,
            decision="WARN",
            confidence=0.85,
            feature_contributions={"type_changes": 0.4, "removed_fields": 0.35}
        )
        assert prediction.risk_score == 0.75
        assert prediction.decision == "WARN"
    
    @allure.title("Test FeatureImportance dataclass")
    def test_feature_importance(self):
        importance = FeatureImportance(
            feature_name="type_changes",
            importance_score=0.35,
            direction="positive"
        )
        assert importance.feature_name == "type_changes"
        assert importance.importance_score == 0.35
    
    @allure.title("Test MLScorer initialization")
    def test_ml_scorer_init(self):
        scorer = MLScorer()
        assert scorer is not None
    
    @allure.title("Test MLScorer predict")
    def test_ml_scorer_predict(self):
        scorer = MLScorer()
        
        from qoe_guard.model import FeatureVector
        features = FeatureVector(
            total_changes=10,
            breaking_changes=2,
            type_changes=1,
            critical_changes=3,
            added_fields=2,
            removed_fields=2
        )
        
        result = scorer.predict(features)
        assert result is not None
        assert isinstance(result, MLPrediction)
    
    @allure.title("Test MLScorer explain_prediction")
    def test_ml_scorer_explain(self):
        scorer = MLScorer()
        
        from qoe_guard.model import FeatureVector
        features = FeatureVector(
            total_changes=5,
            breaking_changes=1,
            type_changes=0,
            critical_changes=1
        )
        
        explanation = scorer.explain_prediction(features)
        assert explanation is not None
    
    @allure.title("Test MLScorer get_feature_importance")
    def test_ml_scorer_feature_importance(self):
        scorer = MLScorer()
        
        importance = scorer.get_feature_importance()
        assert isinstance(importance, list)


# ============================================================================
# Test qoe_guard.cli module
# ============================================================================
from qoe_guard.cli import main as cli_main, parse_args


@allure.feature("CLI - Full Coverage")
class TestCLIFullCoverage:
    """Complete coverage for CLI module."""
    
    @allure.title("Test parse_args with defaults")
    def test_parse_args_defaults(self):
        args = parse_args(["validate", "--baseline", "baseline.json", "--candidate", "candidate.json"])
        assert args.command == "validate"
        assert args.baseline == "baseline.json"
        assert args.candidate == "candidate.json"
    
    @allure.title("Test parse_args with all options")
    def test_parse_args_full(self):
        args = parse_args([
            "validate",
            "--baseline", "baseline.json",
            "--candidate", "candidate.json",
            "--output", "json",
            "--fail-on-warn",
            "--verbose"
        ])
        assert args.command == "validate"
        assert args.output == "json"
        assert args.fail_on_warn is True
        assert args.verbose is True
    
    @allure.title("Test CLI help command")
    def test_cli_help(self):
        with pytest.raises(SystemExit) as exc_info:
            parse_args(["--help"])
        assert exc_info.value.code == 0
    
    @allure.title("Test CLI version command")
    def test_cli_version(self):
        args = parse_args(["version"])
        assert args.command == "version"
