# ODD Compliance Agent Evaluation

## Overview

This directory contains ADK evaluation tests for the **OddComplianceAgent** - a **non-loop agent** that compares ODD specifications against Categorical Operating Domain (COD) classifications to assess compliance.

**Key Characteristic**: This agent makes a **single LLM inference** without tools or multi-turn interactions.

## Agent Architecture

**Pattern**: Context Data In → Compliance Analysis Out

```python
# Agent has NO tools (unlike loop agents)
create_odd_compliance_agent(api_key, model)
# Single inference: Compare {temp:odd_spec} vs {temp:cod_classification} → JSON compliance report
```

**Differs from Loop Agents** (perception/motion/collision):
- ❌ No `list_windows` tool
- ❌ No `analyze_*` tool
- ❌ No multi-turn tool trajectory
- ✅ Single inference call
- ✅ Rubric-based evaluation only
- ✅ Uses mock context data (temp variables)

## Agent Behavior

The Compliance Agent performs comparative analysis:

**Input Data** (from context):
- `{temp:odd_spec}` - ODD specification with categorical and numeric constraints
- `{temp:cod_classification}` - Current Operating Domain classification

**Analysis Logic**:
For each axis in COD, compare against ODD constraints and classify as:
- `IN_ODD`: Current conditions within allowed parameters
- `ODD_BOUNDARY`: Close to design limits (in boundary zones)
- `OUT_ODD`: Violates design parameters (in prohibited zones)

**Output**: JSON with compliance assessment structure

## Test Data

**Input**: Mock context data with ODD specifications and COD classifications

### Test Cases

1. **Compliant Scenario** (`compliant_scenario`)
   - COD values within ODD constraints
   - All categorical axes in allowed lists
   - All numeric axes within safe ranges
   - Expected: Overall IN_ODD, no violations

2. **Non-Compliant Scenario** (`non_compliant_scenario`)
   - COD values violate multiple ODD constraints
   - Categorical axes in prohibited lists
   - Numeric axes exceed limits
   - Expected: Overall OUT_ODD, multiple violations listed

3. **Boundary Scenario** (`boundary_scenario`)
   - COD values near ODD constraint boundaries
   - Categorical axes compliant
   - Numeric axes in boundary zones
   - Expected: Overall ODD_BOUNDARY, warnings listed

**Not Used**: Windows 006/007 from sim_run_test (those are for loop agents only)

## Test Configurations

### 1. Rubric-Based Quality (`test_config_rubric_only.json`)
**Runtime**: ~100-120s (3 test cases)

Evaluates compliance analysis quality:
- `json_structure`: Valid JSON with required compliance fields
- `categorical_compliance_accuracy`: Correct categorical constraint checking
- `numeric_compliance_accuracy`: Correct numeric boundary checking
- `violations_identification`: Complete and accurate violation listing
- `overall_compliance_reasoning`: Logical overall assessment with clear reasoning

**Note**: No tool_trajectory criterion (this agent has no tools)

### 2. Comprehensive (`test_config_comprehensive.json`)
**Runtime**: ~120-180s

Same rubrics as rubric-only, plus:
- `hallucinations_avg_score`: Ensures no fabricated constraints or violations
- Additional response quality checks

## Rubric Details

### JSON Structure (Pass: 7/10)
Validates proper JSON format with all required fields:
- Root `odd_compliance` object
- `categorical_compliance` and `numeric_compliance` objects
- `overall_compliance`, `violations`, `warnings`, `compliance_summary` fields

### Categorical Compliance Accuracy (Pass: 7/10)
Verifies correct comparison logic:
- COD value in ODD allowed list → IN_ODD
- COD value in ODD prohibited list → OUT_ODD

### Numeric Compliance Accuracy (Pass: 7/10)
Validates boundary checking:
- obstacle_density: value > max → OUT_ODD, in boundary_zone → ODD_BOUNDARY
- traversability_score: value < min → OUT_ODD, in boundary_zone → ODD_BOUNDARY
- collision_risk: value > max → OUT_ODD, in boundary_zone → ODD_BOUNDARY

### Violations Identification (Pass: 7/10)
Ensures violations are:
- Complete (all OUT_ODD conditions listed)
- Specific (which axis, value, constraint violated)
- Accurate (match actual constraint violations)

### Overall Compliance Reasoning (Pass: 7/10)
Validates logical aggregation:
- OUT_ODD if ANY axis is OUT_ODD
- ODD_BOUNDARY if ANY axis is ODD_BOUNDARY (and none OUT_ODD)
- IN_ODD only if ALL axes are IN_ODD

