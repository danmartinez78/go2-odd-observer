"""
COD construction tools implementing ODD_COD_DISTANCE.md spec.

These Python tools process sensor agent outputs (per-window measurements)
and construct:
1. Overall COD region for scenario
2. Time series of point violation distances and margins
3. Region-level aggregate metrics

Implements distance metrics for range, bool, and enum axis types.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import math


def construct_cod_from_sensor_outputs(
    odd_spec: Dict[str, Any],
    perception_output: Dict[str, Any],
    motion_output: Dict[str, Any],
    collision_output: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Construct COD from sensor agent outputs.

    Args:
        odd_spec: ODD specification with type definitions
        perception_output: Perception agent output (per-window measurements)
        motion_output: Motion agent output (per-window measurements)
        collision_output: Collision agent output (per-window measurements)
        weights: Optional per-axis weights for distance calculations

    Returns:
        {
            "cod_region": {...},
            "time_series": {...},
            "region_metrics": {...}
        }
    """
    if weights is None:
        weights = {k: 1.0 for k in odd_spec.keys()}

    # Combine per-window measurements from all sensor agents
    per_window_data = _combine_sensor_outputs(
        perception_output,
        motion_output,
        collision_output
    )

    # Build overall COD region
    cod_region = _build_cod_region(per_window_data, odd_spec)

    # Compute time series metrics (violation distance & margin per window)
    time_series = _compute_time_series_metrics(
        per_window_data,
        odd_spec,
        weights
    )

    # Compute region-level metrics
    region_metrics = _compute_region_metrics(
        cod_region,
        odd_spec,
        time_series,
        weights
    )

    return {
        "cod_region": cod_region,
        "time_series": time_series,
        "region_metrics": region_metrics,
    }


