# Phase 1.4.4 - Type-Driven COD Construction

**Branch:** `feature/phase1.4.4-type-driven-cod`  
**Status:** Complete - ready for testing  
**Date:** 2024

## Overview

Phase 1.4.4 implements a comprehensive architecture redesign that uses typed ODD specifications and Python tools for deterministic COD construction. This addresses the key limitation of Phase 1.4.3 where the COD agent consumed massive amounts of tokens processing window data.

## Architecture Changes

### Agent Updates

#### 1. ODD Spec Agent v5.0.0 (Breaking)
**Changes:**
- Added `type` field to every ODD axis: `"range"`, `"bool"`, or `"enum"`
- Changed `"values"` to `"allowed"` for categorical axes (consistency)
- Added `"boolean"` section alongside `"categorical"` and `"numeric"`
- All range axes now require both `min` and `max` (even if conceptually one-sided)

**Example:**
```json
{
  "environment": {
    "numeric": {
      "obstacle_density": {
        "type": "range",
        "min": 0.0,
        "max": 0.7,
        "description": "Spatial density of obstacles",
        "measurement_guidance": "Calculate from BEV occupancy channel"
      }
    },
    "categorical": {
      "lighting_conditions": {
        "type": "enum",
        "allowed": ["bright", "moderate", "dim"],
        "description": "Ambient illumination level",
        "measurement_guidance": "Assess from camera imagery"
      }
    },
    "boolean": {
      "stairs_present": {
        "type": "bool",
        "allowed": 0,
        "description": "Whether stairs are accessible",
        "measurement_guidance": "Detect from depth discontinuities"
      }
    }
  }
}
```

#### 2. Sensor Agents v5.0.0 (Perception/Motion/Collision)
**Changes:**
- Output format changed to per-window measurements with compliance tagging
- Each window gets measurements aligned exactly to ODD axis names
- Compliance tags: `"IN_ODD"`, `"OUT_ODD"`, `"AT_BOUNDARY"`
- Summary includes temporal observations and safety concerns separately

**Output Structure:**
```json
{
  "per_window_measurements": [
    {
      "window_id": "000",
      "measurements": {
        "obstacle_density": 0.35,
        "lighting_conditions": "bright",
        "stairs_present": 0
      },
      "compliance": {
        "obstacle_density": "IN_ODD",
        "lighting_conditions": "IN_ODD",
        "stairs_present": "IN_ODD"
      }
    }
  ],
  "summary": {
    "temporal_observations": [
      "Cross-window: obstacle density stable around 0.3-0.4",
      "Sensor quality: good throughout scenario"
    ],
    "safety_concerns": []
  }
}
```

#### 3. Evaluator Agent v1.0.0 (New)
**Purpose:** Replaces COD Classifier + ODD Compliance agents with tool-based approach

**Tools:**
1. `construct_cod_from_sensor_outputs(scenario_path, odd_spec)`:
   - Reads per-window measurements from all sensor agents
   - Constructs overall COD region (envelope of all measurements)
   - Computes time series: violation distance & margin per window
   - Computes region metrics: overall distance, fraction-outside per axis
   - Returns comprehensive JSON result

2. `get_window_details(scenario_path, window_id)`:
   - Retrieves detailed measurements for specific window
   - Used to investigate violations or boundary cases
   - Returns per-sensor measurements for the window

**Output:**
```json
{
  "cod_region": {
    "obstacle_density": {"type": "range", "min": 0.1, "max": 0.6},
    "lighting_conditions": {"type": "enum", "bright": 0.7, "dim": 0.3}
  },
  "time_series_analysis": {
    "violation_patterns": "No violations detected, stable compliance",
    "critical_windows": [],
    "margin_trends": "Margins improve over time (0.2 → 0.4)"
  },
  "compliance_verdict": {
    "overall": "IN_ODD",
    "rationale": "All measurements within ODD boundaries",
    "critical_axes": [],
    "temporal_stability": "STABLE"
  }
}
```

#### 4. Report Agent v4.0.0 (Breaking)
**Changes:**
- Uses `read_analysis_results(scenario_path)` tool instead of blackboard
- Tool reads all agent outputs from files (avoids token overhead)
- LLM focuses on summarization and insights (not data reformatting)
- More concise output focused on executive summary and key findings

