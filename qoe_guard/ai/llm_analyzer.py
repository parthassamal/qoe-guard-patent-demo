"""
LLM-Powered Analysis for QoE-Guard.

Supports multiple providers:
- Groq (fastest inference, Llama/Mixtral)
- OpenAI (GPT-4)
- Anthropic (Claude)

Provides:
- Intelligent diff analysis and explanations
- Auto-generated fix recommendations
- Breaking change classification
- Impact prediction
"""
from __future__ import annotations

import os
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class LLMProvider(Enum):
    """Supported LLM providers."""
    GROQ = "groq"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""
    provider: LLMProvider
    api_key: str
    model: str
    temperature: float = 0.1
    max_tokens: int = 2000


@dataclass
class DiffAnalysis:
    """Result of LLM diff analysis."""
    summary: str
    breaking_changes: List[str]
    non_breaking_changes: List[str]
    risk_assessment: str
    recommendations: List[str]
    impact_prediction: str
    confidence: float


@dataclass
class FixRecommendation:
    """A recommended fix for an API issue."""
    issue: str
    severity: str  # critical, high, medium, low
    fix_type: str  # code, config, documentation, rollback
    description: str
    code_example: Optional[str] = None
    estimated_effort: str = "unknown"


# Default models for each provider
DEFAULT_MODELS = {
    LLMProvider.GROQ: "llama-3.1-70b-versatile",  # Fast and capable
    LLMProvider.OPENAI: "gpt-4-turbo-preview",
    LLMProvider.ANTHROPIC: "claude-3-sonnet-20240229",
}


