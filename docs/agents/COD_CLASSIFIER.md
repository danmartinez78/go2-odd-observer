# COD Classifier Agent

## Overview

The **CodClassifierAgent** (Current Operating Domain Classifier) synthesizes sensor data from perception, motion, and collision analysis to classify the robot's **actual operating conditions** at runtime.

**Key Distinction**: 
- **ODD** = What the robot was *designed* for (specification)
- **COD** = What the robot is *actually experiencing* (reality)

This agent bridges the gap between design assumptions and operational reality.

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
    {"motion_smoothness": "smooth", ...}
  ]
}

// From CollisionSummaryAgent
{
  "collision_events": [
    {"collision_likelihood_score": 0.25, ...}
  ]
}
```

### Outputs

**Output Key:** `temp:cod_classification`

**Schema:**
```json
{
  "cod_classification": {
    "categorical": {
      "environment_type": "indoor_office",
      "lighting_conditions": "bright",
      "terrain_type": "smooth",
      "motion_smoothness": "smooth"
    },
    "numeric": {
      "max_accel_mps2": 1.23,
      "obstacle_density": 0.42,
      "traversability_score": 0.65,
      "collision_risk": 0.28
    }
  },
  "cod_summary": "Robot operating in indoor office environment with bright lighting, smooth terrain, and moderate obstacle density. Motion is smooth with low collision risk."
}
```

### Prompting Strategy

The agent uses **explicit synthesis logic** to extract COD from sensor data:

#### Categorical Axes

**1. environment_type**
```
Source: perception.environment_classification.primary_class
Direct mapping (no aggregation needed)
```

**2. lighting_conditions**
```
Source: perception.per_window_perception[*].lighting_class
Aggregation: Majority vote across windows
Logic: Count occurrences of each class, select most common
```

**3. terrain_type**
```
Source: perception.per_window_perception[*].terrain_roughness_class
Aggregation: Majority vote across windows
Logic: Count occurrences of each class, select most common
```

**4. motion_smoothness**
```
Source: motion.per_window_motion[*].motion_smoothness
Aggregation: Majority vote across windows
Logic: Count occurrences ("smooth", "moderate", "abrupt"), select most common
```

#### Numeric Axes

**1. max_accel_mps2**
```
Source: motion.overall_stats.max_horizontal_accel_mps2
Extraction: Peak acceleration across all windows (already aggregated)
```

**2. obstacle_density**
```
Source: perception.per_window_perception[*].obstacle_density
Aggregation: Average across all windows
Logic: Sum all values, divide by count
```

**3. traversability_score**
```
Source: perception.per_window_perception[*].traversability_score
Aggregation: Average across all windows
Logic: Sum all values, divide by count
```

**4. collision_risk**
```
Source: collision.collision_events[*].collision_likelihood_score
Aggregation: Average across all windows
Logic: Sum all values, divide by count
```

### Key Instruction Patterns

1. **Parse input data**: Extract JSON from all three previous agents
2. **Apply synthesis logic**: Use majority vote for categorical, averaging for numeric
3. **Return ONLY JSON**: No explanations outside schema
4. **Include summary**: Brief human-readable description of COD

**Critical**: The COD schema must exactly match ODD schema structure to enable direct comparison in compliance agent.

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
  "cod_classification": {
    "categorical": {
      "environment_type": "indoor_office",
      "lighting_conditions": "bright",
      "terrain_type": "smooth",
      "motion_smoothness": "smooth"
    },
    "numeric": {
      "max_accel_mps2": 1.23,
      "obstacle_density": 0.53,
      "traversability_score": 0.38,
      "collision_risk": 0.412
    }
  },
  "cod_summary": "Robot operating in indoor office environment with bright lighting and smooth floors. Moderate obstacle density (0.53) with low traversability (0.38) indicating constrained navigation space. Smooth motion with peak acceleration 1.23 m/s². Elevated collision risk (0.412) due to obstacle proximity."
}
```

### Common Issues

**Issue 1: Missing input data**
- **Symptom**: Agent complains about missing perception/motion/collision data
- **Cause**: Previous agents failed or `output_key` misconfigured
- **Fix**: Check logs from PerceptionSummaryAgent, MotionSummaryAgent, CollisionSummaryAgent

**Issue 2: Tied majority vote**
- **Symptom**: Categorical axis has equal counts for multiple classes (e.g., 5 "bright", 5 "dim")
- **Agent behavior**: The LLM will select one based on its reasoning (implementation-dependent: may choose first encountered, most conservative, or use additional context)
- **Expected**: This is acceptable - COD represents best estimate, and the agent's choice should be documented in the cod_summary field

