"""
NLP Analysis for QoE-Guard.

Analyzes API documentation and descriptions using NLP:
- Extract intent and business logic from descriptions
- Auto-classify endpoints by purpose/criticality
- Detect documentation drift
- Extract keywords and entities

Libraries:
- spacy: NLP pipeline
- transformers: Zero-shot classification
- keybert: Keyword extraction
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict


@dataclass
class EndpointIntent:
    """Extracted intent from endpoint description."""
    primary_intent: str
    confidence: float
    secondary_intents: List[Tuple[str, float]]
    extracted_entities: Dict[str, List[str]]
    business_domain: str
    keywords: List[str]


@dataclass
class CriticalityClassification:
    """Classification of endpoint criticality."""
    criticality_level: str  # critical, high, medium, low
    score: float  # 0-1
    reasons: List[str]
    qoe_impact: str
    suggested_tags: List[str]


@dataclass
class DocumentationQuality:
    """Assessment of API documentation quality."""
    overall_score: float  # 0-1
    completeness: float
    clarity: float
    consistency: float
    issues: List[str]
    suggestions: List[str]


# Intent categories for streaming APIs
STREAMING_INTENTS = {
    "playback": ["play", "stream", "manifest", "video", "audio", "watch", "content"],
    "authentication": ["auth", "login", "token", "session", "credential", "oauth"],
    "entitlement": ["entitle", "subscription", "access", "permission", "license", "drm"],
    "metadata": ["info", "detail", "catalog", "search", "recommend", "browse"],
    "analytics": ["track", "event", "metric", "log", "telemetry", "beacon"],
    "ads": ["ad", "advertisement", "commercial", "sponsor", "vast", "vmap"],
    "user": ["profile", "preference", "setting", "account", "history"],
    "payment": ["pay", "billing", "purchase", "subscribe", "transaction"],
}

# Criticality keywords
CRITICAL_KEYWORDS = {
    "critical": ["playback", "manifest", "license", "drm", "entitlement", "stream", "video"],
    "high": ["auth", "token", "session", "payment", "subscription", "access"],
    "medium": ["metadata", "profile", "search", "catalog", "recommendation"],
    "low": ["analytics", "tracking", "log", "beacon", "preference"],
}


class NLPAnalyzer:
    """
    NLP-based analyzer for API documentation.
    
    Uses spaCy for NLP and transformers for zero-shot classification.
    """
    
    def __init__(
        self,
        spacy_model: str = "en_core_web_sm",
        use_transformers: bool = True,
    ):
        """
        Initialize NLP analyzer.
        
        Args:
            spacy_model: spaCy model to use
            use_transformers: Whether to use transformers for classification
        """
        self.spacy_model = spacy_model
        self.use_transformers = use_transformers
        self.nlp = None
        self.classifier = None
        self.keyword_extractor = None
        
        self._init_models()
    
    def _init_models(self):
        """Initialize NLP models."""
        # Try spaCy
        try:
            import spacy
            try:
                self.nlp = spacy.load(self.spacy_model)
            except OSError:
                # Model not installed, try downloading
                print(f"Downloading spaCy model {self.spacy_model}...")
                spacy.cli.download(self.spacy_model)
                self.nlp = spacy.load(self.spacy_model)
        except ImportError:
            print("Warning: spaCy not installed. Some NLP features disabled.")
        
        # Try transformers for zero-shot classification
        if self.use_transformers:
            try:
                from transformers import pipeline
                self.classifier = pipeline(
                    "zero-shot-classification",
                    model="facebook/bart-large-mnli",
                )
            except ImportError:
                print("Warning: transformers not installed. Zero-shot classification disabled.")
            except Exception as e:
                print(f"Warning: Could not load classifier: {e}")
        
        # Try KeyBERT
        try:
            from keybert import KeyBERT
            self.keyword_extractor = KeyBERT()
        except ImportError:
            print("Warning: keybert not installed. Keyword extraction uses fallback.")
    
    @property
    def is_available(self) -> bool:
        """Check if basic NLP is available."""
        return self.nlp is not None
    
    def extract_intent(
        self,
        endpoint_path: str,
        method: str,
        description: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> EndpointIntent:
        """
        Extract intent from endpoint information.
        
        Args:
            endpoint_path: API path (e.g., /api/v1/playback/manifest)
            method: HTTP method
            description: Optional description
            summary: Optional summary
        
        Returns:
            EndpointIntent with analysis
        """
        text = " ".join(filter(None, [endpoint_path, description, summary]))
        text = text.lower()
        
        # Rule-based intent detection
        intent_scores = self._compute_intent_scores(text)
        
        # Use zero-shot if available
        if self.classifier and description:
            try:
                labels = list(STREAMING_INTENTS.keys())
                result = self.classifier(description, labels)
                for label, score in zip(result["labels"], result["scores"]):
                    intent_scores[label] = max(intent_scores.get(label, 0), score)
            except Exception:
                pass
        
        # Sort by score
        sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_intents[0] if sorted_intents else ("unknown", 0.0)
        secondary = sorted_intents[1:4] if len(sorted_intents) > 1 else []
        
        # Extract entities
        entities = self._extract_entities(text)
        
        # Extract keywords
        keywords = self._extract_keywords(text)
        
        # Determine business domain
        domain = self._classify_domain(primary[0])
        
        return EndpointIntent(
            primary_intent=primary[0],
            confidence=primary[1],
            secondary_intents=secondary,
            extracted_entities=entities,
            business_domain=domain,
            keywords=keywords,
        )
    
    def classify_criticality(
        self,
        endpoint_path: str,
        method: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> CriticalityClassification:
        """
        Classify endpoint criticality for QoE.
        
        Args:
            endpoint_path: API path
            method: HTTP method
            description: Optional description
            tags: Optional OpenAPI tags
        
        Returns:
            CriticalityClassification with analysis
        """
        text = " ".join(filter(None, [endpoint_path, description] + (tags or [])))
        text = text.lower()
        
        # Score for each criticality level
        level_scores = {level: 0.0 for level in CRITICAL_KEYWORDS}
        reasons = []
        
        for level, keywords in CRITICAL_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    level_scores[level] += 0.3
                    reasons.append(f"Contains '{keyword}' -> {level}")
        
        # Method-based adjustments
        if method.upper() in ["POST", "PUT", "DELETE", "PATCH"]:
            level_scores["high"] += 0.1
            reasons.append(f"{method} method indicates state change")
        
        # Path-based adjustments
        if "/internal" in endpoint_path or "/admin" in endpoint_path:
            level_scores["critical"] += 0.2
            reasons.append("Internal/admin endpoint")
        
        # Determine level
        max_level = max(level_scores, key=level_scores.get)
        max_score = min(1.0, level_scores[max_level])
        
        # QoE impact description
        qoe_impact = self._describe_qoe_impact(max_level)
        
        # Suggest tags
        suggested_tags = self._suggest_tags(text)
        
        return CriticalityClassification(
            criticality_level=max_level,
            score=max_score,
            reasons=reasons[:5],  # Top 5 reasons
            qoe_impact=qoe_impact,
            suggested_tags=suggested_tags,
        )
    
    def assess_documentation(
        self,
        operations: List[Dict[str, Any]],
    ) -> DocumentationQuality:
        """
        Assess quality of API documentation.
        
        Args:
            operations: List of OpenAPI operations
        
        Returns:
            DocumentationQuality assessment
        """
        issues = []
        suggestions = []
        
        total_ops = len(operations)
        if total_ops == 0:
            return DocumentationQuality(
                overall_score=0.0,
                completeness=0.0,
                clarity=0.0,
                consistency=0.0,
                issues=["No operations found"],
                suggestions=["Add API operations"],
            )
        
        # Check completeness
        with_description = sum(1 for op in operations if op.get("description"))
        with_summary = sum(1 for op in operations if op.get("summary"))
        with_tags = sum(1 for op in operations if op.get("tags"))
        with_responses = sum(1 for op in operations if op.get("responses"))
        
        completeness = (
            (with_description / total_ops) * 0.3 +
            (with_summary / total_ops) * 0.2 +
            (with_tags / total_ops) * 0.2 +
            (with_responses / total_ops) * 0.3
        )
        
        if with_description < total_ops:
            issues.append(f"{total_ops - with_description} operations missing descriptions")
            suggestions.append("Add descriptions to all operations")
        
        if with_summary < total_ops:
            issues.append(f"{total_ops - with_summary} operations missing summaries")
        
        # Check clarity (description length, readability)
        description_lengths = [
            len(op.get("description", "")) for op in operations if op.get("description")
        ]
        avg_length = sum(description_lengths) / len(description_lengths) if description_lengths else 0
        
        clarity = min(1.0, avg_length / 200)  # Ideal: 200+ chars
        
        if avg_length < 50:
            issues.append("Descriptions are too short")
            suggestions.append("Expand descriptions with more detail")
        
        # Check consistency (naming conventions)
        operation_ids = [op.get("operationId", "") for op in operations]
        consistency = self._check_consistency(operation_ids)
        
        if consistency < 0.7:
            issues.append("Inconsistent naming conventions")
            suggestions.append("Standardize operationId naming (e.g., getUsers, createUser)")
        
        overall = (completeness * 0.4 + clarity * 0.3 + consistency * 0.3)
        
        return DocumentationQuality(
            overall_score=overall,
            completeness=completeness,
            clarity=clarity,
            consistency=consistency,
            issues=issues,
            suggestions=suggestions,
        )
    
    def _compute_intent_scores(self, text: str) -> Dict[str, float]:
        """Compute intent scores using keyword matching."""
        scores = defaultdict(float)
        
        for intent, keywords in STREAMING_INTENTS.items():
            for keyword in keywords:
                if keyword in text:
                    scores[intent] += 0.25
        
        # Normalize
        max_score = max(scores.values()) if scores else 1
        return {k: min(1.0, v / max_score) for k, v in scores.items()}
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities from text."""
        entities: Dict[str, List[str]] = defaultdict(list)
        
        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                entities[ent.label_].append(ent.text)
        
        # Custom entity extraction for API-specific patterns
        # Extract path parameters
        path_params = re.findall(r"\{(\w+)\}", text)
        if path_params:
            entities["PATH_PARAM"] = path_params
        
        # Extract version numbers
        versions = re.findall(r"v\d+", text)
        if versions:
            entities["VERSION"] = versions
        
        return dict(entities)
    
    def _extract_keywords(self, text: str, top_k: int = 5) -> List[str]:
        """Extract keywords from text."""
        if self.keyword_extractor:
            try:
                keywords = self.keyword_extractor.extract_keywords(
                    text,
                    keyphrase_ngram_range=(1, 2),
                    stop_words="english",
                    top_n=top_k,
                )
                return [kw[0] for kw in keywords]
            except Exception:
                pass
        
        # Fallback: simple word frequency
        words = re.findall(r"\b\w{3,}\b", text.lower())
        stop_words = {"the", "and", "for", "with", "this", "that", "from", "are", "was"}
        words = [w for w in words if w not in stop_words]
        
        freq = defaultdict(int)
        for w in words:
            freq[w] += 1
        
        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [w[0] for w in sorted_words[:top_k]]
    
    def _classify_domain(self, intent: str) -> str:
        """Classify business domain from intent."""
        domain_map = {
            "playback": "content_delivery",
            "authentication": "identity",
            "entitlement": "access_control",
            "metadata": "content_catalog",
            "analytics": "telemetry",
            "ads": "monetization",
            "user": "user_management",
            "payment": "commerce",
        }
        return domain_map.get(intent, "general")
    
    def _describe_qoe_impact(self, level: str) -> str:
        """Describe QoE impact for criticality level."""
        impacts = {
            "critical": "Direct impact on playback. Failure causes immediate service disruption.",
            "high": "Significant user experience impact. May prevent content access.",
            "medium": "Moderate impact on features. Core playback unaffected.",
            "low": "Minimal user impact. Background functionality only.",
        }
        return impacts.get(level, "Unknown impact")
    
    def _suggest_tags(self, text: str) -> List[str]:
        """Suggest OpenAPI tags based on text analysis."""
        tags = []
        
        for intent, keywords in STREAMING_INTENTS.items():
            if any(kw in text for kw in keywords):
                tags.append(intent)
        
        return tags[:3]  # Max 3 tags
    
    def _check_consistency(self, operation_ids: List[str]) -> float:
        """Check naming consistency of operation IDs."""
        if not operation_ids:
            return 1.0
        
        # Check for common patterns
        patterns = {
            "camelCase": re.compile(r"^[a-z]+[A-Z]"),
            "snake_case": re.compile(r"^[a-z]+_[a-z]"),
            "kebab-case": re.compile(r"^[a-z]+-[a-z]"),
        }
        
        pattern_counts = defaultdict(int)
        for op_id in operation_ids:
            for pattern_name, pattern in patterns.items():
                if pattern.search(op_id):
                    pattern_counts[pattern_name] += 1
                    break
            else:
                pattern_counts["other"] += 1
        
        # Consistency = most common pattern / total
        if not pattern_counts:
            return 0.5
        
        most_common = max(pattern_counts.values())
        return most_common / len(operation_ids)


# Convenience functions
def extract_api_intent(
    endpoint_path: str,
    method: str,
    description: Optional[str] = None,
) -> EndpointIntent:
    """Quick function to extract endpoint intent."""
    analyzer = NLPAnalyzer()
    return analyzer.extract_intent(endpoint_path, method, description)


def classify_endpoint_criticality(
    endpoint_path: str,
    method: str,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> CriticalityClassification:
    """Quick function to classify endpoint criticality."""
    analyzer = NLPAnalyzer()
    return analyzer.classify_criticality(endpoint_path, method, description, tags)