class LLMAnalyzer:
    """
    LLM-powered analyzer for API changes.
    
    Uses Groq by default for fastest inference, with fallback to OpenAI/Anthropic.
    """
    
    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize LLM analyzer.
        
        Auto-detects available provider from environment if not specified.
        Priority: Groq > OpenAI > Anthropic
        """
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.client = None
        
        # Auto-detect provider
        if not self.provider:
            self._auto_detect_provider()
        
        # Initialize client
        if self.provider:
            self._init_client()
    
    def _auto_detect_provider(self):
        """Auto-detect available LLM provider from environment."""
        if os.getenv("GROQ_API_KEY"):
            self.provider = LLMProvider.GROQ
            self.api_key = os.getenv("GROQ_API_KEY")
        elif os.getenv("OPENAI_API_KEY"):
            self.provider = LLMProvider.OPENAI
            self.api_key = os.getenv("OPENAI_API_KEY")
        elif os.getenv("ANTHROPIC_API_KEY"):
            self.provider = LLMProvider.ANTHROPIC
            self.api_key = os.getenv("ANTHROPIC_API_KEY")
    
    def _init_client(self):
        """Initialize the appropriate client."""
        if not self.model:
            self.model = DEFAULT_MODELS.get(self.provider)
        
        try:
            if self.provider == LLMProvider.GROQ:
                from groq import Groq
                self.client = Groq(api_key=self.api_key)
            elif self.provider == LLMProvider.OPENAI:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            elif self.provider == LLMProvider.ANTHROPIC:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError as e:
            print(f"Warning: Could not import {self.provider.value} client: {e}")
            self.client = None
    
    @property
    def is_available(self) -> bool:
        """Check if LLM is available."""
        return self.client is not None
    
    def analyze_diff(
        self,
        baseline: Dict[str, Any],
        candidate: Dict[str, Any],
        changes: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> DiffAnalysis:
        """
        Analyze API diff using LLM.
        
        Args:
            baseline: Baseline JSON response
            candidate: Candidate JSON response
            changes: List of detected changes
            context: Optional context (endpoint info, criticality, etc.)
        
        Returns:
            DiffAnalysis with intelligent insights
        """
        if not self.is_available:
            return self._fallback_analysis(changes)
        
        prompt = self._build_analysis_prompt(baseline, candidate, changes, context)
        
        try:
            response = self._call_llm(prompt)
            return self._parse_analysis_response(response)
        except Exception as e:
            print(f"LLM analysis failed: {e}")
            return self._fallback_analysis(changes)
    
    def generate_recommendations(
        self,
        analysis: DiffAnalysis,
        brittleness_score: float,
        qoe_risk_score: float,
    ) -> List[FixRecommendation]:
        """
        Generate fix recommendations based on analysis.
        
        Args:
            analysis: Previous diff analysis
            brittleness_score: Brittleness score (0-100)
            qoe_risk_score: QoE risk score (0-1)
        
        Returns:
            List of prioritized fix recommendations
        """
        if not self.is_available:
            return self._fallback_recommendations(analysis)
        
        prompt = self._build_recommendation_prompt(analysis, brittleness_score, qoe_risk_score)
        
        try:
            response = self._call_llm(prompt)
            return self._parse_recommendations_response(response)
        except Exception as e:
            print(f"LLM recommendations failed: {e}")
            return self._fallback_recommendations(analysis)
    
    def explain_for_stakeholders(
        self,
        analysis: DiffAnalysis,
        audience: str = "technical",  # technical, business, executive
    ) -> str:
        """
        Generate human-readable explanation for different audiences.
        
        Args:
            analysis: Diff analysis
            audience: Target audience type
        
        Returns:
            Tailored explanation string
        """
        if not self.is_available:
            return analysis.summary
        
        prompt = f"""
        Given this API change analysis:
        
        Summary: {analysis.summary}
        Breaking Changes: {json.dumps(analysis.breaking_changes)}
        Risk Assessment: {analysis.risk_assessment}
        
        Generate a {audience}-friendly explanation that:
        - Uses appropriate terminology for {audience} audience
        - Highlights the most important points
        - Is concise (2-3 paragraphs max)
        - Includes actionable next steps
        
        Audience guidelines:
        - technical: Use technical terms, include specific paths/types
        - business: Focus on user/revenue impact, avoid jargon
        - executive: High-level summary, risk/opportunity focus
        """
        
        try:
            return self._call_llm(prompt)
        except Exception:
            return analysis.summary
    
    def classify_breaking_change(
        self,
        change: Dict[str, Any],
        schema_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Classify if a specific change is breaking.
        
        Returns detailed classification with reasoning.
        """
        if not self.is_available:
            return {"is_breaking": change.get("change_type") in ["removed", "type_changed"]}
        
        prompt = f"""
        Analyze this API change and determine if it's a breaking change:
        
        Change: {json.dumps(change)}
        Schema Context: {json.dumps(schema_context) if schema_context else "Not provided"}
        
        Respond in JSON format:
        {{
            "is_breaking": true/false,
            "confidence": 0.0-1.0,
            "reasoning": "explanation",
            "affected_clients": ["list of client types that might be affected"],
            "mitigation": "suggested mitigation if breaking"
        }}
        """
        
        try:
            response = self._call_llm(prompt)
            return json.loads(response)
        except Exception:
            return {"is_breaking": change.get("change_type") in ["removed", "type_changed"]}
    
    def _call_llm(self, prompt: str) -> str:
        """Call the LLM with the given prompt."""
        if self.provider == LLMProvider.GROQ:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert API analyst specializing in streaming services, QoE (Quality of Experience), and API contract testing. Provide precise, actionable insights."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=2000,
            )
            return response.choices[0].message.content
        
        elif self.provider == LLMProvider.OPENAI:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert API analyst specializing in streaming services, QoE (Quality of Experience), and API contract testing. Provide precise, actionable insights."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=2000,
            )
            return response.choices[0].message.content
        
        elif self.provider == LLMProvider.ANTHROPIC:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt},
                ],
            )
            return response.content[0].text
        
        raise ValueError(f"Unknown provider: {self.provider}")
    
    def _build_analysis_prompt(
        self,
        baseline: Dict[str, Any],
        candidate: Dict[str, Any],
        changes: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
    ) -> str:
        """Build prompt for diff analysis."""
        return f"""
        Analyze these API response changes for a streaming service:
        
        ## Changes Detected
        {json.dumps(changes, indent=2)}
        
        ## Context
        {json.dumps(context, indent=2) if context else "No additional context"}
        
        ## Baseline Response (truncated)
        {json.dumps(baseline, indent=2)[:2000]}
        
        ## Candidate Response (truncated)
        {json.dumps(candidate, indent=2)[:2000]}
        
        Provide analysis in JSON format:
        {{
            "summary": "1-2 sentence summary",
            "breaking_changes": ["list of breaking changes with paths"],
            "non_breaking_changes": ["list of non-breaking changes"],
            "risk_assessment": "low/medium/high/critical with explanation",
            "recommendations": ["prioritized list of recommendations"],
            "impact_prediction": "predicted user/business impact",
            "confidence": 0.0-1.0
        }}
        
        Focus on QoE-critical paths: playback, DRM, entitlements, ads.
        """
    
    def _build_recommendation_prompt(
        self,
        analysis: DiffAnalysis,
        brittleness_score: float,
        qoe_risk_score: float,
    ) -> str:
        """Build prompt for fix recommendations."""
        return f"""
        Generate fix recommendations for these API issues:
        
        ## Analysis Summary
        {analysis.summary}
        
        ## Breaking Changes
        {json.dumps(analysis.breaking_changes)}
        
        ## Scores
        - Brittleness Score: {brittleness_score}/100
        - QoE Risk Score: {qoe_risk_score}
        
        Provide recommendations in JSON format:
        {{
            "recommendations": [
                {{
                    "issue": "specific issue",
                    "severity": "critical/high/medium/low",
                    "fix_type": "code/config/documentation/rollback",
                    "description": "what to do",
                    "code_example": "optional code snippet",
                    "estimated_effort": "hours/days/weeks"
                }}
            ]
        }}
        
        Prioritize by: 1) User impact, 2) Revenue impact, 3) Ease of fix
        """
    
    def _parse_analysis_response(self, response: str) -> DiffAnalysis:
        """Parse LLM response into DiffAnalysis."""
        try:
            # Extract JSON from response
            start = response.find("{")
            end = response.rfind("}") + 1
            data = json.loads(response[start:end])
            
            return DiffAnalysis(
                summary=data.get("summary", "Analysis complete"),
                breaking_changes=data.get("breaking_changes", []),
                non_breaking_changes=data.get("non_breaking_changes", []),
                risk_assessment=data.get("risk_assessment", "unknown"),
                recommendations=data.get("recommendations", []),
                impact_prediction=data.get("impact_prediction", "unknown"),
                confidence=data.get("confidence", 0.5),
            )
        except Exception:
            return DiffAnalysis(
                summary=response[:500],
                breaking_changes=[],
                non_breaking_changes=[],
                risk_assessment="unknown",
                recommendations=[],
                impact_prediction="unknown",
                confidence=0.3,
            )
    
    def _parse_recommendations_response(self, response: str) -> List[FixRecommendation]:
        """Parse LLM response into recommendations."""
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            data = json.loads(response[start:end])
            
            return [
                FixRecommendation(
                    issue=r.get("issue", "Unknown issue"),
                    severity=r.get("severity", "medium"),
                    fix_type=r.get("fix_type", "code"),
                    description=r.get("description", ""),
                    code_example=r.get("code_example"),
                    estimated_effort=r.get("estimated_effort", "unknown"),
                )
                for r in data.get("recommendations", [])
            ]
        except Exception:
            return []
    
    def _fallback_analysis(self, changes: List[Dict[str, Any]]) -> DiffAnalysis:
        """Fallback analysis when LLM is unavailable."""
        breaking = [c for c in changes if c.get("change_type") in ["removed", "type_changed"]]
        non_breaking = [c for c in changes if c.get("change_type") not in ["removed", "type_changed"]]
        
        return DiffAnalysis(
            summary=f"Detected {len(changes)} changes ({len(breaking)} potentially breaking)",
            breaking_changes=[f"{c.get('path')}: {c.get('change_type')}" for c in breaking],
            non_breaking_changes=[f"{c.get('path')}: {c.get('change_type')}" for c in non_breaking],
            risk_assessment="high" if len(breaking) > 0 else "medium" if len(changes) > 5 else "low",
            recommendations=["Review breaking changes before deployment", "Update client SDKs"],
            impact_prediction="Potential client breakage" if breaking else "Minor changes",
            confidence=0.5,
        )
    
    def _fallback_recommendations(self, analysis: DiffAnalysis) -> List[FixRecommendation]:
        """Fallback recommendations when LLM is unavailable."""
        recs = []
        
        if analysis.breaking_changes:
            recs.append(FixRecommendation(
                issue="Breaking changes detected",
                severity="high",
                fix_type="code",
                description="Review and fix breaking changes before deployment",
                estimated_effort="1-2 days",
            ))
        
        if "high" in analysis.risk_assessment.lower() or "critical" in analysis.risk_assessment.lower():
            recs.append(FixRecommendation(
                issue="High risk assessment",
                severity="high",
                fix_type="rollback",
                description="Consider rolling back changes and implementing incrementally",
                estimated_effort="hours",
            ))
        
        return recs


# Convenience functions
def analyze_diff_with_llm(
    baseline: Dict[str, Any],
    candidate: Dict[str, Any],
    changes: List[Dict[str, Any]],
) -> DiffAnalysis:
    """Quick function to analyze diff with auto-detected LLM."""
    analyzer = LLMAnalyzer()
    return analyzer.analyze_diff(baseline, candidate, changes)


def generate_recommendations(
    analysis: DiffAnalysis,
    brittleness_score: float = 50.0,
    qoe_risk_score: float = 0.5,
) -> List[FixRecommendation]:
    """Quick function to generate recommendations."""
    analyzer = LLMAnalyzer()
    return analyzer.generate_recommendations(analysis, brittleness_score, qoe_risk_score)
