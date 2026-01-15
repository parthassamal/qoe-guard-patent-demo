"""
Criticality Profiles for QoE-Aware Scoring.

Defines default criticality weights for:
- Endpoint tags (playback, entitlement, ads, drm, etc.)
- JSON paths (manifest URLs, license URLs, etc.)
"""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


# Default criticality weights for endpoint tags
DEFAULT_TAG_CRITICALITY = {
    "playback": 1.0,
    "entitlement": 0.95,
    "drm": 0.95,
    "license": 0.95,
    "ads": 0.85,
    "advertising": 0.85,
    "auth": 0.80,
    "authentication": 0.80,
    "session": 0.75,
    "user": 0.60,
    "profile": 0.50,
    "metadata": 0.40,
    "search": 0.35,
    "analytics": 0.30,
    "logging": 0.20,
    "health": 0.10,
}

# Default criticality weights for JSON paths (glob patterns)
DEFAULT_PATH_CRITICALITY = {
    "$.playback.manifestUrl": 1.0,
    "$.playback.manifest*": 0.95,
    "$.drm.licenseUrl": 1.0,
    "$.drm.license*": 0.95,
    "$.drm.*": 0.90,
    "$.entitlement.allowed": 0.95,
    "$.entitlement.*": 0.85,
    "$.ads.adDecision": 0.85,
    "$.ads.adDecision.*": 0.80,
    "$.ads.*": 0.75,
    "$.playback.maxBitrateKbps": 0.70,
    "$.playback.startPositionSec": 0.65,
    "$.playback.*": 0.60,
    "$.session.*": 0.55,
    "$.metadata.*": 0.30,
    "$.analytics.*": 0.20,
}


@dataclass
class CriticalityProfiles:
    """Criticality profile configuration."""
    tag_weights: Dict[str, float] = field(default_factory=lambda: DEFAULT_TAG_CRITICALITY.copy())
    path_weights: Dict[str, float] = field(default_factory=lambda: DEFAULT_PATH_CRITICALITY.copy())
    default_weight: float = 0.5


# Global default profiles
DEFAULT_CRITICALITY_PROFILES = CriticalityProfiles()


def get_criticality_weight(
    profiles: CriticalityProfiles,
    tags: Optional[List[str]] = None,
    json_path: Optional[str] = None,
) -> float:
    """
    Get the criticality weight for a tag or JSON path.
    
    Args:
        profiles: Criticality profiles to use
        tags: List of endpoint tags
        json_path: JSON path (e.g., "$.playback.manifestUrl")
    
    Returns:
        Criticality weight (0.0 - 1.0)
    """
    max_weight = profiles.default_weight
    
    # Check tags
    if tags:
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower in profiles.tag_weights:
                max_weight = max(max_weight, profiles.tag_weights[tag_lower])
            else:
                # Partial match
                for key, weight in profiles.tag_weights.items():
                    if key in tag_lower or tag_lower in key:
                        max_weight = max(max_weight, weight * 0.8)
    
    # Check JSON path
    if json_path:
        for pattern, weight in profiles.path_weights.items():
            if _path_matches(json_path, pattern):
                max_weight = max(max_weight, weight)
    
    return max_weight


def get_path_criticality(
    profiles: CriticalityProfiles,
    json_path: str,
) -> float:
    """
    Get criticality weight for a specific JSON path.
    
    Args:
        profiles: Criticality profiles to use
        json_path: JSON path (e.g., "$.playback.manifestUrl")
    
    Returns:
        Criticality weight (0.0 - 1.0)
    """
    # Direct match first
    if json_path in profiles.path_weights:
        return profiles.path_weights[json_path]
    
    # Pattern matching
    best_match = profiles.default_weight
    best_specificity = 0
    
    for pattern, weight in profiles.path_weights.items():
        if _path_matches(json_path, pattern):
            # Prefer more specific patterns
            specificity = len(pattern.replace("*", ""))
            if specificity > best_specificity:
                best_specificity = specificity
                best_match = weight
    
    return best_match


def _path_matches(path: str, pattern: str) -> bool:
    """
    Check if a JSON path matches a glob pattern.
    
    Supports:
    - Exact match: $.playback.manifestUrl
    - Wildcard suffix: $.playback.*
    - Wildcard within: $.playback.manifest*
    """
    # Simple glob matching
    if "*" in pattern:
        # Convert to fnmatch pattern
        return fnmatch.fnmatch(path, pattern)
    else:
        return path == pattern


def is_critical_path(
    json_path: str,
    profiles: Optional[CriticalityProfiles] = None,
    threshold: float = 0.7,
) -> bool:
    """
    Check if a JSON path is considered critical.
    
    Args:
        json_path: JSON path to check
        profiles: Criticality profiles (uses default if None)
        threshold: Criticality threshold for "critical" classification
    
    Returns:
        True if path criticality >= threshold
    """
    if profiles is None:
        profiles = DEFAULT_CRITICALITY_PROFILES
    
    return get_path_criticality(profiles, json_path) >= threshold


def get_critical_paths(
    profiles: Optional[CriticalityProfiles] = None,
    threshold: float = 0.7,
) -> List[str]:
    """
    Get all path patterns that are considered critical.
    
    Args:
        profiles: Criticality profiles (uses default if None)
        threshold: Criticality threshold
    
    Returns:
        List of critical path patterns
    """
    if profiles is None:
        profiles = DEFAULT_CRITICALITY_PROFILES
    
    return [
        path for path, weight in profiles.path_weights.items()
        if weight >= threshold
    ]


def get_tag_criticality(
    tag: str,
    profiles: Optional[CriticalityProfiles] = None,
) -> float:
    """
    Get criticality weight for a tag.
    
    Args:
        tag: Tag name
        profiles: Criticality profiles (uses default if None)
    
    Returns:
        Criticality weight (0.0 - 1.0)
    """
    if profiles is None:
        profiles = DEFAULT_CRITICALITY_PROFILES
    
    tag_lower = tag.lower()
    
    if tag_lower in profiles.tag_weights:
        return profiles.tag_weights[tag_lower]
    
    # Partial match
    for key, weight in profiles.tag_weights.items():
        if key in tag_lower or tag_lower in key:
            return weight * 0.8
    
    return profiles.default_weight


def merge_profiles(
    base: CriticalityProfiles,
    overrides: Dict[str, Any],
) -> CriticalityProfiles:
    """
    Create a new profile by merging overrides into a base profile.
    
    Args:
        base: Base criticality profiles
        overrides: Dictionary with tag_weights, path_weights, or default_weight
    
    Returns:
        New CriticalityProfiles with merged values
    """
    merged_tags = base.tag_weights.copy()
    merged_paths = base.path_weights.copy()
    default = base.default_weight
    
    if "tag_weights" in overrides:
        merged_tags.update(overrides["tag_weights"])
    
    if "path_weights" in overrides:
        merged_paths.update(overrides["path_weights"])
    
    if "default_weight" in overrides:
        default = overrides["default_weight"]
    
    return CriticalityProfiles(
        tag_weights=merged_tags,
        path_weights=merged_paths,
        default_weight=default,
    )
