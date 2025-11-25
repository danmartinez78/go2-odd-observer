# ODD Compliance Agent

## Overview

**⚠️ PHASE 1.3 STATUS: This agent is being redesigned as the Evaluator Agent in Phase 1.4**

The **OddComplianceAgent** (becoming **Evaluator** in Phase 1.4) performs the critical safety function of comparing the robot's **Current Operating Domain (COD)** against its **Operational Design Domain (ODD)** specification to detect violations and calculate distance from design limits.

**Safety-Critical Function**: This agent determines if the robot is operating within its design parameters and quantifies how far beyond limits violations extend.

**Phase 1.3 Changes:**
- Removed `collision_risk` from numeric compliance checks (collision is operational outcome, not environmental constraint)
- Binary `collision_detected` flag handled separately as safety event

**Phase 1.4 Planned Changes:**
- Rename: OddComplianceAgent → Evaluator
- Region-based comparison: Compare COD min/max ranges vs ODD limits
- Distance calculation: Quantify violation magnitude (e.g., 15 m/s² vs 10 m/s² limit = 50% overage)
- Severity scoring: Based on magnitude × frequency of violations
- Per-window compliance tracking: No violations lost to averaging

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
      "max_accel_mps2": {
        "max": 10.0,
        "description": "Maximum horizontal acceleration during agile maneuvers",
        "measurement_guidance": "Extract peak magnitude from IMU linear_acceleration (x,y)"
      },
      "obstacle_density": {
        "max": 0.6,
        "description": "Normalized obstacle density (0-1 scale)",
        "measurement_guidance": "Count valid obstacles / total grid cells in BEV"
      },
      "traversability_score": {
        "min": 0.5,
        "description": "Minimum navigability score (0-1 scale, higher = more navigable)",
        "measurement_guidance": "Weighted combination: terrain smoothness + clearance + stability"
      }
    }
  }
}

// COD Classification (Phase 1.3 - Region-Based)
{
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
    "categorical_distribution": {
      "lighting_conditions": {"bright": 2, "dim": 1}
    }
  }
}
```

### Outputs

**Output Key:** `temp:odd_compliance`

**Schema (Phase 1.3 - Simple In/Out Compliance):**
```json
{
  "odd_compliance": {
    "categorical_compliance": {
      "environment_type": "IN_ODD",  // All values in allowed list
      "lighting_conditions": "IN_ODD",  // All values in allowed list
      "terrain_type": "IN_ODD"  // All values in allowed list
    },
    "numeric_compliance": {
      "max_accel_mps2": "IN_ODD",  // max <= ODD max limit
      "obstacle_density": "OUT_ODD",  // max > ODD max limit (0.62 > 0.6)
      "traversability_score": "OUT_ODD"  // min < ODD min limit (0.38 < 0.5)
    },
    "overall_compliance": "OUT_ODD",
    "violations": [
      "obstacle_density: max 0.62 exceeds limit 0.6 (violation in window w002)",
      "traversability_score: min 0.38 below limit 0.5 (violation in window w003)"
    ],
    "compliance_summary": "Robot is OUT_ODD due to obstacle density spike (0.62 vs 0.6 limit) and low traversability point (0.38 vs 0.5 limit). Operating in constrained navigation space. Environment and lighting conditions compliant."
  },
  "collision_detected": true  // Binary flag handled separately (not part of ODD compliance)
}
```

### Prompting Strategy

The agent uses **explicit comparison logic** for each constraint type:

#### Categorical Compliance (Phase 1.3 - Set Containment)

**Logic:**
```python
# Phase 1.3: Check if ALL observed values are in allowed list
cod_values = cod.categorical.X  # List of values (e.g., ["indoor_office", "indoor_corridor"])
allowed = odd.categorical_constraints.X.allowed  # List of allowed values
prohibited = odd.categorical_constraints.X.prohibited  # List of prohibited values

if any(v in prohibited for v in cod_values):
    compliance = "OUT_ODD"  # Any prohibited value = violation
elif all(v in allowed for v in cod_values):
    compliance = "IN_ODD"  # All values allowed = compliant
else:
    compliance = "OUT_ODD"  # Any value not in allowed list = violation
```

**Examples:**
```
# Example 1: Single environment (compliant)
ODD: environment_type.allowed = ["indoor_office", "indoor_corridor"]
COD: environment_type = ["indoor_office"]
Result: "IN_ODD" ✅ (all values in allowed list)

