# Report Agent Evaluation

## Overview

This directory contains ADK evaluation tests for the **ReportAgent** - a **non-loop agent** that aggregates all previous agent outputs into a comprehensive final report.

**Key Characteristic**: This agent makes a **single LLM inference** without tools or multi-turn interactions.

## Agent Architecture

**Pattern**: Mock Context Data In → JSON Report Out

```python
# Agent has NO tools (unlike loop agents)
create_report_agent(api_key, model)
# Single inference: Aggregate all {temp:*} outputs → JSON report
```

**Differs from Loop Agents** (perception/motion/collision):
- ❌ No `list_windows` tool
- ❌ No `analyze_*` tool
- ❌ No multi-turn tool trajectory
- ✅ Single inference call
- ✅ Rubric-based evaluation only
- ✅ Aggregates data from context variables

## Input Data

The Report Agent expects mock context data for all previous agent outputs:

### Mock Context Variables
- `{temp:perception_output}` - Perception analysis results
- `{temp:motion_output}` - Motion analysis results
- `{temp:collision_output}` - Collision risk assessment
- `{temp:odd_spec}` - ODD specification
- `{temp:cod_classification}` - Current Operating Domain classification
- `{temp:odd_compliance}` - ODD compliance assessment

### Test Cases

1. **Simple Scenario** (case_simple_scenario)
   - 1 window analyzed
   - Indoor hallway, stationary robot
   - Low collision risk, full ODD compliance
   - Expected: Clean report with all sections populated

2. **Complex Scenario** (case_complex_scenario)
   - 3 windows analyzed
   - Mixed outdoor terrain with obstacles
   - Variable collision risk (low/medium/high)
   - ODD violations detected (prohibited slope)
   - Expected: Detailed report highlighting violations and risks

3. **Edge Case - Minimal Data** (case_edge_minimal_data)
   - No windows analyzed
   - Minimal/missing data in all inputs
   - Expected: Report acknowledges data gaps and provides recommendations

**Not Used**: Windows 006/007 from sim_run_test (those are for loop agents only)

## Output Structure

The Report Agent produces JSON with this structure:

```json
{
  "report": {
    "executive_summary": "2-3 sentence overview",
    "scenario_metadata": {
      "total_windows_analyzed": <int>,
      "scenario_name": "<name>",
      "data_source": "simulation|real_world",
      "data_source_confidence": 0.0-1.0
    },
    "perception_summary": "Brief summary",
    "motion_summary": "Brief summary",
    "collision_summary": "Brief summary",
    "odd_spec_summary": "Brief summary",
    "cod_classification_summary": "Brief summary",
    "odd_compliance_summary": "Brief summary",
    "key_findings": ["finding1", "finding2", "finding3"],
    "recommendations": ["rec1", "rec2"]
  },
  "full_analysis": {
    // Aggregated data from all inputs (optional)
  }
}
```

## Test Configurations

### 1. Rubric-Based Quality (`test_config_rubric_only.json`)
**Runtime**: ~100-120s (3 test cases × 5 rubrics)

Evaluates report generation quality:
- `json_structure`: Valid JSON with all required fields
- `executive_summary_quality`: Clear 2-3 sentence overview covering key aspects
- `data_aggregation_accuracy`: Correctly extracts and aggregates input data
- `report_completeness`: All 6 summary sections present and meaningful
- `actionability_and_clarity`: Specific findings and actionable recommendations

**Note**: No tool_trajectory criterion (this agent has no tools)

### 2. Comprehensive (`test_config_comprehensive.json`)
**Runtime**: ~120-180s (estimated)

