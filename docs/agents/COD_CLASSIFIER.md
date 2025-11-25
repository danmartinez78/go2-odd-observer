# COD Classifier Agent

## Overview

The **CodMeasurementAgent** (Current Operating Domain Measurement) synthesizes sensor data from perception, motion, and collision analysis to measure the robot's **actual operating conditions** at runtime.

**Key Distinction**: 
- **ODD** = What the robot was *designed* for (specification)
- **COD** = What the robot is *actually experiencing* (measurements)
- **Evaluator** = Compares COD vs ODD, calculates distance from limits (Phase 1.4)

**Phase 1.3 Redesign**: This agent is now **measurement-only** (no compliance checking). It extracts per-window measurements and constructs the operational region (min/max ranges). The Evaluator agent (Phase 1.4) will handle compliance analysis and distance-from-limits calculation.

---

## CodClassifierAgent

### Purpose

Classifies the robot's current operating domain from multi-stage sensor analysis, enabling comparison against the ODD specification.

**Problem it solves**: Raw sensor data (camera images, IMU readings, LiDAR maps) must be aggregated into a unified domain representation that matches the ODD specification schema for automated compliance checking.

### Inputs

**From Previous Agents:**
- `{temp:perception_output?}`: Perception analysis results
- `{temp:motion_output?}`: Motion analysis results
- `{temp:collision_output?}`: Collision risk analysis results

**Schema Expected:**
```json
// From PerceptionSummaryAgent
{
  "environment_classification": {"primary_class": "indoor_office", ...},
  "per_window_perception": [
    {"lighting_class": "bright", "terrain_roughness_class": "smooth", "obstacle_density": 0.35, "traversability_score": 0.75, ...}
  ]
}

// From MotionSummaryAgent
{
  "overall_stats": {"max_horizontal_accel_mps2": 1.23, ...},
  "per_window_motion": [
    {"peak_horizontal_accel_mps2": 0.85, ...},
    {"peak_horizontal_accel_mps2": 1.23, ...}
  ]
}
```

### Outputs

**Output Key:** `temp:cod_measurements`

**Schema (Phase 1.3 - Measurement-Only):**
```json
{
  "per_window_measurements": [
    {
      "window_id": "w001",
      "max_accel_mps2": 1.23,
      "obstacle_density": 0.42,
      "traversability_score": 0.65
    },
    {
      "window_id": "w002",
      "max_accel_mps2": 2.15,
      "obstacle_density": 0.68,
      "traversability_score": 0.38
    }
  ],
  "cod_region": {
    "categorical": {
      "environment_type": ["indoor_office"],
      "lighting_conditions": ["bright", "dim"],
      "terrain_type": ["smooth"]
    },
    "numeric": {
      "max_accel_mps2": {"min": 1.23, "max": 2.15},
      "obstacle_density": {"min": 0.42, "max": 0.68},
      "traversability_score": {"min": 0.38, "max": 0.65}
    }
  },
  "statistics": {
    "total_windows": 2,
    "categorical_diversity": {
      "lighting_conditions": 2
    }
  },
  "cod_summary": "Robot operated in indoor office environment across 2 observation windows. Lighting varied between bright and dim. Horizontal acceleration ranged 1.23-2.15 m/s², obstacle density 0.42-0.68, traversability 0.38-0.65. Lowest traversability in window w002 (0.38)."
}
```

**Key Changes (Phase 1.3):**
- **Per-window data preserved**: No averaging, all measurements retained
- **Region construction**: Min/max ranges for numeric axes, unique values for categorical
- **No compliance checking**: Removed per_window_compliance (deferred to Evaluator)
- **Collision separate**: `collision_detected` boolean handled separately (not in numeric measurements)
- **Statistical summary**: Provides context (total windows, diversity metrics)

### Prompting Strategy

The agent uses **region-based extraction** to construct the multidimensional operational envelope:

#### Categorical Axes - Collect ALL Observed Values

