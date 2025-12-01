"""
COD construction tools implementing ODD_COD_DISTANCE.md spec.

These Python tools process sensor agent outputs (per-window measurements)
and construct:
1. Overall COD region for scenario
2. Time series of point violation distances and margins
3. Region-level aggregate metrics

Implements distance metrics for range, bool, and enum axis types.
Uses LLM micro-agent for semantic categorical mismatch assessment.
"""

import json
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import math

# Version tracking for COD construction tools
# 1.1.0: Added categorical micro-agent with gemini-2.5-flash
# 1.2.0: Updated to handle odd_measurements schema and normalize field names
# 1.3.0: Removed collision→proximity mapping (collision is advisory only, not actor proximity)
COD_TOOL_VERSION = "1.3.0"
CATEGORICAL_AGENT_MODEL = "gemini-2.5-flash"


def _flatten_odd_spec(odd_spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten nested ODD spec structure to flat axis dictionary.

    Input format (from OddSpecAgent):
    {
      "odd_specification": {
        "environment": {
          "categorical": {"lighting": {"type": "enum", ...}},
          "numeric": {"speed": {"type": "range", ...}},
          "boolean": {"stairs": {"type": "bool", ...}}
        },
        "actors": {...},
        "ego": {...}
      }
    }

    Output format (for COD construction):
    {
      "lighting": {"type": "enum", ...},
      "speed": {"type": "range", ...},
      "stairs": {"type": "bool", ...}
    }
    """
    flat = {}

    # Handle already-flat format (defensive)
    if "odd_specification" not in odd_spec:
        # Check if it's already flat (has type fields at top level values)
        for key, val in odd_spec.items():
            if isinstance(val, dict) and "type" in val:
                return odd_spec  # Already flat
        # Otherwise unknown format, return as-is
        return odd_spec

    spec = odd_spec["odd_specification"]

    # Iterate over domains (environment, actors, ego, etc.)
    for domain_name, domain_data in spec.items():
        if not isinstance(domain_data, dict):
            continue

        # Iterate over constraint types (categorical, numeric, boolean)
        for constraint_type, constraints in domain_data.items():
            if not isinstance(constraints, dict):
                continue

            # Add each axis to flat dict
            for axis_name, axis_spec in constraints.items():
                if isinstance(axis_spec, dict):
                    flat[axis_name] = axis_spec

    return flat


# =============================================================================
# CATEGORICAL MISMATCH MICRO-AGENT
# =============================================================================

def _assess_categorical_mismatches_sync(
    mismatches: List[Dict[str, Any]],
    model: str = CATEGORICAL_AGENT_MODEL
) -> Dict[str, float]:
    """
    Synchronous wrapper for categorical mismatch assessment.

    Args:
        mismatches: List of {axis_name, odd_allowed, measured_labels}
        model: Which model to use (default: flash for better generalization)

    Returns:
        Dict mapping axis_name -> semantic distance (0.0, 0.5, or 1.0)
    """
    if not mismatches:
        return {}

    # Run async function in sync context
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context, create new loop
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    _assess_categorical_mismatches_async(mismatches, model)
                )
                return future.result()
        else:
            return loop.run_until_complete(
                _assess_categorical_mismatches_async(mismatches, model)
            )
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(_assess_categorical_mismatches_async(mismatches, model))


async def _assess_categorical_mismatches_async(
    mismatches: List[Dict[str, Any]],
    model: str = "gemini-2.5-flash-lite"
) -> Dict[str, float]:
    """
    Use LLM to assess semantic compatibility of categorical mismatches.

    This enables the COD distance computation to understand that
    "smooth" ≈ "flat" (synonyms) or "indoor_commercial" ⊇ "office" (superset).

    Args:
        mismatches: List of {axis_name, odd_allowed, measured_labels}
        model: Which model to use (default: cheapest/fastest)

    Returns:
        Dict mapping axis_name -> semantic distance (0.0, 0.5, or 1.0)
    """
    try:
        from google import genai
    except ImportError:
        # Fallback to exact matching if genai not available
        return {m['axis_name']: 1.0 for m in mismatches}

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        # Fallback to exact matching if no API key
        return {m['axis_name']: 1.0 for m in mismatches}

    client = genai.Client(api_key=api_key)

    # Build the prompt
    prompt_parts = [
        "You are assessing categorical ODD (Operational Design Domain) mismatches.",
        "For each axis, determine if the measured values are semantically compatible with allowed values.",
        "",
        "SCORING RULES (apply in order):",
        "",
        "1. SUPERSET/GENERAL (score 0.0): If measured is a BROADER or MORE GENERAL category.",
        "   - 'smooth' is a property shared by 'smooth_tile', 'smooth_hardwood', 'smooth_concrete'",
        "   - 'indoor_commercial' contains 'office', 'retail', 'warehouse'",
        "   - 'indoor' contains 'indoor_commercial', 'indoor_residential'",
        "   - 'commercial' contains 'warehouse', 'office', 'retail'",
        "   - 'flooring' contains 'tile', 'hardwood', 'carpet'",
        "   KEY: If measured is a prefix, qualifier, or parent category of the allowed values → 0.0",
        "",
        "2. SUBSET/SPECIFIC (score 0.0): If measured is MORE SPECIFIC than allowed.",
        "   - 'office' is a type of 'commercial' or 'indoor_commercial' → compatible",
        "   - 'smooth_tile' is a type of 'smooth' → compatible",
        "",
        "3. SYNONYM (score 0.0): Same meaning, different words.",
        "   - 'smooth' ≈ 'flat' ≈ 'level' ≈ 'even'",
        "   - 'bright' ≈ 'well-lit' ≈ 'good_lighting'",
        "",
        "4. RELATED (score 0.5): Same domain, no hierarchy relationship.",
        "   - 'warehouse' vs 'retail' (both commercial, but siblings)",
        "   - 'dim' vs 'moderate' lighting (adjacent levels)",
        "",
        "5. INCOMPATIBLE (score 1.0): Fundamentally different.",
        "   - 'outdoor' vs 'indoor'",
        "   - 'stairs' vs 'flat'",
        "",
        "IMPORTANT: When measured is a general property and allowed values are specific variants",
        "of that property (e.g., measured='smooth', allowed=['smooth_tile', 'smooth_hardwood']),",
        "this is COMPATIBLE (score 0.0) because the robot IS on a smooth surface.",
        "",
        "MISMATCHES TO ASSESS:",
        ""
    ]

    for i, m in enumerate(mismatches, 1):
        prompt_parts.append(f"{i}. AXIS: {m['axis_name']}")
        prompt_parts.append(f"   ODD ALLOWED: {m['odd_allowed']}")
        prompt_parts.append(f"   MEASURED: {m['measured_labels']}")
        prompt_parts.append("")

    prompt_parts.extend([
        "Respond with ONLY a JSON object mapping axis names to scores.",
        "Example: {\"terrain_type\": 0.0, \"environment_type\": 1.0}",
        "",
        "JSON response:"
    ])

    prompt = "\n".join(prompt_parts)

    try:
        response = client.models.generate_content(
            model=model,
            contents=[prompt]
        )

        # Log token usage for cost tracking
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage = response.usage_metadata
            print(f"[COD] Categorical micro-agent ({model}): "
                  f"{usage.prompt_token_count} input + {usage.candidates_token_count} output tokens")

        # Parse response
        text = response.text.strip()
        # Handle markdown code blocks
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text)
        return result

    except Exception as e:
        # Fallback to 1.0 (violation) for all axes on error
        print(f"[COD] Categorical assessment error: {e}")
        return {m['axis_name']: 1.0 for m in mismatches}


def _collect_categorical_mismatches(
    cod_region: Dict[str, Any],
    odd_spec: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
    """
    Identify categorical (enum) axes with mismatches between COD and ODD.

    Returns:
        mismatches: List of {axis_name, odd_allowed, measured_labels} for LLM assessment
        exact_matches: Dict of axis_name -> list of matching labels (no LLM needed)
    """
    mismatches = []
    exact_matches = {}

    for axis_name, axis_spec in odd_spec.items():
        if axis_spec.get("type") != "enum":
            continue

        if axis_name not in cod_region:
            continue

        cod_data = cod_region[axis_name]
        allowed_set = set(axis_spec.get("allowed", []))

        # Get measured labels from COD region
        measured_labels = [
            label for label in cod_data.keys()
            if label != "type" and cod_data[label] > 0
        ]

        # Separate exact matches from mismatches
        exact = [l for l in measured_labels if l in allowed_set]
        mismatched = [l for l in measured_labels if l not in allowed_set]

        if exact:
            exact_matches[axis_name] = exact

        if mismatched:
            mismatches.append({
                "axis_name": axis_name,
                "odd_allowed": list(allowed_set),
                "measured_labels": mismatched
            })

    return mismatches, exact_matches


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

    # DEBUG: Check for axis/measurement alignment
    # Extract all axis names from nested ODD spec structure
    odd_axes = set()
    spec = odd_spec.get("odd_specification", {})
    for domain_data in spec.values():
        if isinstance(domain_data, dict):
            for constraint_type_data in domain_data.values():
                if isinstance(constraint_type_data, dict):
                    odd_axes.update(constraint_type_data.keys())

    measured_axes = set(cod_region.keys())

    missing_measurements = odd_axes - measured_axes
    extra_measurements = measured_axes - odd_axes

    if missing_measurements:
        print(
            f"⚠️  [COD] ODD axes WITHOUT measurements: {sorted(missing_measurements)}")
    if extra_measurements:
        print(
            f"⚠️  [COD] Measurements WITHOUT ODD axes: {sorted(extra_measurements)}")
    if not missing_measurements and not extra_measurements:
        print(
            f"✅ [COD] All {len(odd_axes)} ODD axes have matching measurements")

    # Collect categorical mismatches FIRST for semantic assessment
    # This is used for BOTH time series AND region metrics
    mismatches, exact_matches = _collect_categorical_mismatches(
        cod_region, odd_spec)

    # Assess mismatches with LLM (single batched call)
    categorical_distances = {}
    if mismatches:
        categorical_distances = _assess_categorical_mismatches_sync(mismatches)

    # Compute time series metrics (violation distance & margin per window)
    # NOW includes semantic distances for categorical axes
    time_series = _compute_time_series_metrics(
        per_window_data,
        odd_spec,
        weights,
        categorical_distances  # Pass semantic distances
    )

    # Compute region-level metrics (also uses semantic distances)
    region_metrics = _compute_region_metrics(
        cod_region,
        odd_spec,
        time_series,
        weights,
        categorical_distances  # Pass semantic distances
    )

    return {
        "cod_region": cod_region,
        "time_series": time_series,
        "region_metrics": region_metrics,
    }


def _normalize_perception_measurements(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize perception measurements.

    Perception tool outputs odd_measurements with EXACT axis names from ODD spec.
    Just pass through measurement fields.
    """
    normalized = {}

    for key, value in raw.items():
        # Skip non-measurement fields
        if key in ["window_id", "observations", "reasoning", "confidence", "odd_concerns"]:
            continue
        normalized[key] = value

    return normalized


def _normalize_motion_measurements(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize motion measurements to match ODD spec axis names.
    Motion measurements already match ODD spec names.
    """
    normalized = {}

    # Direct mappings (already correct)
    for key in ["max_accel_mps2", "max_speed_mps", "max_roll_deg", "max_pitch_deg"]:
        if key in raw:
            normalized[key] = raw[key]

    return normalized


def _normalize_collision_measurements(raw: Dict[str, Any], window_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize collision measurements.

    NOTE: Collision proximity_estimate_m is OBSTACLE distance (furniture, walls),
    NOT actor (human/animal) proximity. Do NOT map to min_proximity_m.
    Collision is ADVISORY ONLY - does not contribute ODD measurements.
    """
    # Return empty - collision doesn't contribute ODD axis measurements
    # Actor presence is handled by perception agent (human_present, animal_present)
    return {}


def _combine_sensor_outputs(
    perception_output: Dict[str, Any],
    motion_output: Dict[str, Any],
    collision_output: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Combine per-window measurements from all sensor agents.

    Handles current schema where agents output:
    - "per_window": [{"window_id": "000", "odd_measurements": {...}}, ...]

    Normalizes field names to match ODD spec axes.

    Returns list of dicts, one per window:
    [
        {
            "window_id": "000",
            "measurements": {
                "lighting_conditions": "moderate",
                "terrain_type": "smooth_floors",
                "obstacle_density": 0.01,
                "max_accel_mps2": 0.15,
                ...
            }
        },
        ...
    ]
    """
    # Extract per-window data from each agent
    # Current schema uses "per_window" with "odd_measurements"
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
        # Current schema uses odd_measurements, fallback to measurements
        raw = window_data.get("odd_measurements",
                              window_data.get("measurements", {}))
        normalized = _normalize_perception_measurements(raw)
        combined[wid]["measurements"].update(normalized)

    for window_data in motion_windows:
        wid = window_data["window_id"]
        if wid not in combined:
            combined[wid] = {"window_id": wid, "measurements": {}}
        raw = window_data.get("odd_measurements",
                              window_data.get("measurements", {}))
        normalized = _normalize_motion_measurements(raw)
        combined[wid]["measurements"].update(normalized)

    for window_data in collision_windows:
        wid = window_data["window_id"]
        if wid not in combined:
            combined[wid] = {"window_id": wid, "measurements": {}}
        # Collision is ADVISORY ONLY - does not contribute ODD measurements
        # Actor presence (human_present, animal_present) is handled by perception
        # Collision proximity_estimate_m is obstacle distance, NOT actor proximity

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
    weights: Dict[str, float],
    categorical_distances: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Compute per-window point violation distance and margin to boundary.

    Args:
        per_window_data: Combined measurements per window
        odd_spec: ODD specification
        weights: Per-axis weights
        categorical_distances: LLM-assessed semantic distances for enum axes

    Returns time series arrays.
    """
    if categorical_distances is None:
        categorical_distances = {}

    window_ids = []
    violation_distances = []
    margins_to_boundary = []
    violation_flags = []

    for window in per_window_data:
        wid = window["window_id"]
        measurements = window["measurements"]

        # Compute point violation distance WITH semantic distances
        d_viol = _violation_distance_point(
            measurements, odd_spec, weights, categorical_distances)

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
    weights: Dict[str, float],
    categorical_distances: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Compute region-level aggregate metrics.

    Args:
        cod_region: COD region data
        odd_spec: ODD specification
        time_series: Per-window time series data
        weights: Per-axis weights
        categorical_distances: Pre-computed LLM semantic distances for enum axes
    """
    if categorical_distances is None:
        categorical_distances = {}

    # Region distance
    d_region = _region_distance(
        cod_region, odd_spec, weights, categorical_distances)

    # Fraction outside per axis
    fraction_outside = {}
    for axis_name, axis_spec in odd_spec.items():
        if axis_name not in cod_region:
            continue

        f_i = _fraction_outside_axis(
            axis_name,
            cod_region[axis_name],
            axis_spec,
            categorical_distances.get(axis_name)
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

    result = {
        "region_distance": round(d_region, 4),
        "fraction_outside_per_axis": fraction_outside,
        "total_windows": total_windows,
        "windows_in_odd": windows_in_odd,
        "windows_violated": windows_violated,
        "first_violation_window": first_violation,
    }

    # Include semantic assessment details for transparency
    if categorical_distances:
        result["categorical_semantic_distances"] = categorical_distances

    return result


# =============================================================================
# DISTANCE METRIC IMPLEMENTATIONS (from ODD_COD_DISTANCE.md)
# =============================================================================

def _violation_distance_point(
    cod_point: Dict[str, Any],
    odd_spec: Dict[str, Any],
    weights: Dict[str, float],
    categorical_distances: Optional[Dict[str, float]] = None
) -> float:
    """
    Compute point violation distance D_violation_point.

    Returns 0 if point is inside ODD, positive value if outside.

    Args:
        cod_point: Current operating conditions
        odd_spec: ODD specification with allowed values
        weights: Feature weights for distance calculation
        categorical_distances: Pre-computed semantic distances for categorical features
                             (from semantic micro-agent assessment)
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
            if x in allowed_set:
                # Exact match - no violation
                v = 0.0
            elif categorical_distances and feat in categorical_distances:
                # Use semantic distance from micro-agent assessment
                # (e.g., "hardwood" vs "smooth_hardwood" -> 0.0 semantically compatible)
                v = categorical_distances[feat]
            else:
                # No semantic assessment available - treat as full violation
                v = 1.0

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
    weights: Dict[str, float],
    categorical_distances: Optional[Dict[str, float]] = None
) -> float:
    """
    Compute region distance D_region.

    Measures how much of the COD region lies outside ODD.

    Args:
        cod_region: COD region data
        odd_spec: ODD specification
        weights: Per-axis weights
        categorical_distances: LLM-assessed semantic distances for enum axes
    """
    if categorical_distances is None:
        categorical_distances = {}

    f_sq_sum = 0.0

    for feat, spec in odd_spec.items():
        if feat not in cod_region:
            continue

        w = weights.get(feat, 1.0)
        f_i = _fraction_outside_axis(
            feat,
            cod_region[feat],
            spec,
            categorical_distances.get(feat)
        )
        f_sq_sum += w * (f_i ** 2)

    return math.sqrt(f_sq_sum)


def _fraction_outside_axis(
    axis_name: str,
    cod_axis_data: Dict[str, Any],
    odd_axis_spec: Dict[str, Any],
    semantic_distance: Optional[float] = None
) -> float:
    """
    Compute fraction of COD region outside ODD for a single axis.

    Args:
        axis_name: Name of the axis
        cod_axis_data: COD region data for this axis
        odd_axis_spec: ODD specification for this axis
        semantic_distance: For enum axes, LLM-assessed semantic distance (0.0, 0.5, 1.0)
                          If None, uses exact string matching
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

        # Calculate probability-weighted distance
        total_outside = 0.0
        for label, prob in cod_axis_data.items():
            if label == "type":
                continue

            if label in allowed_set:
                # Exact match - no distance
                continue
            else:
                # Use semantic distance if provided, otherwise 1.0 (full violation)
                if semantic_distance is not None:
                    total_outside += prob * semantic_distance
                else:
                    total_outside += prob * 1.0

        return total_outside

    return 0.0
