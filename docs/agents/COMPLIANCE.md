# ODD Compliance Agent

## Overview

The **OddComplianceAgent** performs the critical safety function of comparing the robot's **Current Operating Domain (COD)** against its **Operational Design Domain (ODD)** specification to detect violations and warnings.

**Safety-Critical Function**: This agent determines if the robot is operating within its design parameters, approaching limits, or violating safety constraints.

---

## OddComplianceAgent

### Purpose

Compares COD (actual conditions) against ODD (design specifications) and classifies each operational axis as IN_ODD, ODD_BOUNDARY, or OUT_ODD.

**Problem it solves**: Automated safety compliance checking without manual inspection. Enables real-time violation detection, post-incident analysis, and deployment validation.

### Inputs

**From Previous Agents:**
- `{temp:odd_spec?}`: ODD specification from OddSpecAgent
- `{temp:cod_classification?}`: COD classification from CodClassifierAgent

**Schema Expected:**
```json
// ODD Specification
{
  "odd_specification": {
    "categorical_constraints": {
      "environment_type": {"allowed": [...], "prohibited": [...]},
      "lighting_conditions": {"allowed": [...], "prohibited": [...]},
      "terrain_type": {"allowed": [...], "prohibited": [...]}
    },
    "numeric_constraints": {
      "obstacle_density": {"in_odd": [0.0, 0.6], "boundary": [0.6, 0.8], "out_odd": [0.8, 1.0]},
      "traversability_score": {"in_odd": [0.5, 1.0], "boundary": [0.3, 0.5], "out_odd": [0.0, 0.3]},
      "collision_risk": {"in_odd": [0.0, 0.3], "boundary": [0.3, 0.5], "out_odd": [0.5, 1.0]}
    }
  }
}

// COD Classification
{
  "cod_classification": {
    "categorical": {
      "environment_type": "indoor_office",
      "lighting_conditions": "bright",
      "terrain_type": "smooth"
    },
    "numeric": {
      "obstacle_density": 0.53,
      "traversability_score": 0.38,
      "collision_risk": 0.412
    }
  }
}
```

### Outputs

**Output Key:** `temp:odd_compliance`

**Schema:**
```json
{
  "odd_compliance": {
    "categorical_compliance": {
      "environment_type": "IN_ODD",
      "lighting_conditions": "IN_ODD",
      "terrain_type": "IN_ODD",
      "motion_smoothness": "IN_ODD"
    },
    "numeric_compliance": {
      "obstacle_density": "IN_ODD",
      "traversability_score": "OUT_ODD",
      "collision_risk": "ODD_BOUNDARY"
    },
    "overall_compliance": "OUT_ODD",
    "violations": [
      "traversability_score: 0.38 is below the minimum allowed value of 0.5"
    ],
    "warnings": [
      "collision_risk: 0.412 is within the boundary zone [0.3, 0.5]"
    ],
    "compliance_summary": "Robot is OUT_ODD due to low traversability score. Operating in constrained navigation space with elevated collision risk approaching safety boundary. Environment and lighting conditions are compliant."
  }
}
```

### Prompting Strategy

The agent uses **explicit comparison logic** for each constraint type:

#### Categorical Compliance

**Logic:**
```python
if cod.categorical.X in odd.categorical_constraints.X.allowed:
    compliance = "IN_ODD"
elif cod.categorical.X in odd.categorical_constraints.X.prohibited:
    compliance = "OUT_ODD"
else:
    compliance = "IN_ODD"  # Not prohibited = allowed by default
```

**Example:**
```
ODD: environment_type.allowed = ["indoor_office", "indoor_corridor"]
COD: environment_type = "indoor_office"
Result: "IN_ODD" ✅
```

#### Numeric Compliance

**Logic:**
```python
value = cod.numeric.X
in_odd_range = odd.numeric_constraints.X.in_odd
boundary_range = odd.numeric_constraints.X.boundary
out_odd_range = odd.numeric_constraints.X.out_odd

if in_odd_range[0] <= value <= in_odd_range[1]:
    compliance = "IN_ODD"
elif boundary_range[0] <= value <= boundary_range[1]:
    compliance = "ODD_BOUNDARY"
elif out_odd_range[0] <= value <= out_odd_range[1]:
    compliance = "OUT_ODD"
```

**Example:**
```
ODD: obstacle_density = {in_odd: [0.0, 0.6], boundary: [0.6, 0.8], out_odd: [0.8, 1.0]}
COD: obstacle_density = 0.53
Result: "IN_ODD" ✅ (0.53 is in [0.0, 0.6])

ODD: traversability_score = {in_odd: [0.5, 1.0], boundary: [0.3, 0.5], out_odd: [0.0, 0.3]}
COD: traversability_score = 0.38
Result: "ODD_BOUNDARY" ⚠️ (0.38 is in [0.3, 0.5])

ODD: collision_risk = {in_odd: [0.0, 0.3], boundary: [0.3, 0.5], out_odd: [0.5, 1.0]}
COD: collision_risk = 0.68
Result: "OUT_ODD" ❌ (0.68 is in [0.5, 1.0])
```