Same rubrics as rubric-only, plus:
- Hallucination detection (ensures report doesn't fabricate data)

## Rubrics Design

### 1. JSON Structure (json_structure)
**Purpose**: Validate output format and required fields
**Pass criteria**: 
- Valid JSON
- 'report' object with all required string/array/object fields
- 'full_analysis' object present (can be empty)
**Threshold**: 10/10 for complete structure, 5/10 for partial, 0/10 for invalid

### 2. Executive Summary Quality (executive_summary_quality)
**Purpose**: Assess summary effectiveness
**Pass criteria**:
- 2-3 sentences long
- High-level overview
- Mentions environment type, compliance status, risk level
- Clear and actionable
**Threshold**: 10/10 for excellent, 7/10 for good, 5/10 for basic

### 3. Data Aggregation Accuracy (data_aggregation_accuracy)
**Purpose**: Verify correct data extraction and aggregation
**Pass criteria**:
- total_windows_analyzed matches input data
- data_source/confidence extracted from perception
- Summaries reflect key details from each input
- ODD violations properly reflected
**Threshold**: 10/10 for perfect, 7/10 for mostly accurate, 5/10 for some errors

### 4. Report Completeness (report_completeness)
**Purpose**: Ensure all required sections are present and informative
**Pass criteria**: All 6 summary sections (perception, motion, collision, odd_spec, cod, compliance) are:
- Present
- Non-empty
- Provide meaningful information
**Threshold**: 10/10 for all present and informative, 8/10 for all present, 5/10 for some missing

### 5. Actionability and Clarity (actionability_and_clarity)
**Purpose**: Assess report usefulness for decision-making
**Pass criteria**:
- 2-5 specific, concrete key findings
- 1-3 actionable recommendations
- Clear technical language
- Critical issues (violations, risks) highlighted
**Threshold**: 10/10 for highly actionable, 7/10 for good, 5/10 for vague

## Running Tests

```bash
# Rubric-based quality (~100-120s)
pytest tests/test_adk_evaluation.py::test_report_rubric_quality -v

# Comprehensive evaluation (~120-180s)
pytest tests/test_adk_evaluation.py::test_report_comprehensive -v
```

## Expected Results

### Simple Scenario
Good report should:
- Identify scenario as indoor hallway, simulation data
- Note robot is stationary with clear path
- Confirm low collision risk and full ODD compliance
- Provide simple recommendations like "Safe to proceed"

### Complex Scenario
Good report should:
- Identify mixed outdoor terrain with real-world data
- Note variable collision risk across windows
- **Highlight ODD violation** (prohibited slope operation)
- Flag high collision risk in specific window (002)
- Recommend avoiding slopes and implementing detection

### Minimal Data Scenario
Good report should:
- Acknowledge lack of data (0 windows analyzed)
- Note inability to assess ODD compliance
- Provide recommendations to collect data and run full analysis
- Not fabricate information where data is missing

## Non-Loop Agent Pattern

This is a reference implementation for **non-loop agent evaluation** alongside odd_spec. Key differences from loop agents:

| Aspect | Loop Agents | Non-Loop Agents (Report) |
|--------|-------------|--------------------------|
| **Tools** | list_windows, analyze_* | None |
| **Test Configs** | tool_traj + rubric + comprehensive | rubric + comprehensive only |
| **Test Data** | Windows 006/007 | Mock context data |
| **tool_uses** | Populated array | Empty array `[]` |
| **Runtime** | ~20s (tool_traj), ~70s (rubric) | ~100-120s (rubric for 3 cases) |
| **Evaluation** | Tool trajectory + response quality | Response quality only |
| **Input** | File paths, window IDs | Context variables {temp:*} |

**Other non-loop agents** (follow same pattern):
- ODD Spec: NL description → JSON specification
- COD Classifier: Synthesizes from {temp:perception/motion/collision}
- Compliance: Compares {temp:odd_spec} vs {temp:cod}

## Adding New Test Cases

To add more test scenarios:

1. Edit `report_agent.test.json`
2. Add new eval_case with complete mock context data:
   ```json
   {
     "eval_case_id": "case_new_scenario",
     "conversation": [
       {
         "invocation_id": "0",
         "user_content": {
           "parts": [{"text": "Generate report with: Perception Output: {...} Motion Output: {...} ..."}],
           "role": "user"
         },
         "final_response": {
           "parts": [{"text": "{\"report\": {...}}"}],
           "role": "model"
         },
         "intermediate_data": {
           "tool_uses": []  // Always empty for non-loop agents
         }
       }
     ]
   }
   ```

3. Run tests to validate

## Acceptance Criteria

- ✅ All test files created in `tests/evaluation/report/`
- ✅ Agent export (`report_agent.py`) with no tools
- ✅ Test cases (`report_agent.test.json`) with 3 scenarios and complete mock data
- ✅ Two config files: `test_config_rubric_only.json`, `test_config_comprehensive.json`
- ✅ Five rubrics covering structure, summary, aggregation, completeness, actionability
- ✅ README documents non-loop pattern specifics
- ✅ Empty `tool_uses` arrays in all test cases
- ⏳ Tests pass with scores >= 0.7 (to be validated)
