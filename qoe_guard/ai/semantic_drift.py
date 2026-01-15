"""
Semantic Drift Detection for QoE-Guard.

Uses embedding models to detect semantic changes even when structure matches.
Examples:
- Field rename: "playback_url" → "manifest_url" (same meaning)
- Value semantic shift: "HD" → "1080p" (equivalent)
- Enum mapping: "PREMIUM" → "tier_3" (semantic equivalence)

Libraries:
- sentence-transformers: State-of-the-art embeddings
- numpy: Vector operations
"""
from __future__ import annotations

import os
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from functools import lru_cache


@dataclass
class SemanticMatch:
    """Result of semantic similarity check."""
    source_key: str
    source_value: Any
    target_key: str
    target_value: Any
    similarity: float
    match_type: str  # key_rename, value_equivalent, semantic_drift
    confidence: float


@dataclass
class SemanticDriftReport:
    """Complete semantic drift analysis."""
    total_comparisons: int
    high_similarity_matches: List[SemanticMatch]
    potential_renames: List[SemanticMatch]
    value_equivalences: List[SemanticMatch]
    semantic_drifts: List[SemanticMatch]
    summary: str


class SemanticDriftDetector:
    """
    Detect semantic drift in API responses using embeddings.
    
    Uses sentence-transformers for generating text embeddings and
    computing cosine similarity between field names and values.
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",  # Fast and effective
        similarity_threshold: float = 0.75,
        use_cache: bool = True,
    ):
        """
        Initialize semantic drift detector.
        
        Args:
            model_name: Sentence transformer model to use
            similarity_threshold: Minimum similarity for a match
            use_cache: Whether to cache embeddings
        """
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self.use_cache = use_cache
        self.model = None
        self._embedding_cache: Dict[str, List[float]] = {}
        
        self._init_model()
    
    def _init_model(self):
        """Initialize the embedding model."""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
        except ImportError:
            print("Warning: sentence-transformers not installed. Semantic drift detection disabled.")
            self.model = None
    
    @property
    def is_available(self) -> bool:
        """Check if model is available."""
        return self.model is not None
    
    def detect_drift(
        self,
        baseline: Dict[str, Any],
        candidate: Dict[str, Any],
        structural_changes: Optional[List[Dict[str, Any]]] = None,
    ) -> SemanticDriftReport:
        """
        Detect semantic drift between baseline and candidate.
        
        Args:
            baseline: Baseline JSON
            candidate: Candidate JSON
            structural_changes: Pre-computed structural changes
        
        Returns:
            SemanticDriftReport with all findings
        """
        if not self.is_available:
            return self._fallback_report()
        
        # Extract all keys and values
        baseline_items = self._extract_items(baseline, "")
        candidate_items = self._extract_items(candidate, "")
        
        # Find removed keys (potential renames)
        removed_keys = set(baseline_items.keys()) - set(candidate_items.keys())
        added_keys = set(candidate_items.keys()) - set(candidate_items.keys())
        
        matches = []
        
        # Check for potential key renames
        for removed in removed_keys:
            for added in added_keys:
                similarity = self._compute_similarity(removed, added)
                if similarity >= self.similarity_threshold:
                    matches.append(SemanticMatch(
                        source_key=removed,
                        source_value=baseline_items.get(removed),
                        target_key=added,
                        target_value=candidate_items.get(added),
                        similarity=similarity,
                        match_type="key_rename",
                        confidence=similarity,
                    ))
        
        # Check for value semantic equivalence
        common_keys = set(baseline_items.keys()) & set(candidate_items.keys())
        for key in common_keys:
            baseline_val = baseline_items[key]
            candidate_val = candidate_items[key]
            
            if baseline_val != candidate_val:
                # Different values - check semantic equivalence
                similarity = self._compute_value_similarity(baseline_val, candidate_val)
                if similarity >= self.similarity_threshold:
                    matches.append(SemanticMatch(
                        source_key=key,
                        source_value=baseline_val,
                        target_key=key,
                        target_value=candidate_val,
                        similarity=similarity,
                        match_type="value_equivalent",
                        confidence=similarity,
                    ))
                elif similarity >= 0.5:
                    matches.append(SemanticMatch(
                        source_key=key,
                        source_value=baseline_val,
                        target_key=key,
                        target_value=candidate_val,
                        similarity=similarity,
                        match_type="semantic_drift",
                        confidence=similarity,
                    ))
        
        # Categorize matches
        high_similarity = [m for m in matches if m.similarity >= 0.9]
        renames = [m for m in matches if m.match_type == "key_rename"]
        equivalences = [m for m in matches if m.match_type == "value_equivalent"]
        drifts = [m for m in matches if m.match_type == "semantic_drift"]
        
        return SemanticDriftReport(
            total_comparisons=len(matches),
            high_similarity_matches=high_similarity,
            potential_renames=renames,
            value_equivalences=equivalences,
            semantic_drifts=drifts,
            summary=self._generate_summary(matches),
        )
    
    def find_similar_fields(
        self,
        field_name: str,
        schema: Dict[str, Any],
        top_k: int = 5,
    ) -> List[Tuple[str, float]]:
        """
        Find fields in schema similar to given field name.
        
        Useful for detecting potential migrations/renames.
        """
        if not self.is_available:
            return []
        
        schema_fields = list(self._extract_items(schema, "").keys())
        
        similarities = []
        for schema_field in schema_fields:
            sim = self._compute_similarity(field_name, schema_field)
            similarities.append((schema_field, sim))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def compute_batch_similarity(
        self,
        texts1: List[str],
        texts2: List[str],
    ) -> List[List[float]]:
        """
        Compute pairwise similarity matrix for two lists of texts.
        
        Returns NxM matrix where N=len(texts1), M=len(texts2).
        """
        if not self.is_available:
            return [[0.0] * len(texts2) for _ in texts1]
        
        from sentence_transformers import util
        
        embeddings1 = self.model.encode(texts1)
        embeddings2 = self.model.encode(texts2)
        
        similarity_matrix = util.cos_sim(embeddings1, embeddings2)
        return similarity_matrix.tolist()
    
    def _extract_items(
        self,
        obj: Any,
        prefix: str,
    ) -> Dict[str, Any]:
        """Recursively extract all key-value pairs with paths."""
        items = {}
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                path = f"{prefix}.{key}" if prefix else key
                items[path] = value
                items.update(self._extract_items(value, path))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                path = f"{prefix}[{i}]"
                items.update(self._extract_items(item, path))
        
        return items
    
    def _compute_similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two texts."""
        if not self.is_available:
            return 0.0
        
        # Check cache
        cache_key = f"{text1}||{text2}"
        if self.use_cache and cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]
        
        from sentence_transformers import util
        
        embeddings = self.model.encode([text1, text2])
        similarity = float(util.cos_sim(embeddings[0], embeddings[1])[0][0])
        
        if self.use_cache:
            self._embedding_cache[cache_key] = similarity
        
        return similarity
    
    def _compute_value_similarity(self, val1: Any, val2: Any) -> float:
        """Compute similarity between two values."""
        # Convert to strings for embedding
        str1 = str(val1) if not isinstance(val1, str) else val1
        str2 = str(val2) if not isinstance(val2, str) else val2
        
        # Handle numeric comparisons
        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            # Normalize numeric difference
            max_val = max(abs(val1), abs(val2), 1)
            diff = abs(val1 - val2) / max_val
            return max(0, 1 - diff)
        
        # Handle boolean comparisons
        if isinstance(val1, bool) and isinstance(val2, bool):
            return 1.0 if val1 == val2 else 0.0
        
        # Use semantic similarity for strings
        return self._compute_similarity(str1, str2)
    
    def _generate_summary(self, matches: List[SemanticMatch]) -> str:
        """Generate human-readable summary."""
        if not matches:
            return "No significant semantic drift detected."
        
        renames = len([m for m in matches if m.match_type == "key_rename"])
        equivalences = len([m for m in matches if m.match_type == "value_equivalent"])
        drifts = len([m for m in matches if m.match_type == "semantic_drift"])
        
        parts = []
        if renames > 0:
            parts.append(f"{renames} potential field rename(s)")
        if equivalences > 0:
            parts.append(f"{equivalences} semantically equivalent value(s)")
        if drifts > 0:
            parts.append(f"{drifts} semantic drift(s) detected")
        
        return f"Found: {', '.join(parts)}."
    
    def _fallback_report(self) -> SemanticDriftReport:
        """Fallback when model unavailable."""
        return SemanticDriftReport(
            total_comparisons=0,
            high_similarity_matches=[],
            potential_renames=[],
            value_equivalences=[],
            semantic_drifts=[],
            summary="Semantic drift detection unavailable (install sentence-transformers).",
        )