## Running Tests

```bash
# Rubric-based quality only (~100-120s)
pytest tests/test_adk_evaluation.py::test_compliance_rubric_quality -v

# Comprehensive evaluation (~120-180s)
pytest tests/test_adk_evaluation.py::test_compliance_comprehensive -v
```

## Expected Results

### Compliant Scenario
```json
{
  "odd_compliance": {
    "categorical_compliance": {
      "environment_type": "IN_ODD",
      "lighting_conditions": "IN_ODD",
      "terrain_type": "IN_ODD"
    },
    "numeric_compliance": {
      "obstacle_density": "IN_ODD",
      "traversability_score": "IN_ODD",
      "collision_risk": "IN_ODD"
    },
    "overall_compliance": "IN_ODD",
    "violations": [],
    "warnings": [],
    "compliance_summary": "All conditions within ODD parameters"
  }
}
```

### Non-Compliant Scenario
```json
{
  "odd_compliance": {
    "categorical_compliance": {
      "environment_type": "OUT_ODD",
      "lighting_conditions": "OUT_ODD",
      "terrain_type": "OUT_ODD"
    },
    "numeric_compliance": {
      "obstacle_density": "OUT_ODD",
      "traversability_score": "OUT_ODD",
      "collision_risk": "OUT_ODD"
    },
    "overall_compliance": "OUT_ODD",
    "violations": [
      "environment_type: outdoor_structured is in prohibited list",
      "obstacle_density: 0.35 exceeds max_allowed 0.2",
      "..."
    ],
    "warnings": [],
    "compliance_summary": "Multiple ODD violations detected"
  }
}
```

### Boundary Scenario
```json
{
  "odd_compliance": {
    "categorical_compliance": {
      "environment_type": "IN_ODD",
      "lighting_conditions": "IN_ODD",
      "terrain_type": "IN_ODD"
    },
    "numeric_compliance": {
      "obstacle_density": "ODD_BOUNDARY",
      "traversability_score": "ODD_BOUNDARY",
      "collision_risk": "ODD_BOUNDARY"
    },
    "overall_compliance": "ODD_BOUNDARY",
    "violations": [],
    "warnings": [
      "obstacle_density: 0.27 in boundary zone [0.25, 0.3]",
      "..."
    ],
    "compliance_summary": "Operating near ODD limits"
  }
}
```

## Non-Loop Agent Pattern

This follows the **non-loop agent evaluation pattern** (reference: `odd_spec/`). Key differences from loop agents:

| Aspect | Loop Agents | Non-Loop Agents (Compliance) |
|--------|-------------|------------------------------|
| **Tools** | list_windows, analyze_* | None |
| **Test Configs** | tool_traj + rubric | Rubric only (2 configs) |
| **Test Data** | Windows 006/007 | Mock context data |
| **tool_uses** | Populated array | Empty array `[]` |
| **Runtime** | ~20s (tool_traj), ~70s (rubric) | ~100-120s (rubric for 3 cases) |
| **Evaluation** | Tool trajectory + response quality | Response quality only |
| **Input Pattern** | File-based (SCENARIO_PATH) | Context-based (temp variables) |

**Other non-loop agents** (to be evaluated):
- ODD Spec: NL description → structured JSON specification
- COD Classifier: Synthesizes from {temp:perception/motion/collision}
- Report: Aggregates all {temp:*} outputs

## Adding New Test Cases

To add more compliance scenarios to test:

1. Edit `compliance_agent.test.json`
2. Add new eval_case in EvalSet format:
   ```json
   {
     "eval_case_id": "new_scenario",
     "conversation": [
       {
         "invocation_id": "0",
         "user_content": "Assess compliance between ODD and COD",
         "context": {
           "temp:odd_spec": { ... },
           "temp:cod_classification": { ... }
         },
         "final_response": "Expected outcome description",
         "intermediate_data": {
           "tool_uses": []
         }
       }
     ]
   }
   ```

3. Run tests to validate

## Acceptance Criteria

- ✅ All files created in `tests/evaluation/compliance/`
- ✅ 2 tests added to `test_adk_evaluation.py` (rubric, comprehensive)
- ✅ Test configs created (rubric_only, comprehensive)
- ✅ 5 rubrics designed for comprehensive evaluation
- ✅ 3 test cases covering different compliance scenarios
- ✅ README documents non-loop pattern specifics
- ⏳ All tests pass with scores >= 0.7

---

**Last Updated**: November 22, 2025  
**Pattern**: Non-Loop Agent (No Tools)  
**Reference**: `tests/evaluation/odd_spec/`
