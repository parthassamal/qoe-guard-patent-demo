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
    LLMConfig,
    FixRecommendation,
)


@allure.feature("LLM Analyzer - Full Coverage")
class TestLLMAnalyzerFullCoverage:
    """Complete coverage for LLM analyzer."""
    
    @allure.title("Test LLMProvider enum")
    def test_llm_provider_enum(self):
        assert LLMProvider.GROQ.value == "groq"
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.ANTHROPIC.value == "anthropic"
    
    @allure.title("Test LLMConfig dataclass")
    def test_llm_config(self):
        config = LLMConfig(
            provider=LLMProvider.GROQ,
            model="llama3-8b-8192",
            temperature=0.7,
            max_tokens=1000
        )
        assert config.provider == LLMProvider.GROQ
        assert config.model == "llama3-8b-8192"
    
    @allure.title("Test DiffAnalysis dataclass")
    def test_diff_analysis(self):
        analysis = DiffAnalysis(
            summary="Breaking changes detected",
            impact_level="high",
            breaking_changes=[],
            recommendations=[],
            confidence=0.9
        )
        assert analysis.summary == "Breaking changes detected"
        assert analysis.impact_level == "high"
    
    @allure.title("Test FixRecommendation dataclass")
    def test_fix_recommendation(self):
        rec = FixRecommendation(
            change_path="$.response.data",
            issue="Type changed from int to string",
            recommendation="Update client parsers",
            priority="high",
            code_example="// Handle both types"
        )
        assert rec.priority == "high"
    
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
        
        from qoe_guard.diff import json_diff
        diff_result = json_diff({"a": 1}, {"a": 2})
        
        # Should return fallback analysis without API key
        result = analyzer.analyze_diff(diff_result)
        assert result is not None
        assert isinstance(result, DiffAnalysis)


# ============================================================================
# Test qoe_guard.ai.semantic_drift module
# ============================================================================
from qoe_guard.ai.semantic_drift import (
    SemanticDriftDetector,
    SemanticMatch,
    SemanticDriftReport,
)


@allure.feature("Semantic Drift - Full Coverage")
class TestSemanticDriftFullCoverage:
    """Complete coverage for semantic drift detector."""
    
    @allure.title("Test SemanticMatch dataclass")
    def test_semantic_match(self):
        match = SemanticMatch(
            text1="user authentication",
            text2="user login",
            similarity=0.85,
            is_match=True,
            method="embedding"
        )
        assert match.similarity == 0.85
        assert match.is_match is True
    
    @allure.title("Test SemanticDriftReport dataclass")
    def test_semantic_drift_report(self):
        report = SemanticDriftReport(
            has_drift=True,
            drift_score=0.3,
            changed_fields=[],
            matches=[],
            summary="Drift detected"
        )
        assert report.has_drift is True
        assert report.drift_score == 0.3
    
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
        assert isinstance(result, SemanticMatch)
    
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
        assert isinstance(result, SemanticDriftReport)


# ============================================================================
# Test qoe_guard.ai.nlp_analyzer module
# ============================================================================
from qoe_guard.ai.nlp_analyzer import (
    NLPAnalyzer,
    EndpointIntent,
    CriticalityClassification,
    DocumentationQuality,
)


@allure.feature("NLP Analyzer - Full Coverage")
class TestNLPAnalyzerFullCoverage:
    """Complete coverage for NLP analyzer."""
    
    @allure.title("Test EndpointIntent dataclass")
    def test_endpoint_intent(self):
        intent = EndpointIntent(
            endpoint="/api/users",
            intent="retrieve",
            confidence=0.9,
            keywords=["users", "get"],
            suggested_tags=["users", "crud"]
        )
        assert intent.intent == "retrieve"
        assert intent.confidence == 0.9
    
    @allure.title("Test CriticalityClassification dataclass")
    def test_criticality_classification(self):
        classification = CriticalityClassification(
            path="$.playback.manifestUrl",
            criticality_score=0.95,
            category="core",
            reasoning="Critical playback field"
        )
        assert classification.criticality_score == 0.95
    
    @allure.title("Test DocumentationQuality dataclass")
    def test_documentation_quality(self):
        quality = DocumentationQuality(
            completeness_score=0.8,
            clarity_score=0.9,
            consistency_score=0.85,
            suggestions=["Add more examples"],
            overall_score=0.85
        )
        assert quality.overall_score == 0.85
    
    @allure.title("Test NLPAnalyzer initialization")
    def test_nlp_analyzer_init(self):
        analyzer = NLPAnalyzer()
        assert analyzer is not None
    
    @allure.title("Test classify_endpoint")
    def test_classify_endpoint(self):
        analyzer = NLPAnalyzer()
        
        result = analyzer.classify_intent(
            path="/api/users/{id}",
            method="GET",
            summary="Get user by ID",
            description="Retrieves a user by their unique identifier"
        )
        
        assert result is not None
        assert isinstance(result, EndpointIntent)
    
    @allure.title("Test extract_keywords")
    def test_extract_keywords(self):
        analyzer = NLPAnalyzer()
        
        text = "This endpoint handles user authentication and authorization"
        keywords = analyzer.extract_keywords(text)
        
        assert isinstance(keywords, list)
    
    @allure.title("Test analyze_documentation_quality")
    def test_analyze_doc_quality(self):
        analyzer = NLPAnalyzer()
        
        result = analyzer.analyze_documentation(
            summary="Get user",
            description="Gets the user from the database by ID and returns their profile"
        )
        
        assert result is not None
        assert isinstance(result, DocumentationQuality)