#### Overall Compliance

**Logic:**
```python
if any constraint is "OUT_ODD":
    overall = "OUT_ODD"
elif any constraint is "ODD_BOUNDARY":
    overall = "ODD_BOUNDARY"
else:
    overall = "IN_ODD"
```

**Rationale**: Single violation triggers OUT_ODD (conservative safety approach).

#### Violations and Warnings

**Violations (OUT_ODD conditions):**
```json
[
  "traversability_score: 0.38 is below the minimum allowed value of 0.5",
  "environment_type: outdoor_urban is prohibited (allowed: indoor_office, indoor_corridor)"
]
```

**Warnings (ODD_BOUNDARY conditions):**
```json
[
  "collision_risk: 0.412 is within the boundary zone [0.3, 0.5]",
  "obstacle_density: 0.65 is approaching the boundary limit of 0.6"
]
```

### Key Instruction Patterns

1. **Parse both inputs**: Extract ODD spec and COD classification
2. **Compare each axis**: Apply categorical/numeric logic
3. **Collect violations**: List all OUT_ODD conditions with values
4. **Collect warnings**: List all ODD_BOUNDARY conditions with values
5. **Determine overall**: OUT_ODD if any violation, else ODD_BOUNDARY if any warning, else IN_ODD
6. **Return ONLY JSON**: No explanations outside schema
7. **Include summary**: Brief assessment of compliance status

### Model Selection

**Default:** `gemini-2.0-flash-lite`  
**Recommended Upgrade:** Not typically needed

**Rationale:**
- Rule-based comparison logic (flash-lite capable)
- Well-defined thresholds and ranges
- No complex reasoning required
- **Keep flash-lite** unless:
  - Debugging comparison logic issues
  - Need more sophisticated violation explanation generation

**Cost Impact:** flash-lite optimal for this task (~70% cheaper than pro)

### Tool Dependencies

**None** - Pure reasoning agent using only LLM logic on input data.

### Example Outputs

#### Example 1: Fully Compliant Operation

**Input:**
```json
// ODD
{
  "categorical_constraints": {
    "environment_type": {"allowed": ["indoor_office"], "prohibited": ["outdoor"]},
    "lighting_conditions": {"allowed": ["bright", "dim"], "prohibited": ["dark"]}
  },
  "numeric_constraints": {
    "obstacle_density": {"in_odd": [0.0, 0.6], "boundary": [0.6, 0.8], "out_odd": [0.8, 1.0]},
    "collision_risk": {"in_odd": [0.0, 0.3], "boundary": [0.3, 0.5], "out_odd": [0.5, 1.0]}
  }
}

// COD
{
  "categorical": {
    "environment_type": "indoor_office",
    "lighting_conditions": "bright"
  },
  "numeric": {
    "obstacle_density": 0.35,
    "collision_risk": 0.18
  }
}
```

**Output:**
```json
{
  "odd_compliance": {
    "categorical_compliance": {
      "environment_type": "IN_ODD",
      "lighting_conditions": "IN_ODD"
    },
    "numeric_compliance": {
      "obstacle_density": "IN_ODD",
      "collision_risk": "IN_ODD"
    },
    "overall_compliance": "IN_ODD",
    "violations": [],
    "warnings": [],
    "compliance_summary": "Robot is fully IN_ODD. Operating within all design parameters with safe obstacle density and low collision risk in compliant indoor office environment."
  }
}
```

#### Example 2: Boundary Warning

**Input:**
```json
// ODD (same as above)

// COD
{
  "categorical": {
    "environment_type": "indoor_office",
    "lighting_conditions": "bright"
  },
  "numeric": {
    "obstacle_density": 0.55,
    "collision_risk": 0.35  // In boundary zone
  }
}
```

**Output:**
```json
{
  "odd_compliance": {
    "categorical_compliance": {
      "environment_type": "IN_ODD",
      "lighting_conditions": "IN_ODD"
    },
    "numeric_compliance": {
      "obstacle_density": "IN_ODD",
      "collision_risk": "ODD_BOUNDARY"
    },
    "overall_compliance": "ODD_BOUNDARY",
    "violations": [],
    "warnings": [
      "collision_risk: 0.35 is within the boundary zone [0.3, 0.5] - approaching safety limit"
    ],
    "compliance_summary": "Robot is at ODD_BOUNDARY due to elevated collision risk. Operating near safety thresholds - caution warranted. Consider reducing speed or improving obstacle avoidance."
  }
}
```

#### Example 3: Violation Detected

**Input:**
```json
// ODD (same as above)

// COD
{
  "categorical": {
    "environment_type": "outdoor_urban",  // Prohibited
    "lighting_conditions": "bright"
  },
  "numeric": {
    "obstacle_density": 0.85,  // OUT_ODD
    "collision_risk": 0.42     // BOUNDARY
  }
}
```

