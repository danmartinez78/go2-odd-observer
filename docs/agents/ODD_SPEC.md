# ODD Specification Agent

## Overview

The **OddSpecAgent** converts natural language descriptions of a robot's Operational Design Domain (ODD) into formal, structured specifications with precise numerical ranges and categorical constraints.

**Key Innovation**: Enables domain experts to define safety constraints in plain English, which the agent translates into machine-readable specifications for automated compliance checking.

---

## OddSpecAgent

### Purpose

Transforms conversational ODD descriptions into formal specifications with:
- Categorical constraints (environment types, lighting, terrain)
- Numerical limits with semantic context (max/min + description + measurement_guidance)

**Phase 1.3 Changes**: Simplified to max/min limits (removed 3-zone in_odd/boundary/out_odd), removed collision_risk, added semantic context fields for measurement consistency

**Problem it solves**: Robotics engineers and safety engineers shouldn't need to manually define complex JSON specifications. This agent interprets vague descriptions ("moderate speed", "low obstacles") and produces precise thresholds.

### Inputs

**From User:**
Natural language ODD description passed as query to the workflow:

```python
nl_odd_description = """
Quadruped robot designed for indoor office navigation.
- Designed for: smooth floors, bright/dim lighting, low obstacles
- Prohibited: outdoor, stairs, dark environments, dense clutter
- Speed limit: 0-1.5 m/s
- Collision risk threshold: <0.3 (low risk only)
"""
```

**No dependencies on previous agents** - This is the first agent in the workflow.

### Outputs

**Output Key:** `temp:odd_spec`

**Schema (Phase 1.3 - Simplified):**
```json
{
  "odd_specification": {
    "categorical_constraints": {
      "environment_type": {
        "allowed": ["indoor_office", "indoor_corridor"],
        "prohibited": ["outdoor_urban", "outdoor_natural", "stairs"]
      },
      "lighting_conditions": {
        "allowed": ["bright", "dim"],
        "prohibited": ["dark", "low_light"]
      },
      "terrain_type": {
        "allowed": ["smooth"],
        "prohibited": ["moderate", "rough", "very_rough"]
      }
    },
    "numeric_constraints": {
      "max_accel_mps2": {
        "max": 10.0,
        "description": "Maximum horizontal acceleration in meters per second squared during agile maneuvers",
        "measurement_guidance": "Extract peak magnitude of horizontal acceleration (sqrt(x² + y²)) from IMU linear_acceleration during observation window. Report peak value, not average."
      },
      "obstacle_density": {
        "max": 0.7,
        "description": "Maximum normalized obstacle density (0-1 scale) in navigation area",
        "measurement_guidance": "Count distinct obstacles in BEV occupancy map, divide by total navigable area, normalize to 0-1 scale where 1.0 = completely obstructed."
      },
      "traversability_score": {
        "min": 0.5,
        "description": "Minimum ease of navigation score (0-1 scale) where 1.0 = completely clear path",
        "measurement_guidance": "Assess from BEV roughness and occupancy: combine surface smoothness + path clearance + obstacle spacing. 1.0 = wide open space, 0.0 = impassable."
      }
    }
  },
  "odd_summary": "Quadruped robot designed for indoor office environments with smooth floors, controlled lighting, and moderate obstacle density. Maximum horizontal acceleration 10 m/s² during agile maneuvers."
}
```

**Key Changes (Phase 1.3):**
- **Simplified numeric constraints**: 3-zone model (in_odd/boundary/out_odd) → simple max/min limits
- **Semantic context added**: 
  - `description`: Human-readable explanation of what the metric represents
  - `measurement_guidance`: Specific instructions for agents on how to measure consistently
- **Collision removed**: `collision_risk` is operational outcome, not environmental constraint
  - Binary `collision_detected` flag handled separately (not part of ODD)
- **Shared vocabulary**: Description + guidance create consistency across Perception, Motion, COD, Evaluator agents

### Prompting Strategy

The agent uses **expert heuristics** to convert vague descriptions into precise ranges:

#### Speed Interpretation
```
"slow"     → max: 0.5 m/s (design limit)
"moderate" → max: 1.5 m/s (design limit)
"fast"     → max: 2.5 m/s (design limit)

If max speed explicitly mentioned: Use as max limit directly
```

#### Obstacle Density (0.0-1.0 scale)
```
"sparse/low"  → max: 0.4 (normalized density on 0-1 scale)
"moderate"    → max: 0.6 (normalized density on 0-1 scale)
"dense/high"  → max: 0.8 (normalized density on 0-1 scale)
```

#### Traversability (0.0-1.0 scale, higher = better)
```
"good/clear"     → min: 0.5 (minimum acceptable navigability)
"challenging"    → min: 0.3 (lower threshold for difficult terrain)
```

#### Acceleration (m/s²)
```
"low/gentle"   → max: 2.0 m/s²
"moderate"     → max: 5.0 m/s²
"high/agile"   → max: 10.0 m/s²
```