# Convenience function
def detect_semantic_changes(
    baseline: Dict[str, Any],
    candidate: Dict[str, Any],
) -> SemanticDriftReport:
    """Quick function to detect semantic drift."""
    detector = SemanticDriftDetector()
    return detector.detect_drift(baseline, candidate)


# Domain-specific semantic mappings for streaming
STREAMING_EQUIVALENCES = {
    # Quality levels
    "HD": ["high_definition", "1080p", "720p", "hd"],
    "SD": ["standard_definition", "480p", "sd"],
    "4K": ["ultra_hd", "2160p", "uhd", "4k"],
    
    # Subscription tiers
    "premium": ["tier_3", "gold", "pro"],
    "basic": ["tier_1", "free", "starter"],
    "standard": ["tier_2", "silver", "plus"],
    
    # Playback states
    "playing": ["play", "started", "active"],
    "paused": ["pause", "stopped", "inactive"],
    "buffering": ["loading", "buffer", "waiting"],
    
    # Error states
    "error": ["failure", "failed", "err"],
    "success": ["ok", "passed", "completed"],
}


def check_domain_equivalence(val1: str, val2: str) -> Tuple[bool, float]:
    """
    Check if two values are domain-equivalent for streaming.
    
    Returns (is_equivalent, confidence).
    """
    val1_lower = val1.lower() if isinstance(val1, str) else str(val1).lower()
    val2_lower = val2.lower() if isinstance(val2, str) else str(val2).lower()
    
    for canonical, equivalents in STREAMING_EQUIVALENCES.items():
        all_terms = [canonical.lower()] + [e.lower() for e in equivalents]
        if val1_lower in all_terms and val2_lower in all_terms:
            return True, 0.95
    
    return False, 0.0
