"""
Distance Metrics

Compute COD-ODD distance at window and scenario levels.
"""

from typing import Dict, List, Tuple
import numpy as np
from .odd_spec_schema import OddSpec, AxisSpecNumeric, AxisSpecCategorical
from .cod_features import TERRAIN_MAP, LIGHTING_MAP, HUMAN_PROX_MAP, COLLISION_MAP


def compute_window_distance(
    cod_vector: Dict[str, float],
    odd_spec: OddSpec,
) -> Tuple[float, Dict[str, float], Dict[str, str]]:
    """
    Compute COD–ODD distance for a single window.
    
    Returns a normalized distance in [0, 1] where:
    - 0.0 = perfect ODD compliance (at center)
    - ~0.3 = at ODD boundary
    - 0.7-1.0 = ODD violation
    
    Args:
        cod_vector: Numeric COD feature vector (from build_cod_vector)
        odd_spec: The ODD specification
        
    Returns:
        Tuple of:
        - overall_distance: Weighted average distance [0, 1]
        - axis_distances: Per-axis distances
        - axis_statuses: Per-axis classifications ('in_odd', 'near_boundary', 'out_of_odd')
    """
    axis_distances = {}
    axis_statuses = {}
    
    for axis_name, axis_spec in odd_spec.axes.items():
        if axis_name not in cod_vector:
            # Missing data, assume worst case
            axis_distances[axis_name] = 1.0
            axis_statuses[axis_name] = "unknown"
            continue
        
        value = cod_vector[axis_name]
        
        if isinstance(axis_spec, AxisSpecNumeric):
            # Numeric distance
            axis_distances[axis_name] = axis_spec.distance_from_odd(value)
            axis_statuses[axis_name] = axis_spec.classify_value(value)
        
        elif isinstance(axis_spec, AxisSpecCategorical):
            # Categorical distance (convert to numeric first)
            # Values in allowed_in_odd → distance 0
            # Values not in allowed_in_odd but in allowed_all → distance 1
            # Unknown values → distance 1
            axis_statuses[axis_name] = axis_spec.classify_value(_numeric_to_category(value, axis_name))
            
            if axis_statuses[axis_name] == "in_odd":
                axis_distances[axis_name] = 0.0
            elif axis_statuses[axis_name] == "out_of_odd":
                axis_distances[axis_name] = 1.0
            else:  # unknown
                axis_distances[axis_name] = 1.0
    
    # Weighted average
    total_weight = sum(odd_spec.importance.values())
    if total_weight == 0:
        overall_distance = 0.0
    else:
        weighted_sum = sum(
            axis_distances.get(axis_name, 1.0) * weight
            for axis_name, weight in odd_spec.importance.items()
        )
        overall_distance = weighted_sum / total_weight
    
    return overall_distance, axis_distances, axis_statuses


def _numeric_to_category(value: float, axis_name: str) -> str:
    """
    Convert numeric value back to category for classification.
    
    This reverses the categorical mapping to find the closest category.
    """
    if axis_name == "terrain":
        mapping = TERRAIN_MAP
    elif axis_name == "lighting":
        mapping = LIGHTING_MAP
    elif axis_name == "humans":
        mapping = HUMAN_PROX_MAP
    elif axis_name == "collision":
        mapping = COLLISION_MAP
    else:
        return "unknown"
    
    # Find closest category
    min_dist = float('inf')
    closest_cat = list(mapping.keys())[0]
    
    for cat, num_val in mapping.items():
        dist = abs(value - num_val)
        if dist < min_dist:
            min_dist = dist
            closest_cat = cat
    
    return closest_cat


def compute_window_odd_status(axis_statuses: Dict[str, str]) -> str:
    """
    Determine overall window ODD status from per-axis statuses.
    
    Args:
        axis_statuses: Dictionary of per-axis classifications
        
    Returns:
        One of: 'in_odd', 'near_boundary', 'odd_exit'
    """
    statuses = list(axis_statuses.values())
    
    # If any axis is out_of_odd, the whole window is an ODD exit
    if "out_of_odd" in statuses or "unknown" in statuses:
        return "odd_exit"
    
    # If any axis is near boundary, the window is near boundary
    if "near_boundary" in statuses:
        return "near_boundary"
    
    # All axes in ODD
    return "in_odd"


def compute_scenario_distance(
    window_distances: List[float],
    window_statuses: List[str],
    penalize_exits: bool = True,
) -> float:
    """
    Compute scenario-level COD–ODD distance.
    
    Combines mean window distance with penalty for ODD exits.
    
    Args:
        window_distances: List of per-window distances [0, 1]
        window_statuses: List of per-window ODD statuses
        penalize_exits: Whether to add penalty for ODD exit fraction
        
    Returns:
        Scenario distance in [0, 1]
    """
    if not window_distances:
        return 1.0  # No data = worst case
    
    # Base distance: mean of all windows
    mean_distance = np.mean(window_distances)
    
    if not penalize_exits:
        return float(mean_distance)
    
    # Penalty: fraction of ODD exits
    num_exits = sum(1 for status in window_statuses if status == "odd_exit")
    exit_fraction = num_exits / len(window_statuses) if window_statuses else 0.0
    
    # Combined metric: 70% mean distance + 30% exit fraction
    scenario_distance = 0.7 * mean_distance + 0.3 * exit_fraction
    
    return float(min(1.0, scenario_distance))


def classify_scenario(
    scenario_distance: float,
    exit_fraction: float,
    in_odd_threshold: float = 0.3,
    boundary_threshold: float = 0.7,
) -> str:
    """
    Classify scenario into categories based on distance and exit fraction.
    
    Args:
        scenario_distance: Overall scenario distance [0, 1]
        exit_fraction: Fraction of windows that are ODD exits [0, 1]
        in_odd_threshold: Distance threshold for IN_ODD classification
        boundary_threshold: Distance threshold for BOUNDARY_HEAVY classification
        
    Returns:
        One of: 'IN_ODD', 'BOUNDARY_HEAVY', 'ODD_EXIT'
    """
    if scenario_distance < in_odd_threshold and exit_fraction < 0.1:
        return "IN_ODD"
    elif scenario_distance < boundary_threshold and exit_fraction < 0.3:
        return "BOUNDARY_HEAVY"
    else:
        return "ODD_EXIT"


def compute_time_fractions(window_statuses: List[str]) -> Dict[str, float]:
    """
    Compute time fraction spent in each ODD status.
    
    Args:
        window_statuses: List of window status strings
        
    Returns:
        Dictionary with fractions for 'in_odd', 'near_boundary', 'odd_exit'
    """
    if not window_statuses:
        return {"in_odd": 0.0, "near_boundary": 0.0, "odd_exit": 0.0}
    
    total = len(window_statuses)
    
    return {
        "in_odd": sum(1 for s in window_statuses if s == "in_odd") / total,
        "near_boundary": sum(1 for s in window_statuses if s == "near_boundary") / total,
        "odd_exit": sum(1 for s in window_statuses if s == "odd_exit") / total,
    }
