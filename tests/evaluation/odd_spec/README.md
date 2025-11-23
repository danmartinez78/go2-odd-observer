# ODD Spec Agent Evaluation

## Overview

This directory contains ADK evaluation tests for the **OddSpecAgent** - a **non-loop agent** that converts natural language (NL) robot descriptions into structured JSON ODD specifications.

**Key Characteristic**: This agent makes a **single LLM inference** without tools or multi-turn interactions.

## Agent Architecture

**Pattern**: NL Text In → JSON Specification Out

```python
# Agent has NO tools (unlike loop agents)
create_odd_spec_agent(api_key, model)
# Single inference: NL description → JSON with categories/characteristics
```

**Differs from Loop Agents** (perception/motion/collision):
- ❌ No `list_windows` tool
- ❌ No `analyze_*` tool
- ❌ No multi-turn tool trajectory
- ✅ Single inference call
- ✅ Rubric-based evaluation only

## Test Data

**Input**: Natural language robot/environment descriptions

### Test Cases

1. **Indoor Office Robot** (detailed NL)
   - Environment: Indoor office
   - Robot: Quadruped with sensors
   - Expected: Complete JSON with all categories

2. **Minimal Robot** (sparse NL)
   - Minimal description
   - Expected: JSON with reasonable defaults/inferences

**Not Used**: Windows 006/007 from sim_run_test (those are for loop agents only)

## Test Configurations

### 1. Rubric-Based Quality (`test_config_rubric_only.json`)
**Runtime**: ~107s (2 test cases)

Evaluates JSON generation quality:
- `json_structure`: Valid JSON, required fields present
- `categorical_extraction`: Correct category identification (environment, surface, obstacles, robot, sensors)
- `numeric_inference`: Reasonable numeric values (speed, dimensions, ranges)

**Note**: No tool_trajectory criterion (this agent has no tools)

### 2. Comprehensive (`test_config_comprehensive.json`)
**Runtime**: ~120-180s (estimated)

Same rubrics as rubric-only, plus:
- Hallucination detection
- Additional response quality checks

## Running Tests

```bash
# Rubric-based quality only (~107s)
pytest tests/test_adk_evaluation.py::test_odd_spec_rubric_quality -v

# Comprehensive evaluation (~120-180s)
pytest tests/test_adk_evaluation.py::test_odd_spec_comprehensive -v
```

## Adding New Test Cases

To add more NL descriptions to test:

1. Edit `odd_spec_agent.test.json`
2. Add new eval_case in EvalSet format:
   ```json
   {
     "eval_case_id": "case_3",
     "conversation": [
       {
         "invocation_id": "0",
         "user_content": "Your NL description here",
         "final_response": "Expected JSON or description",
         "intermediate_data": {
           "tool_uses": []  # Always empty for non-loop agents
         }
       }
     ]
   }
   ```

3. Run tests to validate

## Non-Loop Agent Pattern

This is the **reference implementation** for non-loop agent evaluation. Key differences from loop agents:

| Aspect | Loop Agents | Non-Loop Agents (ODD Spec) |
|--------|-------------|----------------------------|
| **Tools** | list_windows, analyze_* | None |
| **Test Configs** | tool_traj + rubric | Rubric only |
| **Test Data** | Windows 006/007 | Varied text inputs |
| **tool_uses** | Populated array | Empty array `[]` |
| **Runtime** | ~20s (tool_traj), ~70s (rubric) | ~107s (rubric for 2 cases) |
| **Evaluation** | Tool trajectory + response quality | Response quality only |

**Other non-loop agents** (to be evaluated):
- COD Classifier: Synthesizes from {temp:perception/motion/collision}
- Compliance: Compares {temp:odd_spec} vs {temp:cod}
- Report: Aggregates all {temp:*} outputs

These will follow the same pattern but need mock context data.
