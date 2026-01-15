"""
AI/ML/NLP Module for QoE-Guard Enterprise.

Provides intelligent analysis capabilities:
- LLM-powered recommendations (Groq, OpenAI, Anthropic)
- Semantic drift detection using embeddings
- Anomaly detection for runtime signals
- NLP-based API documentation analysis
- Explainable ML risk scoring
"""
from .llm_analyzer import LLMAnalyzer, analyze_diff_with_llm, generate_recommendations
from .semantic_drift import SemanticDriftDetector, detect_semantic_changes
from .anomaly_detector import AnomalyDetector, detect_runtime_anomalies
from .nlp_analyzer import NLPAnalyzer, extract_api_intent, classify_endpoint_criticality
from .ml_scorer import MLRiskScorer, train_risk_model, explain_prediction

__all__ = [
    # LLM
    "LLMAnalyzer",
    "analyze_diff_with_llm",
    "generate_recommendations",
    # Semantic
    "SemanticDriftDetector",
    "detect_semantic_changes",
    # Anomaly
    "AnomalyDetector",
    "detect_runtime_anomalies",
    # NLP
    "NLPAnalyzer",
    "extract_api_intent",
    "classify_endpoint_criticality",
    # ML
    "MLRiskScorer",
    "train_risk_model",
    "explain_prediction",
]