**Phase 1.3 Note**: collision_risk removed from ODD spec (operational outcome, not environmental constraint). Binary collision_detected flag handled separately.

#### Default Assumptions (Phase 1.3)
If a constraint is not mentioned, the agent uses conservative defaults:
```json
{
  "max_accel_mps2": {
    "max": 10.0,
    "description": "Maximum horizontal acceleration during agile maneuvers",
    "measurement_guidance": "Extract peak magnitude from IMU linear_acceleration (x,y) during window"
  },
  "obstacle_density": {
    "max": 0.6,
    "description": "Normalized obstacle density (0-1 scale, higher = more cluttered)",
    "measurement_guidance": "Count valid obstacles / total grid cells in BEV projection"
  },
  "traversability_score": {
    "min": 0.5,
    "description": "Minimum navigability score (0-1 scale, higher = more navigable)",
    "measurement_guidance": "Weighted combination: terrain smoothness + clearance + stability"
  }
}
```

**Semantic Context Fields (Phase 1.3)**:
- `description`: Human-readable explanation of what the metric represents
- `measurement_guidance`: Specific instructions for agents to ensure consistent measurement across perception/motion/COD

### Key Instruction Patterns (Phase 1.3)

1. **Extract categorical constraints** from mentions of environment types, lighting, terrain
2. **Infer numerical limits** using the heuristics above (max/min only, no 3-zone)
3. **Add semantic context** for each numeric constraint (description + measurement_guidance)
4. **Return ONLY valid JSON** - no explanations outside the schema
5. **Include summary** - brief human-readable description of the ODD
6. **DO NOT include collision_risk** - operational outcome, not environmental constraint

### Model Selection

**Default:** `gemini-2.0-flash-lite`  
**Recommended Upgrade:** Not typically needed

**Rationale:**
- JSON synthesis task (flash-lite capable)
- Heuristics are well-defined in prompt
- No multimodal analysis required
- **Keep flash-lite** unless:
  - Complex/ambiguous ODD descriptions requiring deep reasoning
  - Multiple conflicting constraints needing reconciliation

**Cost Impact:** flash-lite optimal for this task (~70% cheaper than pro)

### Tool Dependencies

**None** - Pure LLM reasoning, no external tools required.

### Example Outputs

#### Example 1: Indoor Office Robot (Phase 1.3)
**Input:**
```
Quadruped robot designed for indoor office navigation.
- Designed for: smooth floors, bright/dim lighting, low obstacles
- Prohibited: outdoor, stairs, dark environments, dense clutter
- Speed limit: 0-1.5 m/s (maximum horizontal velocity)
```

**Output (Phase 1.3):**
```json
{
  "odd_specification": {
    "categorical_constraints": {
      "environment_type": {
        "allowed": ["indoor_office", "indoor_corridor"],
        "prohibited": ["outdoor_urban", "outdoor_natural", "stairs"]
      },
      "lighting_conditions": {
        "allowed": ["bright", "dim"],
        "prohibited": ["dark", "low_light"]
      },
      "terrain_type": {
        "allowed": ["smooth"],
        "prohibited": ["moderate", "rough", "very_rough"]
      }
    },
    "numeric_constraints": {
      "max_accel_mps2": {
        "max": 2.0,
        "description": "Maximum horizontal acceleration during navigation (gentle acceleration for indoor safety)",
        "measurement_guidance": "Extract peak magnitude from IMU linear_acceleration (x,y) during window"
      },
      "obstacle_density": {
        "max": 0.6,
        "description": "Normalized obstacle density (0-1 scale) - low density for office environment",
        "measurement_guidance": "Count valid obstacles / total grid cells in BEV projection"
      },
      "traversability_score": {
        "min": 0.5,
        "description": "Minimum navigability score (0-1 scale, higher = more navigable) - require good clearance",
        "measurement_guidance": "Weighted combination: terrain smoothness + clearance + stability"
      }
    }
  },
  "odd_summary": "Quadruped robot designed for indoor office environments with smooth floors, controlled lighting (bright/dim), and low obstacle density. Maximum acceleration 2.0 m/s² for safe indoor navigation."
}
```

#### Example 2: Outdoor Delivery Robot (Phase 1.3)
**Input:**
```
Delivery robot for outdoor sidewalk navigation.
- Designed for: outdoor_urban, concrete/asphalt, moderate slopes
- Lighting: bright daylight to dusk (requires daylight)
- Speed: 0-3.0 m/s
- Obstacles: moderate density OK (designed for pedestrians)
- Weather: dry conditions only
```

