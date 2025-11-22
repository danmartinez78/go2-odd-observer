# COD Classifier Agent Evaluation

## Overview

This directory contains ADK evaluation tests for the **COD Classifier Agent** - a **non-loop agent** that synthesizes perception, motion, and collision analyses into a categorical ODD (Current Operating Domain) classification.

**Key Characteristic**: This agent makes a **single LLM inference** without tools or multi-turn interactions.

## Agent Architecture

**Pattern**: Context Synthesis → JSON Classification

```python
# Agent has NO tools (unlike loop agents)
create_cod_classifier_agent(api_key, model)
# Single inference: Synthesizes {temp:perception/motion/collision} → COD classification JSON
```

**Differs from Loop Agents** (perception/motion/collision):
- ❌ No `list_windows` tool
- ❌ No `analyze_*` tool
- ❌ No multi-turn tool trajectory
- ✅ Single inference call
- ✅ Rubric-based evaluation only
- ✅ Synthesizes from multiple context sources

## Agent Purpose

The COD Classifier synthesizes three types of analyses into a categorical classification:

**Input**: Mock context data from:
- `{temp:perception_output}` - Environment classification, lighting, terrain, obstacles
- `{temp:motion_output}` - Motion statistics (acceleration)
- `{temp:collision_output}` - Collision risk scores

**Output**: Structured JSON with:
- **Categorical axes**: environment_type, lighting_conditions, terrain_type
- **Numeric axes**: obstacle_density, traversability_score, collision_risk
- **Summary**: Brief description of current operating conditions

**Synthesis Logic**:
- environment_type: From perception.environment_classification.primary_class
- lighting_conditions: Majority vote from perception.per_window_perception[*].lighting_class
- terrain_type: Majority vote from perception.per_window_perception[*].terrain_roughness_class
- obstacle_density: Average of perception.per_window_perception[*].obstacle_density
- traversability_score: Average of perception.per_window_perception[*].traversability_score
- collision_risk: Average of collision.collision_events[*].collision_likelihood_score

## Test Data

**Input**: Mock context data embedded in test cases

### Test Cases

1. **Indoor Office Scenario** (low complexity)
   - Environment: Indoor office
   - Lighting: Bright
   - Terrain: Smooth
   - Low obstacle density and collision risk
   - Expected: Clean classification with low risk values

2. **Outdoor Rough Terrain** (high complexity)
   - Environment: Outdoor natural
   - Lighting: Dim/variable
   - Terrain: Rough/very rough
   - High obstacle density and collision risk
   - Expected: Classification reflecting challenging conditions

3. **Indoor Warehouse Moderate** (medium complexity)
   - Environment: Indoor warehouse
   - Lighting: Medium/bright
   - Terrain: Smooth/slightly rough
   - Moderate obstacle density and collision risk
   - Expected: Balanced classification

**Not Used**: Windows 006/007 from sim_run_test (those are for loop agents only)

## Test Configurations

### 1. Rubric-Based Quality (`test_config_rubric_only.json`)
**Runtime**: ~100-120s (3 test cases)

Evaluates COD classification quality:
- `json_structure`: Valid JSON with required fields (categorical, numeric, summary)
- `category_identification`: Correct extraction of environment_type, lighting, terrain
- `numeric_synthesis`: Proper averaging of obstacle density, traversability, collision risk
- `context_synthesis`: Uses all 3 input analyses (perception, motion, collision)
- `output_completeness`: Complete output with descriptive summary

**Note**: No tool_trajectory criterion (this agent has no tools)

### 2. Comprehensive (`test_config_comprehensive.json`)
**Runtime**: ~120-180s

Same rubrics as rubric-only, plus:
- Hallucination detection (threshold: 1.0 - no fabricated data allowed)

## Rubrics

### json_structure
- **Purpose**: Validates JSON format and schema compliance
- **Pass criteria**: 
  - Valid JSON
  - Has `cod_classification` with `categorical` and `numeric` sub-objects
  - Has `cod_summary` string
  - All required categorical fields (environment_type, lighting_conditions, terrain_type)
  - All required numeric fields (obstacle_density, traversability_score, collision_risk)
- **Threshold**: 7/10

### category_identification
- **Purpose**: Evaluates correct extraction of categorical values
- **Pass criteria**:
  - environment_type matches input perception.environment_classification.primary_class
  - lighting_conditions reflects majority vote from lighting_class values
  - terrain_type reflects majority vote from terrain_roughness_class values
