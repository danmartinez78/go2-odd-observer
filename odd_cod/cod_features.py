"""
COD Feature Mappings

Provides mappings from categorical COD tags to numeric values for distance computation.
"""

from typing import Dict, Any, List
import numpy as np
from .odd_spec_schema import OddSpec, AxisSpecNumeric, AxisSpecCategorical


# Categorical mappings to [0, 1] range
TERRAIN_MAP = {
    "smooth": 0.0,
    "moderate": 0.33,
    "rough": 0.66,
    "very_rough": 1.0,
}

LIGHTING_MAP = {
    "bright": 0.0,
    "dim": 0.5,
    "dark": 1.0,
}

HUMAN_PROX_MAP = {
    "none": 0.0,
    "visible_far": 0.5,
    "very_close": 1.0,
}

COLLISION_MAP = {
    "no_collision": 0.0,
    "collision_suspected": 1.0,
}

DOMAIN_MAP = {
    "sim": 0.0,
    "real": 1.0,
}


def build_cod_vector(tags: Dict[str, Any], odd_spec: OddSpec) -> Dict[str, float]:
    """
    Convert merged COD tags into a numeric feature vector aligned with ODD axes.
    
    This function takes the raw tags from agents (motion, image, lidar, collision)
    and produces a numeric representation that can be compared against the ODD spec.
    
    Args:
        tags: Dictionary of COD tags from various agents, e.g.:
            {
                "avg_forward_speed": 1.2,
                "max_abs_roll_pitch_deg": 8.5,
                "terrain_roughness_class": "moderate",
                "lighting_class": "dim",
                "humans_very_close": False,
                "collision_suspected": False,
                ...
            }
        odd_spec: The ODD specification to align with
        
    Returns:
        Dictionary mapping axis names to numeric values, e.g.:
            {
                "speed": 1.2,
                "roll_pitch": 8.5,
                "terrain": 0.33,
                "lighting": 0.5,
                "humans": 0.0,
                "collision": 0.0
            }
    """
    cod_vector = {}
    
    for axis_name, axis_spec in odd_spec.axes.items():
        if isinstance(axis_spec, AxisSpecNumeric):
            # Direct numeric mapping
            cod_vector[axis_name] = _extract_numeric_feature(tags, axis_spec.feature, axis_name)
        
        elif isinstance(axis_spec, AxisSpecCategorical):
            # Categorical to numeric mapping
            cod_vector[axis_name] = _extract_categorical_feature(tags, axis_spec.feature, axis_name)
    
    return cod_vector


def _extract_numeric_feature(tags: Dict[str, Any], feature_name: str, axis_name: str) -> float:
    """
    Extract numeric feature from tags.
    
    Tries multiple possible tag names based on common conventions.
    """
    # Try direct match
    if feature_name in tags:
        return float(tags[feature_name])
    
    # Try axis name
    if axis_name in tags:
        return float(tags[axis_name])
    
    # Try common variations
    variations = [
        f"avg_{feature_name}",
        f"max_{feature_name}",
        f"{feature_name}_avg",
        f"{feature_name}_max",
        f"{axis_name}_value",
    ]
    
    for var in variations:
        if var in tags:
            return float(tags[var])
    
    # Default to 0 if not found (with warning in production)
    return 0.0


def _extract_categorical_feature(tags: Dict[str, Any], feature_name: str, axis_name: str) -> float:
    """
    Extract categorical feature from tags and convert to numeric.
    
    Handles both direct category strings and boolean flags.
    """
    # Try direct category value
    if feature_name in tags:
        value = tags[feature_name]
        return _categorical_to_numeric(value, axis_name)
    
    # Try axis name
    if axis_name in tags:
        value = tags[axis_name]
        return _categorical_to_numeric(value, axis_name)
    
    # Try variations
    variations = [
        f"{feature_name}_class",
        f"{axis_name}_class",
        f"{feature_name}_type",
        f"{axis_name}_category",
    ]
    
    for var in variations:
        if var in tags:
            value = tags[var]
            return _categorical_to_numeric(value, axis_name)
    
    # Check for boolean flags (e.g., "collision_suspected", "humans_very_close")
    if axis_name == "collision":
        if "collision_suspected" in tags:
            return 1.0 if tags["collision_suspected"] else 0.0
    
    if axis_name == "humans":
        if "humans_very_close" in tags and tags["humans_very_close"]:
            return HUMAN_PROX_MAP["very_close"]
        if "humans_visible" in tags and tags["humans_visible"]:
            return HUMAN_PROX_MAP["visible_far"]
        return HUMAN_PROX_MAP["none"]
    
    # Default to 0
    return 0.0


def _categorical_to_numeric(value: Any, axis_name: str) -> float:
    """
    Convert categorical value to numeric based on axis name.
    """
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    
    if not isinstance(value, str):
        value = str(value).lower()
    else:
        value = value.lower()
    
    # Select appropriate mapping
    if axis_name == "terrain":
        return TERRAIN_MAP.get(value, 0.5)  # Default to moderate
    elif axis_name == "lighting":
        return LIGHTING_MAP.get(value, 0.5)  # Default to dim
    elif axis_name == "humans":
        return HUMAN_PROX_MAP.get(value, 0.0)  # Default to none
    elif axis_name == "collision":
        return COLLISION_MAP.get(value, 0.0)  # Default to no collision
    elif axis_name == "domain":
        return DOMAIN_MAP.get(value, 1.0)  # Default to real
    
    # Unknown axis, return middle value
    return 0.5


def aggregate_window_tags(window_tags: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate tags from multiple windows into scenario-level statistics.
    
    Args:
        window_tags: List of tag dictionaries, one per window
        
    Returns:
        Dictionary with aggregated statistics (means, modes, distributions)
    """
    if not window_tags:
        return {}
    
    aggregated = {}
    
    # Collect all keys
    all_keys = set()
    for tags in window_tags:
        all_keys.update(tags.keys())
    
    for key in all_keys:
        values = [tags.get(key) for tags in window_tags if key in tags]
        
        if not values:
            continue
        
        # Numeric aggregation
        if isinstance(values[0], (int, float)):
            aggregated[f"{key}_mean"] = np.mean(values)
            aggregated[f"{key}_max"] = np.max(values)
            aggregated[f"{key}_min"] = np.min(values)
            aggregated[f"{key}_std"] = np.std(values)
        
        # Categorical aggregation (mode)
        elif isinstance(values[0], str):
            from collections import Counter
            counter = Counter(values)
            aggregated[f"{key}_mode"] = counter.most_common(1)[0][0]
            aggregated[f"{key}_distribution"] = dict(counter)
        
        # Boolean aggregation
        elif isinstance(values[0], bool):
            aggregated[f"{key}_fraction"] = sum(values) / len(values)
            aggregated[f"{key}_any"] = any(values)
            aggregated[f"{key}_all"] = all(values)
    
    return aggregated