**Output:**
```json
{
  "odd_compliance": {
    "categorical_compliance": {
      "environment_type": "OUT_ODD",
      "lighting_conditions": "IN_ODD"
    },
    "numeric_compliance": {
      "obstacle_density": "OUT_ODD",
      "collision_risk": "ODD_BOUNDARY"
    },
    "overall_compliance": "OUT_ODD",
    "violations": [
      "environment_type: outdoor_urban is prohibited (allowed: indoor_office)",
      "obstacle_density: 0.85 exceeds maximum allowed value of 0.6 (in boundary: 0.6-0.8)"
    ],
    "warnings": [
      "collision_risk: 0.42 is within the boundary zone [0.3, 0.5]"
    ],
    "compliance_summary": "Robot is OUT_ODD due to prohibited environment type and excessive obstacle density. Operating in outdoor environment with dense obstacles, violating design parameters. Immediate corrective action required."
  }
}
```

### Common Issues

**Issue 1: Incorrect boundary classification**
- **Symptom**: Value at exact boundary (e.g., 0.3) classified inconsistently
- **Cause**: Inclusive/exclusive range boundaries
- **Fix**: Prompt specifies inclusive ranges `[a, b]` - value at boundary belongs to zone

**Issue 2: Missing constraints in comparison**
- **Symptom**: COD has field not in ODD (e.g., `max_accel_mps2`)
- **Agent behavior**: Should skip comparison (no constraint = no violation)
- **Expected**: Only compare constraints defined in both ODD and COD

**Issue 3: Conflicting overall assessment**
- **Symptom**: overall_compliance = "IN_ODD" but violations list is non-empty
- **Cause**: Logic error in agent reasoning
- **Fix**: Re-run agent; should follow strict rule: any violation → OUT_ODD

**Issue 4: Vague violation descriptions**
- **Symptom**: Violations list lacks specific values
- **Agent behavior**: Should include both COD value and ODD threshold
- **Expected**: "traversability_score: 0.38 is below minimum 0.5"

### Design Rationale

#### Conservative Safety Approach

The compliance logic is **intentionally conservative**:
- Single violation → Overall OUT_ODD (not averaging or "majority compliance")
- Boundary zone triggers warnings (not ignored until full violation)
- Prohibited environments = immediate OUT_ODD (no gradual warnings)

**Rationale**: Robotics safety requires fail-safe design. One critical violation (e.g., high collision risk) should trigger alerts even if other parameters are compliant.

#### Three-Zone Model Benefits

1. **IN_ODD**: Normal operation, no action needed
2. **ODD_BOUNDARY**: Early warning system, allows corrective action before violation
3. **OUT_ODD**: Safety violation, requires immediate response

This graduated approach enables:
- Preventive warnings (fix issues before failures)
- Graceful degradation (slow down, not emergency stop)
- Audit trail (violations vs. warnings in logs)

#### Violation Specificity

Each violation/warning includes:
- **Which constraint** was violated
- **Actual COD value** observed
- **ODD threshold** that was exceeded

This enables:
- Root cause analysis (which sensor/scenario caused violation)
- Threshold tuning (are ODD specs too strict/loose?)
- Actionable feedback (by how much did we exceed limits?)

---

## Use Cases

### 1. Pre-Deployment Validation
```
Question: Is this new site safe for robot operation?
Process: Run workflow on site test data
Result: overall_compliance = "IN_ODD" → ✅ Approved for deployment
```

### 2. Post-Incident Analysis
```
Question: Why did the robot fail at timestamp X?
Process: Extract windows around incident, run workflow
Result: violations = ["collision_risk: 0.78 exceeded 0.5 limit"]
Finding: Robot operated beyond safe collision risk threshold
```

### 3. Continuous Monitoring
```
Question: Is the robot drifting out of ODD during normal operation?
Process: Run workflow on periodic samples (hourly/daily)
Result: Detect gradual degradation (warnings → violations over time)
Action: Recalibrate, retrain, or restrict deployment area
```

### 4. ODD Refinement
```
Question: Are our ODD specs realistic?
Process: Analyze compliance results across many scenarios
Result: 80% of runs show "obstacle_density boundary warning"
Action: Relax ODD threshold from 0.6 to 0.7 (robot handles it fine)
```

---

## Integration Example

```python
from odd_agents.agents import create_odd_compliance_agent
from google.genai import Client

client = Client(api_key=api_key)

# Create compliance agent
compliance_agent = create_odd_compliance_agent(
    api_key=api_key,
    model="gemini-2.0-flash-lite"
)

# Use in sequential workflow (after ODD spec, COD classification)
from google.adk.agents import SequentialAgent
workflow = SequentialAgent(
    name="ComplianceWorkflow",
    sub_agents=[
        # ... odd_spec_agent ...
        # ... perception agents ...
        # ... motion agents ...
        # ... collision agents ...
        # ... cod_classifier_agent ...
        compliance_agent,  # Compares COD vs ODD
        # ... report_agent ...
    ]
)
```

---

## Related Documentation

- **[Main Agent Architecture](README.md)**: Overall workflow context
- **[ODD Specification Agent](ODD_SPEC.md)**: ODD spec structure
- **[COD Classifier Agent](COD_CLASSIFIER.md)**: COD classification logic
- **[Report Agent](REPORT.md)**: How compliance results are presented
- **[Agent Implementation](../../odd_agents/agents/compliance.py)**: Source code