def _combine_sensor_outputs(
    perception_output: Dict[str, Any],
    motion_output: Dict[str, Any],
    collision_output: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Combine per-window measurements from all sensor agents.

    Returns list of dicts, one per window:
    [
        {
            "window_id": "000",
            "measurements": {
                "lighting": 0.5,
                "clutter": 0.3,
                "speed": 0.4,
                "stairs": 0,
                ...
            }
        },
        ...
    ]
    """
    # Extract per-window data from each agent
    # Sensor agents output format:
    # {
    #   "per_window": [
    #     {"window_id": "000", "measurements": {...}},
    #     ...
    #   ]
    # }
    # Fallback to "per_window_measurements" for backward compatibility

    perception_windows = perception_output.get(
        "per_window", perception_output.get("per_window_measurements", []))
    motion_windows = motion_output.get(
        "per_window", motion_output.get("per_window_measurements", []))
    collision_windows = collision_output.get(
        "per_window", collision_output.get("per_window_measurements", []))

    # Create index by window_id
    combined = {}

    for window_data in perception_windows:
        wid = window_data["window_id"]
        if wid not in combined:
            combined[wid] = {"window_id": wid, "measurements": {}}
        combined[wid]["measurements"].update(
            window_data.get("measurements", {}))

    for window_data in motion_windows:
        wid = window_data["window_id"]
        if wid not in combined:
            combined[wid] = {"window_id": wid, "measurements": {}}
        combined[wid]["measurements"].update(
            window_data.get("measurements", {}))

    for window_data in collision_windows:
        wid = window_data["window_id"]
        if wid not in combined:
            combined[wid] = {"window_id": wid, "measurements": {}}
        combined[wid]["measurements"].update(
            window_data.get("measurements", {}))

    # Sort by window_id
    return sorted(combined.values(), key=lambda x: x["window_id"])


def _build_cod_region(
    per_window_data: List[Dict[str, Any]],
    odd_spec: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Build overall COD region from per-window measurements.

    For each axis type:
    - range: min/max envelope
    - bool: probability distribution {p_0: ..., p_1: ...}
    - enum: probability distribution {label: ...}
    """
    cod_region = {}

    for axis_name, axis_spec in odd_spec.items():
        axis_type = axis_spec["type"]

        # Collect all values for this axis across windows
        values = []
        for window in per_window_data:
            if axis_name in window["measurements"]:
                values.append(window["measurements"][axis_name])

        if not values:
            continue

        if axis_type == "range":
            cod_region[axis_name] = {
                "type": "range",
                "min": float(min(values)),
                "max": float(max(values))
            }

        elif axis_type == "bool":
            # Compute frequency distribution
            count_0 = sum(1 for v in values if v == 0)
            count_1 = sum(1 for v in values if v == 1)
            total = len(values)

            cod_region[axis_name] = {
                "type": "bool",
                "p_0": count_0 / total if total > 0 else 0.0,
                "p_1": count_1 / total if total > 0 else 0.0,
            }

        elif axis_type == "enum":
            # Compute frequency distribution over labels
            label_counts = {}
            for v in values:
                label_counts[v] = label_counts.get(v, 0) + 1

            total = len(values)
            distribution = {
                label: count / total
                for label, count in label_counts.items()
            }
            distribution["type"] = "enum"
            cod_region[axis_name] = distribution

    return cod_region


def _compute_time_series_metrics(
    per_window_data: List[Dict[str, Any]],
    odd_spec: Dict[str, Any],
    weights: Dict[str, float]
) -> Dict[str, Any]:
    """
    Compute per-window point violation distance and margin to boundary.

    Returns time series arrays.
    """
    window_ids = []
    violation_distances = []
    margins_to_boundary = []
    violation_flags = []

    for window in per_window_data:
        wid = window["window_id"]
        measurements = window["measurements"]

        # Compute point violation distance
        d_viol = _violation_distance_point(measurements, odd_spec, weights)

        # Compute margin to boundary (range axes only)
        margin = _margin_to_boundary_point(measurements, odd_spec)

        window_ids.append(wid)
        violation_distances.append(round(d_viol, 4))
        margins_to_boundary.append(round(margin, 4))
        violation_flags.append(d_viol > 0.0)

    return {
        "window_ids": window_ids,
        "violation_distances": violation_distances,
        "margins_to_boundary": margins_to_boundary,
        "violation_flags": violation_flags,
    }


def _compute_region_metrics(
    cod_region: Dict[str, Any],
    odd_spec: Dict[str, Any],
    time_series: Dict[str, Any],
    weights: Dict[str, float]
) -> Dict[str, Any]:
    """
    Compute region-level aggregate metrics.
    """
    # Region distance
    d_region = _region_distance(cod_region, odd_spec, weights)

    # Fraction outside per axis
    fraction_outside = {}
    for axis_name, axis_spec in odd_spec.items():
        if axis_name not in cod_region:
            continue

        f_i = _fraction_outside_axis(
            axis_name,
            cod_region[axis_name],
            axis_spec
        )
        fraction_outside[axis_name] = round(f_i, 4)

    # Count violations
    violation_flags = time_series["violation_flags"]
    window_ids = time_series["window_ids"]

    total_windows = len(window_ids)
    windows_violated = [wid for wid, flag in zip(
        window_ids, violation_flags) if flag]
    windows_in_odd = total_windows - len(windows_violated)
    first_violation = windows_violated[0] if windows_violated else None

    return {
        "region_distance": round(d_region, 4),
        "fraction_outside_per_axis": fraction_outside,
        "total_windows": total_windows,
        "windows_in_odd": windows_in_odd,
        "windows_violated": windows_violated,
        "first_violation_window": first_violation,
    }


# =============================================================================
# DISTANCE METRIC IMPLEMENTATIONS (from ODD_COD_DISTANCE.md)
# =============================================================================

def _violation_distance_point(
    cod_point: Dict[str, Any],
    odd_spec: Dict[str, Any],
    weights: Dict[str, float]
) -> float:
    """
    Compute point violation distance D_violation_point.

    Returns 0 if point is inside ODD, positive value if outside.
    """
    v_sq_sum = 0.0

    for feat, spec in odd_spec.items():
        if feat not in cod_point:
            continue

        w = weights.get(feat, 1.0)
        x = cod_point[feat]
        t = spec["type"]

        if t == "range":
            a, b = spec["min"], spec["max"]
            if a <= x <= b:
                v = 0.0
            elif x > b:
                v = (x - b) / (b - a) if (b - a) > 0 else 0.0
            else:  # x < a
                v = (a - x) / (b - a) if (b - a) > 0 else 0.0

        elif t == "bool":
            allowed = spec["allowed"]
            v = 0.0 if x == allowed else 1.0

        elif t == "enum":
            allowed_set = set(spec["allowed"])
            v = 0.0 if x in allowed_set else 1.0

        else:
            continue

        v_sq_sum += w * (v ** 2)

    return math.sqrt(v_sq_sum)


def _margin_to_boundary_point(
    cod_point: Dict[str, Any],
    odd_spec: Dict[str, Any]
) -> float:
    """
    Compute margin to boundary M_point (range axes only).

    Returns minimum margin across all range axes.
    0 means on boundary or outside ODD.
    """
    margins = []

    for feat, spec in odd_spec.items():
        if spec["type"] != "range":
            continue

        if feat not in cod_point:
            continue

        a, b = spec["min"], spec["max"]
        x = cod_point[feat]

        if x < a or x > b:
            m = 0.0
        else:
            range_width = b - a
            if range_width == 0:
                m = 0.0
            else:
                lower_margin = (x - a) / range_width
                upper_margin = (b - x) / range_width
                m = min(lower_margin, upper_margin)

        margins.append(m)

    if not margins:
        return 0.0

    return min(margins)


def _region_distance(
    cod_region: Dict[str, Any],
    odd_spec: Dict[str, Any],
    weights: Dict[str, float]
) -> float:
    """
    Compute region distance D_region.

    Measures how much of the COD region lies outside ODD.
    """
    f_sq_sum = 0.0

    for feat, spec in odd_spec.items():
        if feat not in cod_region:
            continue

        w = weights.get(feat, 1.0)
        f_i = _fraction_outside_axis(feat, cod_region[feat], spec)
        f_sq_sum += w * (f_i ** 2)

    return math.sqrt(f_sq_sum)


def _fraction_outside_axis(
    axis_name: str,
    cod_axis_data: Dict[str, Any],
    odd_axis_spec: Dict[str, Any]
) -> float:
    """
    Compute fraction of COD region outside ODD for a single axis.
    """
    axis_type = odd_axis_spec["type"]

    if axis_type == "range":
        a, b = odd_axis_spec["min"], odd_axis_spec["max"]
        u_min, u_max = cod_axis_data["min"], cod_axis_data["max"]

        cod_len = max(0.0, u_max - u_min)
        if cod_len == 0.0:
            return 0.0

        overlap_min = max(a, u_min)
        overlap_max = min(b, u_max)
        overlap_len = max(0.0, overlap_max - overlap_min)

        return 1.0 - (overlap_len / cod_len)

    elif axis_type == "bool":
        allowed = odd_axis_spec["allowed"]
        p_allowed = cod_axis_data.get(f"p_{allowed}", 0.0)
        return 1.0 - p_allowed

    elif axis_type == "enum":
        allowed_set = set(odd_axis_spec["allowed"])
        # Sum probability of disallowed labels
        f_outside = 0.0
        for label, prob in cod_axis_data.items():
            if label == "type":
                continue
            if label not in allowed_set:
                f_outside += prob
        return f_outside

    return 0.0