**Tool Output:**
```json
{
  "odd_spec": {...},
  "perception": {...},
  "motion": {...},
  "collision": {...},
  "evaluator": {...}
}
```

### Removed Components
- **COD Classifier Agent (v2.0.0):** Replaced by Evaluator with Python tools
- **ODD Compliance Agent (v2.0.0):** Replaced by Evaluator with Python tools
- **cod_tools.py:** Old Python tools replaced by cod_construction.py

## Python COD Construction Tool

### Implementation: `odd_agents/tools/cod_construction.py`

#### Core Function
```python
def construct_cod_from_sensor_outputs(
    scenario_path: str,
    odd_spec: dict
) -> dict
```

**Process:**
1. Read per-window measurements from `perception_output.json`, `motion_output.json`, `collision_output.json`
2. Combine measurements by window ID across all sensors
3. Build overall COD region using type-specific aggregation:
   - **Range axes:** min/max envelope across all windows
   - **Bool axes:** frequency distribution (p_0, p_1)
   - **Enum axes:** label distribution
4. Compute per-window metrics:
   - Violation distance: how far outside ODD (0 if inside)
   - Margin to boundary: how close to edge (range axes only)
5. Compute aggregate region metrics:
   - Region distance: overall COD vs ODD mismatch
   - Fraction-outside per axis: what % of COD lies outside ODD

#### Distance Metrics (from ODD_COD_DISTANCE.md)

**Point Violation Distance (per window):**
```
D_violation_point = sqrt(Σ w_i * v_i²)

Where for each axis i:
- Range: v_i = normalized distance outside [min,max] (0 if inside)
- Bool: v_i = 1 if mismatches allowed value, 0 otherwise
- Enum: v_i = 1 if not in allowed set, 0 otherwise
- w_i = weight (all 1.0 for now, can be customized)
```

**Margin to Boundary (per window):**
```
M_point = min(margin_i) across all range axes

Where margin_i = min((value - min)/(max-min), (max - value)/(max-min))
```

**Region Distance (aggregate):**
```
D_region = sqrt(Σ w_i * f_i²)

Where f_i = fraction of COD region outside ODD for axis i
```

**Fraction Outside (per axis):**
- **Range:** Portion of COD range outside ODD range, normalized
- **Bool:** Frequency of disallowed value
- **Enum:** Sum of frequencies for disallowed labels

### Output Structure

```json
{
  "cod_region": {
    "<axis_name>": {
      "type": "range|bool|enum",
      // Range: "min": X, "max": Y
      // Bool: "p_0": X, "p_1": Y
      // Enum: "<label>": frequency, ...
    }
  },
  "time_series": {
    "window_ids": ["000", "001", ...],
    "violation_distances": [0.0, 0.0, 0.2, ...],
    "margins_to_boundary": [0.3, 0.4, 0.0, ...],
    "violation_flags": [false, false, true, ...]
  },
  "region_metrics": {
    "region_distance": 0.42,
    "fraction_outside_per_axis": {"L": 0.1, "C": 0.3},
    "total_windows": 50,
    "windows_violated": ["007", "008"],
    "first_violation_window": "007"
  }
}
```

## Benefits

### 1. Massive Token Savings
- **Before:** COD agent reads all window data from blackboard → thousands of tokens
- **After:** Python tool processes files → ~0 tokens for computation
- **Estimate:** 70-90% reduction in COD construction cost

### 2. Temporal Violation Tracking
- Per-window violation distances show exactly when ODD was exited
- Margin trends reveal how close to boundary over time
- Enables temporal analysis: "violations cluster in windows 20-25"

### 3. Type-Driven Correctness
- Range axes: min/max envelope (correct for continuous values)
- Bool axes: frequency distribution (correct for binary)
- Enum axes: label distribution (correct for categorical)
- No more confusion about how to aggregate different types

### 4. Rich Analysis Preserved
- Sensor agents still do full multimodal analysis (camera, BEV, IMU, odometry)
- LLMs still reason about temporal patterns, safety, sensor quality
- Python only handles deterministic distance calculations
- Best of both worlds: AI reasoning + deterministic math

