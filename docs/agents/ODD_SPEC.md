# ODD Specification Agent

## Overview

The **OddSpecAgent** converts natural language descriptions of a robot's Operational Design Domain (ODD) into formal, structured specifications with precise numerical ranges and categorical constraints.

**Key Innovation**: Enables domain experts to define safety constraints in plain English, which the agent translates into machine-readable specifications for automated compliance checking.

---

## OddSpecAgent

### Purpose

Transforms conversational ODD descriptions into formal specifications with:
- Categorical constraints (environment types, lighting, terrain)
- Numerical ranges with three zones: IN_ODD (safe), BOUNDARY (caution), OUT_ODD (unsafe)

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

**Schema:**
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
        "in_odd": [0.0, 2.0],
        "boundary": [2.0, 5.0],
        "out_odd": [5.0, "inf"]
      },
      "obstacle_density": {
        "in_odd": [0.0, 0.6],
        "boundary": [0.6, 0.8],
        "out_odd": [0.8, 1.0]
      },
      "traversability_score": {
        "in_odd": [0.5, 1.0],
        "boundary": [0.3, 0.5],
        "out_odd": [0.0, 0.3]
      },
      "collision_risk": {
        "in_odd": [0.0, 0.3],
        "boundary": [0.3, 0.5],
        "out_odd": [0.5, 1.0]
      }
    }
  },
  "odd_summary": "Quadruped robot designed for indoor office environments with smooth floors, controlled lighting, and low obstacle density. Maximum speed 1.5 m/s with low collision risk tolerance."
}
```

### Prompting Strategy

The agent uses **expert heuristics** to convert vague descriptions into precise ranges:

#### Speed Interpretation
```
"slow"     → IN_ODD: 0.0-0.5 m/s, BOUNDARY: 0.5-1.0, OUT_ODD: >1.0
"moderate" → IN_ODD: 0.0-1.5 m/s, BOUNDARY: 1.5-2.0, OUT_ODD: >2.0
"fast"     → IN_ODD: 0.0-2.5 m/s, BOUNDARY: 2.5-3.5, OUT_ODD: >3.5

If max speed mentioned: Use as IN_ODD upper bound, add 30% for BOUNDARY
```

#### Obstacle Density (0.0-1.0 scale)
```
"sparse/low"  → IN_ODD: 0.0-0.4, BOUNDARY: 0.4-0.6, OUT_ODD: 0.6-1.0
"moderate"    → IN_ODD: 0.0-0.6, BOUNDARY: 0.6-0.8, OUT_ODD: 0.8-1.0
"dense/high"  → Prohibited (OUT_ODD > 0.8)
```

#### Traversability (0.0-1.0 scale, higher = better)
```
"good/clear"     → IN_ODD: 0.5-1.0, BOUNDARY: 0.3-0.5, OUT_ODD: 0.0-0.3
"challenging"    → IN_ODD: 0.3-0.8, BOUNDARY: 0.2-0.3, OUT_ODD: 0.0-0.2
```

#### Collision Risk (0.0-1.0 scale, higher = worse)
```
"low/safe"  → IN_ODD: 0.0-0.3, BOUNDARY: 0.3-0.5, OUT_ODD: 0.5-1.0
"moderate"  → IN_ODD: 0.0-0.5, BOUNDARY: 0.5-0.7, OUT_ODD: 0.7-1.0

Any mention of "safety" → Use conservative thresholds (0.3 boundary)
```

#### Platform Stability (roll/pitch angles)
```
"stable/flat"  → IN_ODD: 0-15°, BOUNDARY: 15-20°, OUT_ODD: >20°
"slopes ok"    → IN_ODD: 0-20°, BOUNDARY: 20-25°, OUT_ODD: >25°
```

#### Default Assumptions
If a constraint is not mentioned, the agent uses conservative defaults:
```json
{
  "max_accel_mps2": {"in_odd": [0.0, 2.0], "boundary": [2.0, 5.0], "out_odd": [5.0, "inf"]},
  "obstacle_density": {"in_odd": [0.0, 0.6], "boundary": [0.6, 0.8], "out_odd": [0.8, 1.0]},
  "traversability_score": {"in_odd": [0.5, 1.0], "boundary": [0.3, 0.5], "out_odd": [0.0, 0.3]},
  "collision_risk": {"in_odd": [0.0, 0.3], "boundary": [0.3, 0.5], "out_odd": [0.5, 1.0]}
}
```

### Key Instruction Patterns

1. **Extract categorical constraints** from mentions of environment types, lighting, terrain
2. **Infer numerical ranges** using the heuristics above
3. **Define three zones** for each numeric constraint (safety-critical design)
4. **Return ONLY valid JSON** - no explanations outside the schema
5. **Include summary** - brief human-readable description of the ODD

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

#### Example 1: Indoor Office Robot
**Input:**
```
Quadruped robot designed for indoor office navigation.
- Designed for: smooth floors, bright/dim lighting, low obstacles
- Prohibited: outdoor, stairs, dark environments, dense clutter
- Speed limit: 0-1.5 m/s
- Collision risk threshold: <0.3 (low risk only)
```

**Output:**
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
        "in_odd": [0.0, 2.0],
        "boundary": [2.0, 5.0],
        "out_odd": [5.0, "inf"]
      },
      "obstacle_density": {
        "in_odd": [0.0, 0.6],
        "boundary": [0.6, 0.8],
        "out_odd": [0.8, 1.0]
      },
      "traversability_score": {
        "in_odd": [0.5, 1.0],
        "boundary": [0.3, 0.5],
        "out_odd": [0.0, 0.3]
      },
      "collision_risk": {
        "in_odd": [0.0, 0.3],
        "boundary": [0.3, 0.5],
        "out_odd": [0.5, 1.0]
      }
    }
  },
  "odd_summary": "Quadruped robot designed for indoor office environments with smooth floors, controlled lighting, and low obstacle density. Maximum speed 1.5 m/s with strict low collision risk tolerance (<0.3)."
}
```

#### Example 2: Outdoor Delivery Robot
**Input:**
```
Delivery robot for outdoor sidewalk navigation.
- Designed for: outdoor_urban, concrete/asphalt, moderate slopes
- Lighting: bright daylight to dusk (requires daylight)
- Speed: 0-3.0 m/s
- Obstacles: moderate density OK (designed for pedestrians)
- Weather: dry conditions only
```

**Output:**
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
        "in_odd": [0.0, 3.0],
        "boundary": [3.0, 5.0],
        "out_odd": [5.0, "inf"]
      },
      "obstacle_density": {
        "in_odd": [0.0, 0.6],
        "boundary": [0.6, 0.8],
        "out_odd": [0.8, 1.0]
      },
      "traversability_score": {
        "in_odd": [0.3, 1.0],
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
