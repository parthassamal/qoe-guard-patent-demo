"""
AI Analysis API Router for QoE-Guard.

Provides REST endpoints for AI-powered features:
- LLM-based diff analysis and recommendations
- Semantic drift detection
- Anomaly detection
- NLP-based endpoint classification
- ML risk scoring
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

router = APIRouter(prefix="/ai", tags=["AI Analysis"])


# Request/Response Models
class DiffAnalysisRequest(BaseModel):
    """Request for LLM diff analysis."""
    baseline: Dict[str, Any] = Field(..., description="Baseline JSON response")
    candidate: Dict[str, Any] = Field(..., description="Candidate JSON response")
    changes: List[Dict[str, Any]] = Field(default=[], description="Pre-computed changes")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    llm_provider: Optional[str] = Field(default=None, description="LLM provider: groq, openai, anthropic")


class DiffAnalysisResponse(BaseModel):
    """Response from LLM diff analysis."""
    summary: str
    breaking_changes: List[str]
    non_breaking_changes: List[str]
    risk_assessment: str
    recommendations: List[str]
    impact_prediction: str
    confidence: float
    provider_used: Optional[str]


class SemanticDriftRequest(BaseModel):
    """Request for semantic drift detection."""
    baseline: Dict[str, Any]
    candidate: Dict[str, Any]
    similarity_threshold: float = Field(default=0.75, ge=0.0, le=1.0)


class SemanticDriftResponse(BaseModel):
    """Response from semantic drift detection."""
    total_comparisons: int
    potential_renames: List[Dict[str, Any]]
    value_equivalences: List[Dict[str, Any]]
    semantic_drifts: List[Dict[str, Any]]
    summary: str


class AnomalyDetectionRequest(BaseModel):
    """Request for anomaly detection."""
    metrics: List[Dict[str, Any]] = Field(..., description="Runtime metrics to analyze")
    historical_metrics: Optional[List[Dict[str, Any]]] = Field(default=None, description="Historical data for training")
    algorithm: str = Field(default="isolation_forest", description="Algorithm: isolation_forest, one_class_svm, lof, statistical")


class AnomalyDetectionResponse(BaseModel):
    """Response from anomaly detection."""
    total_observations: int
    anomaly_count: int
    anomaly_rate: float
    top_anomalies: List[Dict[str, Any]]
    patterns_detected: List[str]
    summary: str


class EndpointClassificationRequest(BaseModel):
    """Request for endpoint classification."""
    endpoint_path: str
    method: str
    description: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[List[str]] = None


class EndpointClassificationResponse(BaseModel):
    """Response from endpoint classification."""
    intent: Dict[str, Any]
    criticality: Dict[str, Any]
    suggested_tags: List[str]


class MLScoringRequest(BaseModel):
    """Request for ML risk scoring."""
    changes: List[Dict[str, Any]]
    criticality_profiles: Optional[Dict[str, float]] = None
    runtime_metrics: Optional[Dict[str, float]] = None


class MLScoringResponse(BaseModel):
    """Response from ML risk scoring."""
    risk_score: float
    decision: str
    confidence: float
    top_contributors: List[Dict[str, Any]]
    explanation: str
    shap_explanation: Optional[Dict[str, Any]] = None


class RecommendationsRequest(BaseModel):
    """Request for AI-generated recommendations."""
    analysis_summary: str
    breaking_changes: List[str]
    brittleness_score: float = Field(default=50.0, ge=0.0, le=100.0)
    qoe_risk_score: float = Field(default=0.5, ge=0.0, le=1.0)


class RecommendationsResponse(BaseModel):
    """Response with AI recommendations."""
    recommendations: List[Dict[str, Any]]


class AIStatusResponse(BaseModel):
    """Status of AI components."""
    llm_available: bool
    llm_provider: Optional[str]
    semantic_drift_available: bool
    anomaly_detection_available: bool
    nlp_available: bool
    ml_scoring_available: bool


# Endpoints
@router.get("/status", response_model=AIStatusResponse)
async def get_ai_status():
    """
    Check status of AI/ML components.
    
    Returns availability of each AI module.
    """
    status = AIStatusResponse(
        llm_available=False,
        llm_provider=None,
        semantic_drift_available=False,
        anomaly_detection_available=False,
        nlp_available=False,
        ml_scoring_available=False,
    )
    
    # Check LLM
    try:
        from qoe_guard.ai.llm_analyzer import LLMAnalyzer
        analyzer = LLMAnalyzer()
        status.llm_available = analyzer.is_available
        if analyzer.provider:
            status.llm_provider = analyzer.provider.value
    except Exception:
        pass
    
    # Check semantic drift
    try:
        from qoe_guard.ai.semantic_drift import SemanticDriftDetector
        detector = SemanticDriftDetector()
        status.semantic_drift_available = detector.is_available
    except Exception:
        pass
    
    # Check anomaly detection
    try:
        from qoe_guard.ai.anomaly_detector import AnomalyDetector
        detector = AnomalyDetector()
        status.anomaly_detection_available = detector.is_available
    except Exception:
        pass
    
    # Check NLP
    try:
        from qoe_guard.ai.nlp_analyzer import NLPAnalyzer
        analyzer = NLPAnalyzer()
        status.nlp_available = analyzer.is_available
    except Exception:
        pass
    
    # Check ML scoring
    try:
        from qoe_guard.ai.ml_scorer import MLRiskScorer
        scorer = MLRiskScorer()
        status.ml_scoring_available = scorer.model is not None
    except Exception:
        pass
    
    return status


@router.post("/analyze-diff", response_model=DiffAnalysisResponse)
async def analyze_diff_with_ai(request: DiffAnalysisRequest):
    """
    Analyze API diff using LLM (Groq/OpenAI/Anthropic).
    
    Provides:
    - Natural language summary
    - Breaking change classification
    - Risk assessment
    - Actionable recommendations
    """
    try:
        from qoe_guard.ai.llm_analyzer import LLMAnalyzer, LLMProvider
        
        # Select provider if specified
        provider = None
        if request.llm_provider:
            provider = LLMProvider(request.llm_provider)
        
        analyzer = LLMAnalyzer(provider=provider)
        
        result = analyzer.analyze_diff(
            baseline=request.baseline,
            candidate=request.candidate,
            changes=request.changes,
            context=request.context,
        )
        
        return DiffAnalysisResponse(
            summary=result.summary,
            breaking_changes=result.breaking_changes,
            non_breaking_changes=result.non_breaking_changes,
            risk_assessment=result.risk_assessment,
            recommendations=result.recommendations,
            impact_prediction=result.impact_prediction,
            confidence=result.confidence,
            provider_used=analyzer.provider.value if analyzer.provider else None,
        )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM libraries not installed. Run: pip install groq openai anthropic",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}",
        )


@router.post("/semantic-drift", response_model=SemanticDriftResponse)
async def detect_semantic_drift(request: SemanticDriftRequest):
    """
    Detect semantic drift between baseline and candidate.
    
    Uses embeddings to detect:
    - Potential field renames
    - Semantically equivalent values
    - Subtle meaning changes
    """
    try:
        from qoe_guard.ai.semantic_drift import SemanticDriftDetector
        
        detector = SemanticDriftDetector(
            similarity_threshold=request.similarity_threshold,
        )
        
        result = detector.detect_drift(
            baseline=request.baseline,
            candidate=request.candidate,
        )
        
        return SemanticDriftResponse(
            total_comparisons=result.total_comparisons,
            potential_renames=[
                {
                    "source": m.source_key,
                    "target": m.target_key,
                    "similarity": m.similarity,
                }
                for m in result.potential_renames
            ],
            value_equivalences=[
                {
                    "key": m.source_key,
                    "old_value": m.source_value,
                    "new_value": m.target_value,
                    "similarity": m.similarity,
                }
                for m in result.value_equivalences
            ],
            semantic_drifts=[
                {
                    "key": m.source_key,
                    "old_value": m.source_value,
                    "new_value": m.target_value,
                    "similarity": m.similarity,
                }
                for m in result.semantic_drifts
            ],
            summary=result.summary,
        )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Semantic analysis libraries not installed. Run: pip install sentence-transformers",
        )


@router.post("/detect-anomalies", response_model=AnomalyDetectionResponse)
async def detect_anomalies(request: AnomalyDetectionRequest):
    """
    Detect anomalies in runtime metrics.
    
    Uses ML algorithms to identify:
    - Latency spikes
    - Error bursts
    - Unusual patterns
    """
    try:
        from qoe_guard.ai.anomaly_detector import AnomalyDetector, RuntimeMetrics
        from datetime import datetime
        
        detector = AnomalyDetector(algorithm=request.algorithm)
        
        # Convert metrics
        metrics = [
            RuntimeMetrics(
                latency_ms=m.get("latency_ms", 0),
                status_code=m.get("status_code", 200),
                response_size_bytes=m.get("response_size_bytes", 0),
                timestamp=datetime.fromisoformat(m["timestamp"]) if "timestamp" in m else datetime.now(),
                endpoint=m.get("endpoint", "unknown"),
                method=m.get("method", "GET"),
            )
            for m in request.metrics
        ]
        
        # Fit on historical if provided
        if request.historical_metrics:
            historical = [
                RuntimeMetrics(
                    latency_ms=m.get("latency_ms", 0),
                    status_code=m.get("status_code", 200),
                    response_size_bytes=m.get("response_size_bytes", 0),
                    timestamp=datetime.fromisoformat(m["timestamp"]) if "timestamp" in m else datetime.now(),
                    endpoint=m.get("endpoint", "unknown"),
                    method=m.get("method", "GET"),
                )
                for m in request.historical_metrics
            ]
            detector.fit(historical)
        
        result = detector.detect_batch(metrics)
        
        return AnomalyDetectionResponse(
            total_observations=result.total_observations,
            anomaly_count=result.anomaly_count,
            anomaly_rate=result.anomaly_rate,
            top_anomalies=[
                {
                    "endpoint": m.endpoint,
                    "latency_ms": m.latency_ms,
                    "status_code": m.status_code,
                    "score": s.score,
                    "explanation": s.explanation,
                }
                for m, s in result.top_anomalies
            ],
            patterns_detected=result.patterns_detected,
            summary=result.summary,
        )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Anomaly detection libraries not installed. Run: pip install scikit-learn",
        )


@router.post("/classify-endpoint", response_model=EndpointClassificationResponse)
async def classify_endpoint(request: EndpointClassificationRequest):
    """
    Classify endpoint using NLP.
    
    Extracts:
    - Intent (playback, auth, metadata, etc.)
    - Criticality level
    - Suggested tags
    """
    try:
        from qoe_guard.ai.nlp_analyzer import NLPAnalyzer
        
        analyzer = NLPAnalyzer()
        
        intent = analyzer.extract_intent(
            endpoint_path=request.endpoint_path,
            method=request.method,
            description=request.description,
            summary=request.summary,
        )
        
        criticality = analyzer.classify_criticality(
            endpoint_path=request.endpoint_path,
            method=request.method,
            description=request.description,
            tags=request.tags,
        )
        
        return EndpointClassificationResponse(
            intent={
                "primary": intent.primary_intent,
                "confidence": intent.confidence,
                "secondary": intent.secondary_intents,
                "business_domain": intent.business_domain,
                "keywords": intent.keywords,
            },
            criticality={
                "level": criticality.criticality_level,
                "score": criticality.score,
                "qoe_impact": criticality.qoe_impact,
                "reasons": criticality.reasons,
            },
            suggested_tags=criticality.suggested_tags,
        )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NLP libraries not installed. Run: pip install spacy transformers",
        )


@router.post("/ml-score", response_model=MLScoringResponse)
async def ml_risk_score(request: MLScoringRequest):
    """
    Get ML-based risk score for changes.
    
    Uses trained model to predict risk and provides SHAP explanation.
    """
    try:
        from qoe_guard.ai.ml_scorer import MLRiskScorer, extract_features_from_changes
        
        scorer = MLRiskScorer()
        
        features = extract_features_from_changes(
            changes=request.changes,
            criticality_profiles=request.criticality_profiles,
            runtime_metrics=request.runtime_metrics,
        )
        
        prediction = scorer.predict(features)
        
        # Try to get SHAP explanation
        shap_explanation = None
        if scorer.is_trained:
            try:
                shap_result = scorer.explain(features)
                shap_explanation = {
                    "base_value": shap_result.base_value,
                    "shap_values": shap_result.shap_values,
                    "top_positive": shap_result.top_positive,
                    "top_negative": shap_result.top_negative,
                }
            except Exception:
                pass
        
        return MLScoringResponse(
            risk_score=prediction.risk_score,
            decision=prediction.decision,
            confidence=prediction.confidence,
            top_contributors=[
                {"feature": c[0], "contribution": c[1], "direction": c[2]}
                for c in prediction.top_contributors
            ],
            explanation=prediction.explanation,
            shap_explanation=shap_explanation,
        )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML libraries not installed. Run: pip install xgboost shap scikit-learn",
        )


@router.post("/recommendations", response_model=RecommendationsResponse)
async def get_ai_recommendations(request: RecommendationsRequest):
    """
    Get AI-generated fix recommendations.
    
    Uses LLM to generate prioritized, actionable recommendations.
    """
    try:
        from qoe_guard.ai.llm_analyzer import LLMAnalyzer, DiffAnalysis
        
        analyzer = LLMAnalyzer()
        
        analysis = DiffAnalysis(
            summary=request.analysis_summary,
            breaking_changes=request.breaking_changes,
            non_breaking_changes=[],
            risk_assessment="",
            recommendations=[],
            impact_prediction="",
            confidence=0.5,
        )
        
        recommendations = analyzer.generate_recommendations(
            analysis=analysis,
            brittleness_score=request.brittleness_score,
            qoe_risk_score=request.qoe_risk_score,
        )
        
        return RecommendationsResponse(
            recommendations=[
                {
                    "issue": r.issue,
                    "severity": r.severity,
                    "fix_type": r.fix_type,
                    "description": r.description,
                    "code_example": r.code_example,
                    "estimated_effort": r.estimated_effort,
                }
                for r in recommendations
            ]
        )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM libraries not installed",
        )


@router.post("/explain-for-stakeholder")
async def explain_for_stakeholder(
    analysis_summary: str = Body(...),
    breaking_changes: List[str] = Body(default=[]),
    risk_assessment: str = Body(default=""),
    audience: str = Body(default="technical"),  # technical, business, executive
):
    """
    Generate stakeholder-appropriate explanation.
    
    Tailors explanation for:
    - technical: Detailed, includes paths/types
    - business: User/revenue impact focus
    - executive: High-level summary
    """
    try:
        from qoe_guard.ai.llm_analyzer import LLMAnalyzer, DiffAnalysis
        
        analyzer = LLMAnalyzer()
        
        analysis = DiffAnalysis(
            summary=analysis_summary,
            breaking_changes=breaking_changes,
            non_breaking_changes=[],
            risk_assessment=risk_assessment,
            recommendations=[],
            impact_prediction="",
            confidence=0.5,
        )
        
        explanation = analyzer.explain_for_stakeholders(
            analysis=analysis,
            audience=audience,
        )
        
        return {"explanation": explanation, "audience": audience}
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM libraries not installed",
        )


@router.post("/batch-classify")
async def batch_classify_endpoints(
    endpoints: List[EndpointClassificationRequest] = Body(...),
):
    """
    Batch classify multiple endpoints.
    
    Efficiently classifies multiple endpoints in one request.
    """
    try:
        from qoe_guard.ai.nlp_analyzer import NLPAnalyzer
        
        analyzer = NLPAnalyzer()
        results = []
        
        for ep in endpoints:
            intent = analyzer.extract_intent(
                endpoint_path=ep.endpoint_path,
                method=ep.method,
                description=ep.description,
                summary=ep.summary,
            )
            
            criticality = analyzer.classify_criticality(
                endpoint_path=ep.endpoint_path,
                method=ep.method,
                description=ep.description,
                tags=ep.tags,
            )
            
            results.append({
                "endpoint": ep.endpoint_path,
                "method": ep.method,
                "intent": intent.primary_intent,
                "criticality": criticality.criticality_level,
                "qoe_impact": criticality.qoe_impact,
                "suggested_tags": criticality.suggested_tags,
            })
        
        return {"classifications": results, "total": len(results)}
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NLP libraries not installed",
        )