- **Threshold**: 7/10

### numeric_synthesis
- **Purpose**: Validates proper aggregation/averaging of numeric values
- **Pass criteria**:
  - obstacle_density = average of per_window obstacle_density values (within 0.05)
  - traversability_score = average of per_window traversability_score values (within 0.05)
  - collision_risk = average of collision_likelihood_score values (within 0.05)
- **Threshold**: 7/10

### context_synthesis
- **Purpose**: Ensures all three input analyses are utilized
- **Pass criteria**:
  - Categorical values derived from perception data
  - Numeric aggregations use perception and collision data
  - Motion data is considered (may influence interpretation)
- **Threshold**: 7/10

### output_completeness
- **Purpose**: Checks output completeness and quality
- **Pass criteria**:
  - cod_summary is present and coherent
  - Summary mentions key aspects (environment, lighting, terrain, risk)
  - No missing or null values
- **Threshold**: 7/10

## Running Tests

```bash
# Rubric-based quality only (~100-120s)
pytest tests/test_adk_evaluation.py::test_cod_classifier_rubric_quality -v

# Comprehensive evaluation (~120-180s)
pytest tests/test_adk_evaluation.py::test_cod_classifier_comprehensive -v
```

## Expected Results

### Indoor Office Scenario
```json
{
  "cod_classification": {
    "categorical": {
      "environment_type": "indoor_office",
      "lighting_conditions": "bright",
      "terrain_type": "smooth"
    },
    "numeric": {
      "obstacle_density": 0.135,
      "traversability_score": 0.935,
      "collision_risk": 0.04
    }
  },
  "cod_summary": "Indoor office environment with bright lighting, smooth terrain, low obstacle density, and minimal collision risk."
}
```

### Outdoor Rough Terrain
```json
{
  "cod_classification": {
    "categorical": {
      "environment_type": "outdoor_natural",
      "lighting_conditions": "dim",
      "terrain_type": "rough"
    },
    "numeric": {
      "obstacle_density": 0.483,
      "traversability_score": 0.583,
      "collision_risk": 0.317
    }
  },
  "cod_summary": "Outdoor natural environment with dim lighting, rough terrain, high obstacle density, and elevated collision risk."
}
```

## Non-Loop Agent Pattern

This is a **reference implementation** for non-loop agent evaluation with context synthesis. Key differences from ODD Spec (the other non-loop agent):

| Aspect | ODD Spec Agent | COD Classifier Agent |
|--------|----------------|----------------------|
| **Input** | Natural language text | Mock context from multiple sources |
| **Synthesis** | NL → JSON | Multi-source context → JSON |
| **Test Data** | Varied NL descriptions | Mock perception/motion/collision data |
| **Complexity** | Single text analysis | Multi-source aggregation & voting |

**Other non-loop agents** (to be evaluated):
- Compliance: Compares {temp:odd_spec} vs {temp:cod}
- Report: Aggregates all {temp:*} outputs

## Adding New Test Cases

To add more scenarios:

1. Edit `cod_classifier_agent.test.json`
2. Add new eval_case with mock context data:
   ```json
   {
     "eval_case_id": "your_scenario_name",
     "conversation": [
       {
         "invocation_id": "0",
         "user_content": "Classify the current operating domain based on the following analyses:\n\nPerception Analysis:\n{...}\n\nMotion Analysis:\n{...}\n\nCollision Analysis:\n{...}",
         "final_response": "{expected JSON output}",
         "intermediate_data": {
           "tool_uses": []
         }
       }
     ]
   }
   ```

3. Run tests to validate

## Test Pattern Summary

**Pattern**: Non-Loop Agent (Context Synthesis)
- **Tools**: None
- **Test Configs**: 2 (rubric_only, comprehensive)
- **Test Functions**: 2 (`test_cod_classifier_rubric_quality`, `test_cod_classifier_comprehensive`)
- **Runtime**: ~100-120s (rubric), ~120-180s (comprehensive)
- **Data**: Mock context from 3 sources
- **Evaluation**: Response quality + hallucinations only (no tool trajectory)

---

**Last Updated**: November 22, 2025  
**Pattern**: Non-Loop Agent with Multi-Source Context Synthesis