**1. environment_type**
```
Source: perception.environment_classification.primary_class
Extraction: Collect unique values across all windows (set union)
CRITICAL: Preserve EXACT values (e.g., "indoor_office" not simplified to "indoor")
Example: ["indoor_office"]  // Single environment observed
Example: ["indoor_office", "indoor_corridor"]  // Transition between two environments
```

**2. lighting_conditions**
```
Source: perception.per_window_perception[*].lighting_class
Extraction: Collect unique values across all windows
Example: ["bright", "dim"]  // Robot experienced both lighting conditions
```

**3. terrain_type**
```
Source: perception.per_window_perception[*].terrain_roughness_class
Extraction: Collect unique values across all windows
Example: ["smooth"]  // Single terrain type observed
Example: ["smooth", "slightly_rough"]  // Terrain variation encountered
```

#### Numeric Axes - Extract Min/Max Ranges

**1. max_accel_mps2**
```
Source: motion.per_window_motion[*].peak_horizontal_accel_mps2
Extraction: Min and max across all window observations
Field normalization: Renamed to match ODD spec schema (max_accel_mps2)
Example: {"min": 0.1, "max": 2.15}  // Acceleration ranged from 0.1 to 2.15 m/s²
```

**2. obstacle_density**
```
Source: perception.per_window_perception[*].obstacle_density
Extraction: Min and max across all windows
Example: {"min": 0.42, "max": 0.68}  // Density varied from sparse to moderate
```

**3. traversability_score**
```
Source: perception.per_window_perception[*].traversability_score
Extraction: Min and max across all windows
Example: {"min": 0.38, "max": 0.82}  // Traversability degraded at some points
Note: Low min value indicates constrained navigation encountered
```

**Phase 1.3 Note**: Redundant `"range": [min, max]` field removed - use `min` and `max` directly.

### Key Instruction Patterns

1. **Extract per-window measurements**: Preserve all observations without averaging
2. **Construct COD region**: Union of categorical values, min/max of numeric values
3. **No compliance logic**: Pure measurement agent (Evaluator handles compliance in Phase 1.4)
4. **Preserve exact values**: Especially environment_type from perception (no simplification)
5. **Field normalization**: Translate source field names to ODD schema for compliance matching
6. **Return ONLY JSON**: No explanations outside schema

### Phase 1.3 Design Rationale

**Why Region-Based (Not Averaged Point)?**

Phase 1.2 (old approach):
```json
// Averaged to single point - LOSES DATA!
{"obstacle_density": 0.55}  // Average of [0.4, 0.7] hides 0.7 peak
```

Phase 1.3 (new approach):
```json
// Region preserves operational envelope
{"obstacle_density": {"min": 0.4, "max": 0.7}}  // Full range visible
```