### 5. File-Based Handoff
- Sensor outputs written to files, not blackboard
- Evaluator reads with Python tool when needed
- Report reads all outputs with one tool call
- Reduces blackboard token overhead

## Workflow Changes

### Previous (Phase 1.4.3)
```
ODD Spec → Perception → Motion → Collision → COD Classifier → ODD Compliance → Report
                                              ↑                ↑
                                          reads all          reads COD
                                        window data         + sensor data
                                       from blackboard      from blackboard
```

### New (Phase 1.4.4)
```
ODD Spec → Perception → Motion → Collision → Evaluator → Report
   v5.0.0    v5.0.0     v5.0.0    v5.0.0       v1.0.0     v4.0.0
    ↓          ↓          ↓          ↓            ↓         ↓
  types   per-window  per-window per-window   Python    file-read
           typed       typed      typed        COD       tool
           measures    measures   measures     tool
             ↓           ↓          ↓            ↓
         [files]     [files]    [files]   → [reads files]
```

## Testing Plan

### 1. Unit Tests
- [x] Distance calculations (verified in cod_construction.py)
- [ ] Per-window measurement parsing
- [ ] COD region construction (range/bool/enum)
- [ ] Region metrics computation

### 2. Integration Tests
- [ ] ODD Spec v5.0.0 output format
- [ ] Sensor agent v5.0.0 output format
- [ ] Evaluator tool integration
- [ ] Report tool integration
- [ ] End-to-end workflow

### 3. Validation Scenarios
- [ ] `sim_test_w010_w011` (small, fast)
- [ ] `sim_1_0` subset (representative)
- [ ] Compare outputs with Phase 1.4.3 (sanity check)
- [ ] Measure token usage reduction

### 4. Edge Cases
- [ ] All windows inside ODD (D_violation = 0 for all)
- [ ] All windows outside ODD (high violation distances)
- [ ] Mixed compliance (some in, some out)
- [ ] Boundary cases (M_point ≈ 0)
- [ ] Single-window scenario
- [ ] Missing measurements (graceful degradation)

## Migration Path

### From Phase 1.4.3
1. **Backup current results:** Copy `data/production/` to safe location
2. **Checkout feature branch:** `git checkout feature/phase1.4.4-type-driven-cod`
3. **Test on small scenario:** Run `sim_test_w010_w011`
4. **Validate output structure:** Check JSON schemas
5. **Compare token usage:** Track improvement
6. **Batch regeneration:** Once validated, regenerate all scenarios

### Compatibility
- **Data:** Window files unchanged (still using v1.0.0 format)
- **BEV images:** No changes
- **Manifest:** No changes
- **ODD spec format:** Breaking change (requires regeneration)
- **Agent outputs:** Breaking change (new schemas)

## Next Steps

1. **Immediate:**
   - [ ] Run end-to-end test on `sim_test_w010_w011`
   - [ ] Fix any runtime errors
   - [ ] Validate output JSON structures

2. **Short-term:**
   - [ ] Add comprehensive unit tests
   - [ ] Test with various ODD configurations
   - [ ] Measure actual token savings
   - [ ] Document any issues or edge cases

3. **Medium-term:**
   - [ ] Merge to `dev` after validation
   - [ ] Regenerate all production scenarios
   - [ ] Update evaluation metrics
   - [ ] Write user guide for new architecture

4. **Future Enhancements:**
   - [ ] Custom per-axis weights in distance calculations
   - [ ] Confidence intervals for COD region bounds
   - [ ] Temporal smoothing for noisy measurements
   - [ ] Interactive COD visualization tool

## References

- **ODD/COD Distance Spec:** `docs/ODD_COD_DISTANCE.md`
- **COD Construction Implementation:** `odd_agents/tools/cod_construction.py`
- **Agent Definitions:** `odd_agents/agents/`
- **Workflow Orchestration:** `odd_agents/workflow.py`
- **Previous Architecture:** Phase 1.4.3 (on `dev` branch)

## Notes

- Type system (range/bool/enum) is fundamental - all downstream logic depends on it
- Python tools are deterministic - same inputs always produce same outputs
- LLMs still valuable for reasoning, summarization, and temporal analysis
- File-based data flow reduces memory overhead and enables inspection
- Per-window tracking enables root cause analysis of violations