**Output (Phase 1.3):**
```json
{
  "odd_specification": {
    "categorical_constraints": {
      "environment_type": {
        "allowed": ["outdoor_urban"],
        "prohibited": ["indoor", "outdoor_natural", "stairs"]
      },
      "lighting_conditions": {
        "allowed": ["bright", "dim"],
        "prohibited": ["dark", "low_light"]
      },
      "terrain_type": {
        "allowed": ["smooth", "moderate"],
        "prohibited": ["rough", "very_rough"]
      }
    },
    "numeric_constraints": {
      "max_accel_mps2": {
        "max": 5.0,
        "description": "Maximum horizontal acceleration for outdoor maneuvers",
        "measurement_guidance": "Extract peak magnitude from IMU linear_acceleration (x,y) during window"
      },
      "obstacle_density": {
        "max": 0.6,
        "description": "Normalized obstacle density (0-1 scale) - moderate density for pedestrian areas",
        "measurement_guidance": "Count valid obstacles / total grid cells in BEV projection"
      },
      "traversability_score": {
        "min": 0.3,
        "description": "Minimum navigability score (0-1 scale) - tolerate moderate slopes",
        "measurement_guidance": "Weighted combination: terrain smoothness + clearance + stability"
      }
    }
  },
  "odd_summary": "Delivery robot for outdoor urban sidewalk navigation with moderate terrain tolerance. Maximum acceleration 5.0 m/s² for faster outdoor speeds. Requires daylight conditions (bright/dim), dry weather only."
}
        "boundary": [0.2, 0.3],
        "out_odd": [0.0, 0.2]
      },
      "collision_risk": {
        "in_odd": [0.0, 0.5],
        "boundary": [0.5, 0.7],
        "out_odd": [0.7, 1.0]
      }
    }
  },
  "odd_summary": "Outdoor delivery robot designed for urban sidewalks with moderate terrain variation and pedestrian obstacles. Maximum speed 3.0 m/s in daylight/dusk conditions, dry weather only."
}
```

### Common Issues

**Issue 1: Conflicting constraints**
- **Symptom**: User describes "high speed" but also "high obstacle density" (unsafe combination)
- **Agent behavior**: Should use conservative thresholds and include warning in summary
- **Fix**: Clarify ODD description or accept agent's conservative interpretation

**Issue 2: Ambiguous speed descriptions**
- **Symptom**: "Normal speed" or "typical speed" - unclear mapping
- **Agent behavior**: Should use default moderate range (0-1.5 m/s) and explain in summary
- **Fix**: Provide specific speed values in m/s

**Issue 3: Missing constraints**
- **Symptom**: User doesn't mention collision risk or traversability
- **Agent behavior**: Uses default conservative thresholds
- **Expected**: This is correct behavior - defaults ensure safety

**Issue 4: Non-standard environment types**
- **Symptom**: User mentions "warehouse" or "parking lot" (not in standard taxonomy)
- **Agent behavior**: Should map to closest standard type (warehouse → indoor, parking lot → outdoor_urban)
- **Fix**: Use standard taxonomy or accept agent's mapping

### Design Rationale

#### Three-Zone Safety Model
The ODD uses three zones for numerical constraints:

1. **IN_ODD**: Normal operating conditions, fully supported
2. **BOUNDARY**: Approaching design limits, caution warranted
3. **OUT_ODD**: Beyond design parameters, unsafe operation

This mirrors industrial safety standards (e.g., ISO 13849) and enables graduated warnings rather than binary pass/fail.

#### Conservative Defaults
When in doubt, the agent uses conservative thresholds:
- Lower speed limits
- Stricter collision risk thresholds
- Higher traversability requirements

This "fail-safe" approach prevents over-confidence in unsafe operating conditions.

#### Categorical vs. Numerical
- **Categorical**: Discrete choices (indoor/outdoor, bright/dark)
- **Numerical**: Continuous ranges (speed, acceleration, density)

The agent extracts both types and maintains them separately for different downstream reasoning:
- Categorical: Simple allowed/prohibited checks
- Numerical: Zone-based threshold evaluation

---

## Integration Example

```python
from odd_agents.agents import create_odd_spec_agent
from google.genai import Client

client = Client(api_key=api_key)

# Create ODD specification agent
odd_spec_agent = create_odd_spec_agent(
    api_key=api_key,
    model="gemini-2.0-flash-lite"
)

# Use in workflow
from google.adk.runners import InMemoryRunner
runner = InMemoryRunner()

nl_odd_description = """
Quadruped robot designed for indoor office navigation.
- Designed for: smooth floors, bright/dim lighting, low obstacles
- Speed limit: 0-1.5 m/s
- Collision risk threshold: <0.3
"""

result = await runner.run(
    agent=odd_spec_agent,
    user_message=nl_odd_description
)
```

---

## Related Documentation

- **[Main Agent Architecture](README.md)**: Overall workflow context
- **[ODD Compliance Agent](COMPLIANCE.md)**: How ODD spec is used for compliance checking
- **[COD Classifier](COD_CLASSIFIER.md)**: Current Operating Domain classification
- **[Agent Implementation](../../odd_agents/agents/odd_spec.py)**: Source code