# ============================================================================
# Test qoe_guard.ai.ml_scorer module
# ============================================================================
from qoe_guard.ai.ml_scorer import (
    MLRiskScorer,
    MLPrediction,
    SHAPExplanation,
    FeatureVector as MLFeatureVector,
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
            model_version="1.0",
            feature_contributions={"type_changes": 0.4, "removed_fields": 0.35}
        )
        assert prediction.risk_score == 0.75
        assert prediction.decision == "WARN"
    
    @allure.title("Test SHAPExplanation dataclass")
    def test_shap_explanation(self):
        explanation = SHAPExplanation(
            base_value=0.5,
            shap_values={"type_changes": 0.2},
            feature_names=["type_changes"],
            expected_value=0.7
        )
        assert explanation.base_value == 0.5
    
    @allure.title("Test MLFeatureVector dataclass")
    def test_ml_feature_vector(self):
        fv = MLFeatureVector(
            total_changes=10,
            added_fields=2,
            removed_fields=3,
            type_changes=1,
            value_changes=4,
            critical_path_changes=2,
            array_changes=1,
            depth_changes=1,
            breaking_changes=2
        )
        assert fv.total_changes == 10
    
    @allure.title("Test MLRiskScorer initialization")
    def test_ml_scorer_init(self):
        scorer = MLRiskScorer()
        assert scorer is not None
    
    @allure.title("Test MLRiskScorer predict")
    def test_ml_scorer_predict(self):
        scorer = MLRiskScorer()
        
        features = MLFeatureVector(
            total_changes=10,
            added_fields=2,
            removed_fields=2,
            type_changes=1,
            value_changes=3,
            critical_path_changes=2,
            array_changes=1,
            depth_changes=1,
            breaking_changes=2
        )
        
        result = scorer.predict(features)
        assert result is not None
        assert isinstance(result, MLPrediction)
    
    @allure.title("Test MLRiskScorer explain")
    def test_ml_scorer_explain(self):
        scorer = MLRiskScorer()
        
        features = MLFeatureVector(
            total_changes=5,
            added_fields=1,
            removed_fields=1,
            type_changes=0,
            value_changes=2,
            critical_path_changes=1,
            array_changes=0,
            depth_changes=0,
            breaking_changes=1
        )
        
        explanation = scorer.explain(features)
        assert explanation is not None
        assert isinstance(explanation, SHAPExplanation)


# ============================================================================
# Test qoe_guard.cli module
# ============================================================================
try:
    from qoe_guard.cli import main as cli_main, load_json_file, run_validation, format_summary
    HAS_CLI = True
except ImportError:
    HAS_CLI = False


@allure.feature("CLI - Full Coverage")
@pytest.mark.skipif(not HAS_CLI, reason="CLI module not available")
class TestCLIFullCoverage:
    """Complete coverage for CLI module."""
    
    @allure.title("Test load_json_file with invalid path")
    def test_load_json_file_invalid(self):
        with pytest.raises(Exception):
            load_json_file("/nonexistent/path.json")
    
    @allure.title("Test run_validation function")
    def test_run_validation(self):
        baseline = {"test": 1, "data": "value"}
        candidate = {"test": 2, "data": "value"}
        
        result = run_validation(baseline, candidate)
        
        assert result is not None
        assert "decision" in result or "changes" in result
    
    @allure.title("Test format_summary function")
    def test_format_summary(self):
        result = {
            "decision": "PASS",
            "qoe_risk_score": 0.2,
            "total_changes": 5,
            "breaking_changes": 0
        }
        
        summary = format_summary(result)
        
        assert isinstance(summary, str)
        assert "PASS" in summary or "decision" in summary.lower()