# Example 2: Multiple environments (compliant)
ODD: environment_type.allowed = ["indoor_office", "indoor_corridor"]
COD: environment_type = ["indoor_office", "indoor_corridor"]
Result: "IN_ODD" ✅ (all values in allowed list)

# Example 3: Prohibited environment (violation)
ODD: environment_type.prohibited = ["outdoor_urban"]
COD: environment_type = ["indoor_office", "outdoor_urban"]
Result: "OUT_ODD" ❌ (outdoor_urban is prohibited)

# Example 4: Unexpected environment (violation)
ODD: environment_type.allowed = ["indoor_office"]
COD: environment_type = ["indoor_office", "indoor_residential"]
Result: "OUT_ODD" ❌ (indoor_residential not in allowed list)
```

#### Numeric Compliance (Phase 1.3 - Range Checking)

**Logic:**
```python
# Phase 1.3: Check if COD range violates ODD limits
cod_min = cod.numeric.X.min
cod_max = cod.numeric.X.max

# Check max limit (if defined in ODD)
if "max" in odd.numeric_constraints.X:
    odd_max = odd.numeric_constraints.X.max
    if cod_max > odd_max:
        compliance = "OUT_ODD"  # Exceeded upper limit

# Check min limit (if defined in ODD)
if "min" in odd.numeric_constraints.X:
    odd_min = odd.numeric_constraints.X.min
    if cod_min < odd_min:
        compliance = "OUT_ODD"  # Below lower limit

# If no violations
if no violations:
    compliance = "IN_ODD"
```

**Examples:**
```
# Example 1: Within limits (compliant)
ODD: obstacle_density.max = 0.6
COD: obstacle_density = {"min": 0.35, "max": 0.58}
Result: "IN_ODD" ✅ (0.58 <= 0.6)

# Example 2: Exceeds max limit (violation)
ODD: obstacle_density.max = 0.6
COD: obstacle_density = {"min": 0.35, "max": 0.62}
Result: "OUT_ODD" ❌ (0.62 > 0.6, overage = 3.3%)

# Example 3: Below min limit (violation)
ODD: traversability_score.min = 0.5
COD: traversability_score = {"min": 0.38, "max": 0.72}
Result: "OUT_ODD" ❌ (0.38 < 0.5, shortfall = 24%)

# Example 4: Both limits violated (violation)
ODD: max_accel_mps2.max = 10.0
COD: max_accel_mps2 = {"min": 0.5, "max": 12.3}
Result: "OUT_ODD" ❌ (12.3 > 10.0, overage = 23%)
```

**Phase 1.4 Enhancement (Planned):**
- Distance calculation: `(cod_max - odd_max) / odd_max * 100` = percentage overage
- Severity scoring: `overage_percentage × violation_frequency`
- Per-window tracking: Identify which specific windows violated (from per_window_measurements)

#### Overall Compliance (Phase 1.3 - Binary In/Out)

**Logic:**
```python
if any constraint is "OUT_ODD":
    overall = "OUT_ODD"
else:
    overall = "IN_ODD"
```

**Rationale**: Single violation triggers OUT_ODD (conservative safety approach). Phase 1.3 removed ODD_BOUNDARY zone (now simple max/min limits).

**Phase 1.4 Enhancement**: Overall compliance will include severity score based on violation magnitude and frequency.

#### Violations (Phase 1.3 - Range-Based)

**Format:**
```json
{
  "violations": [
    "obstacle_density: max 0.62 exceeds limit 0.6 (3.3% overage, window w002)",
    "traversability_score: min 0.38 below limit 0.5 (24% shortfall, window w003)",
    "environment_type: outdoor_urban not in allowed list [indoor_office, indoor_corridor]"
  ]
}
```

**Key Elements:**
1. **Metric name**: Which constraint violated
2. **Observed value**: COD min or max that violated
3. **Limit value**: ODD threshold that was exceeded/undershot
4. **Magnitude**: Percentage overage/shortfall (numeric only)
5. **Window ID**: Which window(s) violated (from per_window_measurements)

**Phase 1.3 Note**: Percentage calculations currently manual in compliance_summary; Phase 1.4 will formalize in distance calculation.

**No Warnings in Phase 1.3**: Boundary zone removed, violations are binary (in/out only).

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