**Benefits**:
- ✅ No violations lost to averaging (e.g., single dark window won't be averaged away)
- ✅ Evaluator can calculate "distance from limits" (e.g., 0.7 vs 0.6 limit = 16.7% overage)
- ✅ Severity scoring based on peak values + frequency (not just averages)
- ✅ Per-window compliance tracking (Evaluator compares each window individually)

### Model Selection

**Default:** `gemini-2.0-flash-lite`  
**Recommended Upgrade:** Not typically needed

**Rationale:**
- Simple data aggregation task (flash-lite capable)
- Well-defined synthesis logic in prompt
- No complex reasoning required
- **Keep flash-lite** unless:
  - Debugging aggregation logic issues
  - Need more sophisticated handling of edge cases (e.g., tied majority votes)

**Cost Impact:** flash-lite optimal for this task (~70% cheaper than pro)

### Tool Dependencies

**None** - Pure synthesis agent using only LLM reasoning on input data.

### Example Output

**Scenario: Indoor office robot with moderate activity**

```json
{
**Input (Complete Data):**
```json
{
  "perception": {
    "environment_classification": {"primary_class": "indoor_office"},
    "per_window_perception": [
      {"lighting_class": "bright", "terrain_roughness_class": "smooth", "obstacle_density": 0.35, "traversability_score": 0.65},
      {"lighting_class": "bright", "terrain_roughness_class": "smooth", "obstacle_density": 0.48, "traversability_score": 0.58},
      {"lighting_class": "dim", "terrain_roughness_class": "smooth", "obstacle_density": 0.62, "traversability_score": 0.38}
    ]
  },
  "motion": {
    "per_window_motion": [
      {"peak_horizontal_accel_mps2": 0.85},
      {"peak_horizontal_accel_mps2": 1.23},
      {"peak_horizontal_accel_mps2": 0.97}
    ]
  }
}
```

**COD Region (Phase 1.3):**
```json
{
  "per_window_measurements": [...],  // Full detail preserved
  "cod_region": {
    "categorical": {
      "environment_type": ["indoor_office"],
      "lighting_conditions": ["bright", "dim"],
      "terrain_type": ["smooth"]
    },
    "numeric": {
      "max_accel_mps2": {"min": 0.85, "max": 1.23},
      "obstacle_density": {"min": 0.35, "max": 0.62},
      "traversability_score": {"min": 0.38, "max": 0.65}
    }
  },
  "statistics": {
    "total_windows": 3,
    "total_duration_s": 15.0,
    "categorical_distribution": {
      "lighting_conditions": {"bright": 2, "dim": 1}
    },
    "numeric_statistics": {
      "max_accel_mps2": {"mean": 1.02, "std": 0.19},
      "obstacle_density": {"mean": 0.48, "std": 0.14}
    }
  }
}
```

**Interpretation**: 
- Categorical axes capture all observed states (lighting varied bright→dim)
- Numeric axes preserve operational envelope (acceleration 0.85-1.23 m/s²)
- Statistics provide distribution context (2/3 windows bright)
- Per-window detail retained for downstream analysis
```

### Common Issues

**Issue 1: Missing input data**
- **Symptom**: Agent complains about missing perception/motion data
- **Cause**: Previous agents failed or `output_key` misconfigured
- **Fix**: Check logs from PerceptionSummaryAgent, MotionSummaryAgent

**Issue 2: Environment type mismatch**
- **Symptom**: COD region has simplified environment (e.g., "indoor" instead of "indoor_office")
- **Cause**: Agent not preserving exact perception.environment_classification.primary_class
- **Fix**: COD must extract EXACTLY from source (no simplification)
- **Phase 1.3 Fix**: Added explicit warnings in prompt to preserve full specificity

**Issue 3: Redundant range field**
- **Symptom**: Numeric regions have both `{"min": 0.2, "max": 0.8}` AND `"range": [0.2, 0.8]`
- **Cause**: Old Phase 1.2 schema template
- **Fix**: Phase 1.3 removed redundant range field - use min/max directly

**Issue 4: Empty categorical sets**
- **Symptom**: Categorical axis has empty array (e.g., `"lighting_conditions": []`)
- **Cause**: All windows missing lighting_class data
- **Fix**: Validate source data quality or mark as "unknown" if truly missing

**Issue 5: Schema mismatch with ODD**
- **Symptom**: COD has different field names than ODD
- **Cause**: Agent hallucinating schema or misunderstanding field normalization
- **Fix**: Agent should normalize field names to match ODD schema (e.g., peak_horizontal_accel_mps2 → max_accel_mps2)

### Design Rationale

#### Why Region-Based (Not Single Point)?

**Phase 1.2 Limitation (Averaged Point)**:
```json
{"obstacle_density": 0.48}  // Average of [0.35, 0.62] - lost peak 0.62!
```
- ❌ Violations averaged away (single dark window → bright average)
- ❌ No distance-from-limit calculation possible
- ❌ Severity scoring impossible (no peak values)

**Phase 1.3 Solution (Operational Envelope)**:
```json
{"obstacle_density": {"min": 0.35, "max": 0.62}}  // Full range preserved
```
- ✅ All conditions visible (bright AND dim experienced)
- ✅ Evaluator can calculate overage (0.62 vs 0.6 limit = 3.3% over)
- ✅ Per-window compliance tracking (each window checked individually)
- ✅ Severity = magnitude × frequency (both captured)

#### Why Set Union for Categorical?

Categorical axes represent discrete states:
- Lighting: `["bright", "dim"]` → robot handled both conditions
- Terrain: `["smooth", "slightly_rough"]` → terrain varied
- Environment: `["indoor_office"]` → single environment (if transitions occur, both appear)

**Set union** captures all observed states without data loss.

#### Why Min/Max for Numeric?

Numeric axes represent continuous measurements:
- Acceleration: `{"min": 0.85, "max": 1.23}` → operational range 0.85-1.23 m/s²
- Density: `{"min": 0.35, "max": 0.62}` → sparse to moderate obstacles
- Traversability: `{"min": 0.38, "max": 0.65}` → constrained at worst point

**Min/max range** defines operational envelope boundaries for compliance checking.

#### Schema Alignment with ODD

Phase 1.3 COD schema **enables direct region comparison** with ODD limits:
```
ODD: categorical_constraints.environment_type.allowed = ["indoor_office", "indoor_corridor"]
COD: categorical.environment_type = ["indoor_office"]
Check: All COD values ⊆ ODD allowed? ✅ YES

ODD: numeric_constraints.obstacle_density.max = 0.6
COD: numeric.obstacle_density = {"min": 0.35, "max": 0.62}
Check: COD.max > ODD.max? ⚠️ YES (0.62 > 0.6, violation by 3.3%)
```

This enables Phase 1.4 Evaluator to:
1. Check categorical subset compliance (set containment)
2. Calculate numeric distance from limits (percentage overage)
3. Score severity (magnitude × frequency from statistics)

---

## Region Construction Examples

### Example 1: Lighting Conditions (Set Union)

**Input (per-window):**
```json
[
  {"lighting_class": "bright"},
  {"lighting_class": "bright"},
  {"lighting_class": "dim"},
  {"lighting_class": "bright"}
]
```

**COD Region:**
```json
{"lighting_conditions": ["bright", "dim"]}
```
**Interpretation**: Robot experienced both bright and dim lighting (not just majority "bright")

---

### Example 2: Obstacle Density (Min/Max Range)

**Input (per-window):**
```json
[
  {"obstacle_density": 0.35},
  {"obstacle_density": 0.62},
  {"obstacle_density": 0.48},
  {"obstacle_density": 0.55}
]
```

**COD Region:**
```json
{"obstacle_density": {"min": 0.35, "max": 0.62}}
```
**Interpretation**: Density ranged from sparse (0.35) to moderate (0.62)

---

### Example 3: Complete COD Construction

**Complete Example (Detailed):**

See "### Example 3: Complete COD Construction" earlier in document for full input → region construction flow.
```

---

## Integration Example

```python
from odd_agents.agents import create_cod_classifier_agent
from google.genai import Client

client = Client(api_key=api_key)

# Create COD classifier agent
cod_agent = create_cod_classifier_agent(
    api_key=api_key,
    model="gemini-2.0-flash-lite"
)

# Use in sequential workflow (after perception, motion, collision)
from google.adk.agents import SequentialAgent
workflow = SequentialAgent(
    name="AnalysisWorkflow",
    sub_agents=[
        # ... perception agents ...
        # ... motion agents ...
        # ... collision agents ...
        cod_agent,  # Synthesizes COD from previous outputs
        # ... compliance and report agents ...
    ]
)
```

---

## Related Documentation

- **[Main Agent Architecture](README.md)**: Overall workflow context
- **[ODD Specification Agent](ODD_SPEC.md)**: ODD spec structure and schema
- **[ODD Compliance Agent](COMPLIANCE.md)**: How COD is compared against ODD
- **[Perception Agents](PERCEPTION.md)**: Source of environment/obstacle data
- **[Motion Agents](MOTION.md)**: Source of motion dynamics data
- **[Collision Agents](COLLISION.md)**: Source of collision risk data
- **[Agent Implementation](../../odd_agents/agents/cod_classifier.py)**: Source code