**Issue 3: Extreme numeric values**
- **Symptom**: Averaged values seem unrealistic (e.g., obstacle_density = 0.95)
- **Cause**: One or more windows had extreme readings
- **Fix**: Validate source data or accept that COD represents actual conditions (even if surprising)

**Issue 4: Schema mismatch with ODD**
- **Symptom**: COD has different field names or structure than ODD
- **Cause**: Agent hallucinating schema or misunderstanding prompt
- **Fix**: Agent should strictly follow ODD schema; re-run or debug prompt

### Design Rationale

#### Why Majority Vote for Categorical?

Categorical axes represent discrete states that can vary window-to-window:
- Lighting may change (entering/exiting shadow)
- Terrain may vary (carpet to tile)
- Motion smoothness fluctuates

**Majority vote** selects the dominant condition, giving an overall characterization without averaging meaningless discrete values.

#### Why Averaging for Numeric?

Numeric axes represent continuous measurements:
- Obstacle density varies smoothly (0.3 → 0.5 → 0.4)
- Traversability changes gradually
- Collision risk fluctuates with proximity

**Averaging** provides a representative value for the entire scenario, smoothing out transient spikes while capturing overall trends.

#### Schema Alignment with ODD

The COD schema **exactly mirrors** the ODD specification schema:
```
ODD: categorical_constraints.environment_type.allowed
COD: categorical.environment_type

ODD: numeric_constraints.obstacle_density.in_odd
COD: numeric.obstacle_density
```

This enables direct comparison in OddComplianceAgent:
```python
# Pseudocode
if cod.categorical.environment_type in odd.categorical_constraints.environment_type.allowed:
    compliance = "IN_ODD"
else:
    compliance = "OUT_ODD"
```

---

## Synthesis Logic Examples

### Example 1: Lighting Conditions (Majority Vote)

**Input (per-window):**
```json
[
  {"lighting_class": "bright"},
  {"lighting_class": "bright"},
  {"lighting_class": "dim"},
  {"lighting_class": "bright"}
]
```

**Aggregation:**
```
bright: 3 occurrences
dim: 1 occurrence
Winner: "bright" (majority)
```

**Output:**
```json
{"lighting_conditions": "bright"}
```

### Example 2: Obstacle Density (Averaging)

**Input (per-window):**
```json
[
  {"obstacle_density": 0.35},
  {"obstacle_density": 0.62},
  {"obstacle_density": 0.48},
  {"obstacle_density": 0.55}
]
```

**Aggregation:**
```
Average: (0.35 + 0.62 + 0.48 + 0.55) / 4 = 2.0 / 4 = 0.50
```

**Output:**
```json
{"obstacle_density": 0.50}
```

### Example 3: Complete COD Construction

**Input Data:**
```json
// Perception
{
  "environment_classification": {"primary_class": "indoor_office"},
  "per_window_perception": [
    {"lighting_class": "bright", "terrain_roughness_class": "smooth", "obstacle_density": 0.35, "traversability_score": 0.75},
    {"lighting_class": "bright", "terrain_roughness_class": "smooth", "obstacle_density": 0.48, "traversability_score": 0.60}
  ]
}

// Motion
{
  "overall_stats": {"max_horizontal_accel_mps2": 1.23},
  "per_window_motion": [
    {"motion_smoothness": "smooth"},
    {"motion_smoothness": "smooth"}
  ]
}

// Collision
{
  "collision_events": [
    {"collision_likelihood_score": 0.25},
    {"collision_likelihood_score": 0.35}
  ]
}
```

**COD Output:**
```json
{
  "cod_classification": {
    "categorical": {
      "environment_type": "indoor_office",         // From perception.environment_classification.primary_class
      "lighting_conditions": "bright",             // Majority: 2 bright, 0 dim
      "terrain_type": "smooth",                    // Majority: 2 smooth, 0 others
      "motion_smoothness": "smooth"                // Majority: 2 smooth, 0 others
    },
    "numeric": {
      "max_accel_mps2": 1.23,                     // From motion.overall_stats.max_horizontal_accel_mps2
      "obstacle_density": 0.415,                   // Average: (0.35 + 0.48) / 2
      "traversability_score": 0.675,               // Average: (0.75 + 0.60) / 2
      "collision_risk": 0.30                       // Average: (0.25 + 0.35) / 2
    }
  },
  "cod_summary": "Indoor office environment with bright lighting and smooth terrain. Moderate obstacle density (0.42) with good traversability (0.68). Smooth motion with low collision risk (0.30)."
}
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
