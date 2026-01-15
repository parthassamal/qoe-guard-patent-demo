"""
Criticality Profiles Module.

Defines criticality scores for different API endpoints and JSON paths.
These profiles determine how much a change impacts QoE.
"""
from typing import Dict, List, Optional
import re


# Default criticality profiles for streaming services
DEFAULT_CRITICALITY_PROFILES: Dict[str, float] = {
    # Endpoint tags/categories
    "playback": 1.00,
    "drm": 0.95,
    "entitlement": 0.95,
    "manifest": 0.95,
    "license": 0.90,
    "ads": 0.85,
    "advertisement": 0.85,
    "auth": 0.80,
    "authentication": 0.80,
    "authorization": 0.80,
    "billing": 0.75,
    "subscription": 0.75,
    "user": 0.70,
    "profile": 0.60,
    "search": 0.55,
    "recommendation": 0.50,
    "metadata": 0.40,
    "catalog": 0.40,
    "analytics": 0.30,
    "telemetry": 0.25,
    "logging": 0.20,
    "health": 0.10,
    "status": 0.10,
    
    # Specific JSON paths (exact or pattern)
    "manifestUrl": 1.00,
    "manifest_url": 1.00,
    "playbackUrl": 1.00,
    "playback_url": 1.00,
    "licenseUrl": 1.00,
    "license_url": 1.00,
    "drmUrl": 0.95,
    "drm_url": 0.95,
    "allowed": 0.95,
    "entitled": 0.95,
    "granted": 0.95,
    "maxBitrate": 0.80,
    "max_bitrate": 0.80,
    "quality": 0.75,
    "resolution": 0.70,
    "adUrl": 0.85,
    "prerollUrl": 0.80,
    "accessToken": 0.90,
    "access_token": 0.90,
}

# Glob pattern to exact mapping
CRITICALITY_PATTERNS = [
    (r"\$\.playback\..*[Uu]rl$", 1.00),
    (r"\$\.drm\..*[Uu]rl$", 0.95),
    (r"\$\.entitlement\.(allowed|granted)", 0.95),
    (r"\$\.ads\.", 0.85),
    (r"\$\.auth\.", 0.80),
    (r"\$\.analytics\.", 0.30),
    (r"\$\.metadata\.", 0.40),
]


def get_criticality_for_path(
    path: str,
    profiles: Optional[Dict[str, float]] = None
) -> float:
    """
    Get criticality score for a JSON path.
    
    Args:
        path: JSON path (e.g., "$.playback.manifestUrl")
        profiles: Optional custom criticality profiles
        
    Returns:
        Criticality score from 0.0 to 1.0
    """
    p = profiles or DEFAULT_CRITICALITY_PROFILES
    
    # Extract the last segment of the path
    path_parts = path.replace("$.", "").replace("$", "").split(".")
    
    # Check exact matches first
    for part in reversed(path_parts):
        # Remove array indices
        clean_part = re.sub(r'\[\d+\]', '', part)
        if clean_part in p:
            return p[clean_part]
    
    # Check category matches
    if path_parts:
        first_segment = path_parts[0].lower()
        for key, score in p.items():
            if key.lower() == first_segment:
                return score
    
    # Check patterns
    for pattern, score in CRITICALITY_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            return score
    
    # Check if any part of path contains critical keywords
    path_lower = path.lower()
    critical_keywords = [
        ("playback", 0.90),
        ("drm", 0.85),
        ("license", 0.85),
        ("entitle", 0.85),
        ("manifest", 0.85),
        ("auth", 0.70),
        ("ads", 0.70),
        ("billing", 0.65),
    ]
    
    for keyword, score in critical_keywords:
        if keyword in path_lower:
            return score
    
    # Default: medium-low criticality
    return 0.35


def get_criticality_for_tags(
    tags: List[str],
    profiles: Optional[Dict[str, float]] = None
) -> float:
    """
    Get highest criticality score for a list of endpoint tags.
    
    Args:
        tags: List of endpoint tags
        profiles: Optional custom criticality profiles
        
    Returns:
        Highest criticality score from tags
    """
    if not tags:
        return 0.35
    
    p = profiles or DEFAULT_CRITICALITY_PROFILES
    
    max_score = 0.0
    for tag in tags:
        tag_lower = tag.lower()
        for key, score in p.items():
            if key.lower() == tag_lower:
                max_score = max(max_score, score)
                break
        else:
            # Check partial matches
            for keyword, score in [
                ("playback", 0.90),
                ("drm", 0.85),
                ("entitle", 0.85),
                ("auth", 0.70),
            ]:
                if keyword in tag_lower:
                    max_score = max(max_score, score)
    
    return max_score if max_score > 0 else 0.35


def calculate_criticality_weighted_changes(
    changed_paths: List[str],
    profiles: Optional[Dict[str, float]] = None
) -> float:
    """
    Calculate the sum of criticality-weighted changes.
    
    Args:
        changed_paths: List of JSON paths that changed
        profiles: Optional custom criticality profiles
        
    Returns:
        Sum of criticality scores for all changed paths
    """
    total = 0.0
    for path in changed_paths:
        total += get_criticality_for_path(path, profiles)
    return total
