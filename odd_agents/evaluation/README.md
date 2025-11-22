# Agent Evaluation Framework

ADK-native evaluation system for assessing agent output quality using Google's Agent Developer Kit (ADK) built-in evaluation framework.

## Overview

This uses **ADK's AgentEvaluator** with built-in evaluation criteria instead of custom evaluation code. Benefits:
- ✅ **Official Google framework**: Maintained by Google, gets updates
- ✅ **Vertex AI integration**: Can use Vertex Gen AI Evaluation Service API
- ✅ **Multiple interfaces**: pytest, CLI (`adk eval`), web UI (`adk web`)
- ✅ **Standard schema**: EvalSet/EvalCase Pydantic models for test data
- ✅ **Built-in criteria**: Tool trajectory, response matching, rubrics, hallucination detection

## Key Principles

### 1. Avoid Model Similarity Bias

**Problem:** Using the same model as both agent and judge creates agreement bias.

**Solution:** ADK's `rubric_based_final_response_quality_v1` uses a **different judge model** by default:
- **Agent models**: `gemini-flash-lite` (fast, cost-effective)
- **Judge model**: `gemini-2.5-pro` (configured in test_config.json)

### 2. Majority Voting for Robustness

**Problem:** LLM evaluations can be inconsistent due to sampling.

**Solution:** Configure `num_samples` in test_config.json:
```json
{
  "criteria": {
    "rubric_based_final_response_quality_v1": {
      "judge_model_options": {
        "num_samples": 5
      }
    }
  }
}
```

### 3. Custom Rubrics for Each Agent Type

**Problem:** Generic evaluation criteria miss agent-specific quality requirements.

**Solution:** Define **custom rubrics** in ADK format for each agent type:
- Perception: environment classification, lighting assessment, multimodal consistency
- Motion: velocity extraction, platform stability, stationary detection
- Collision: risk calibration, proximity analysis, multimodal fusion
- ODD Spec: conversational interpretation, range inference, boundary consistency
- COD: correct classification, violation identification, confidence calibration
- Compliance: accurate comparison, violation detection, importance weighting
- Report: executive summary quality, actionable recommendations, risk assessment

Rubrics are in `odd_agents/evaluation/rubrics.py` in ADK dict schema format.

## Usage

### Method 1: pytest Integration

```python
import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator

@pytest.mark.asyncio
@pytest.mark.slow
async def test_perception_agent_evaluation():
    """Evaluate perception agent using ADK framework."""
    await AgentEvaluator.evaluate(
        agent_module="odd_agents.agents.perception",
        eval_dataset_file_path_or_dir="tests/evaluation/perception_agent.test.json",
        config_file_path="tests/evaluation/test_config.json",
    )
```

### Method 2: CLI (adk eval)

```bash
# Evaluate specific test file
adk eval \
  --agent-module odd_agents.agents.perception \
  --eval-dataset tests/evaluation/perception_agent.test.json \
  --config tests/evaluation/test_config.json

# Evaluate all test files in directory
adk eval \
  --agent-module odd_agents \
  --eval-dataset tests/evaluation/ \
  --config tests/evaluation/test_config.json
```

### Method 3: Web UI (adk web)

```bash
# Launch web UI for interactive evaluation
adk web

# Then navigate to evaluation section and:
# 1. Select agent module (odd_agents.agents.perception)
# 2. Upload test file (perception_agent.test.json)
# 3. Select config file (test_config.json)
# 4. Click "Run Evaluation"
```

### Programmatic Usage

```python
from google.adk.evaluation.agent_evaluator import AgentEvaluator

# Run evaluation programmatically
results = await AgentEvaluator.evaluate(
    agent_module="odd_agents.agents.perception",
    eval_dataset_file_path_or_dir="tests/evaluation/perception_agent.test.json",
    config_file_path="tests/evaluation/test_config.json",
)

# Access results
for result in results:
    print(f"Eval ID: {result.eval_id}")
    print(f"Overall Score: {result.overall_score}")
    
    # Tool trajectory results
    if "tool_trajectory_avg_score" in result.criteria_results:
        traj_result = result.criteria_results["tool_trajectory_avg_score"]
        print(f"Tool Trajectory: {traj_result.score}")
    
    # Rubric results
    if "rubric_based_final_response_quality_v1" in result.criteria_results:
        rubric_result = result.criteria_results["rubric_based_final_response_quality_v1"]
        print(f"Rubric Score: {rubric_result.score}")
        for rubric_id, rubric_score in rubric_result.rubric_scores.items():
            print(f"  {rubric_id}: {rubric_score}")
```

## Test File Format

ADK uses `.test.json` files in **EvalSet/EvalCase** schema:

```json
{
  "eval_set_id": "perception_agent_basic_tests",
  "eval_cases": [{
    "eval_id": "perception_basic_analysis",
    "conversation": [{
      "user_content": {
        "parts": [{"text": "Analyze perception for all available windows"}]
      },
      "final_response": {
        "parts": [{"text": "{\"windows_analyzed\": 2, ...}"}]
      },
      "intermediate_data": {
        "tool_uses": [
          {"name": "list_windows_tool"},
          {"name": "analyze_window_perception_tool", "args": {"window_id": "w000"}},
          {"name": "analyze_window_perception_tool", "args": {"window_id": "w001"}}
        ],
        "intermediate_responses": []
      }
    }],
    "session_input": {
      "app_name": "PerceptionWorkflowApp",
      "user_id": "test_user"
    }
  }]
}
```

## Config File Format

`test_config.json` defines evaluation criteria:

```json
{
  "criteria": {
    "tool_trajectory_avg_score": {
      "threshold": 1.0,
      "match_type": "IN_ORDER"
    },
    "rubric_based_final_response_quality_v1": {
      "threshold": 0.7,
      "judge_model_options": {
        "judge_model": "gemini-2.5-pro",
        "num_samples": 5
      },
      "rubrics": [
        {
          "rubric_id": "environment_classification",
          "rubric_content": {
            "text_property": "The agent correctly identifies environment type..."
          }
        }
      ]
    }
  }
}
```

## Rubric Design Guidelines

When creating custom rubrics (in `odd_agents/evaluation/rubrics.py`):

1. **Be Specific**: Vague criteria lead to inconsistent judgments
   - ❌ Bad: "The output is good"
   - ✅ Good: "The agent correctly identifies environment type (indoor, outdoor, mixed) based on camera data"

2. **Be Measurable**: Include concrete success criteria
   - ❌ Bad: "Obstacle detection is accurate"
   - ✅ Good: "Obstacle count is within ±20% of reference, consistent with LiDAR density"

3. **Be Independent**: Each rubric should evaluate a distinct aspect
   - Avoid: Multiple rubrics checking the same thing in different ways
   - Prefer: Each rubric focuses on a unique quality dimension

4. **Use ADK dict schema**:
   ```python
   {
       "rubric_id": "safety_critical",
       "rubric_content": {
           "text_property": "Critical safety requirement description"
       }
   }
   ```

## Available Evaluation Criteria

ADK provides these built-in criteria:

### 1. tool_trajectory_avg_score
Verifies correct tool usage sequence:
- `EXACT`: Exact match (same tools, same order, same args)
- `IN_ORDER`: Tools appear in correct order (extra tools allowed)
- `ANY_ORDER`: All expected tools used (any order)

### 2. response_match_score
ROUGE-1 similarity between actual and reference response.

### 3. final_response_match_v2
LLM-judged semantic equivalence (uses different model).

### 4. rubric_based_final_response_quality_v1
Custom rubrics for response quality (our primary quality metric).

### 5. rubric_based_tool_use_quality_v1
Custom rubrics for tool usage quality.

### 6. hallucinations_v1
Grounding check - detects hallucinations/factual errors.

### 7. safety_v1
Safety check - detects harmful content.

## Best Practices

### 1. Define Expected Tool Trajectory

```json
{
  "intermediate_data": {
    "tool_uses": [
      {"name": "list_windows_tool"},
      {"name": "analyze_window_perception_tool", "args": {"window_id": "w000"}}
    ]
  }
}
```

Then configure `tool_trajectory_avg_score` with `IN_ORDER` match type.

### 2. Use Reference Responses When Available

```json
{
  "final_response": {
    "parts": [{"text": "Expected JSON output..."}]
  }
}
```

Enables `response_match_score` and `final_response_match_v2` criteria.

### 3. Select Appropriate Rubrics

Choose rubrics from `odd_agents/evaluation/rubrics.py`:
- **Perception**: PERCEPTION_RUBRICS (environment classification, lighting, multimodal consistency)
- **Motion**: MOTION_RUBRICS (velocity extraction, platform stability)
- **Collision**: COLLISION_RUBRICS (risk calibration, proximity analysis)

### 4. Adjust num_samples Based on Importance
File Structure

```
tests/evaluation/
├── perception_agent.test.json    # Perception agent test cases
├── motion_agent.test.json        # Motion agent test cases
├── collision_agent.test.json     # Collision agent test cases
├── odd_spec_agent.test.json      # ODD spec agent test cases
├── cod_agent.test.json           # COD classifier test cases
├── compliance_agent.test.json    # Compliance agent test cases
├── report_agent.test.json        # Report generator test cases
└── test_config.json              # Shared evaluation criteria config

odd_agents/evaluation/
├── __init__.py                   # Module exports
├── rubrics.py                    # All agent rubrics in ADK format
└── README.md                     # This file

tests/
└── test_adk_evaluation.py        # pytest integration
```

## References

- [Kaggle 5 Days of AI - Day 4b: Agent Evaluation](https://www.kaggle.com/code/kaggle5daysofai/day-4b-agent-evaluation)
- [Google ADK Evaluation Criteria](https://google.github.io/adk-docs/evaluate/criteria/)
- [ADK Evaluation Guide](https://google.github.io/adk-docs/evaluate/)
- [LLM-as-Judge Best Practices](https://google.github.io/adk-docs/evaluate/criteria/#rubric_based_final_response_quality_v1)

## Roadmap

- [x] Rubrics for all 7 agent types (40 total rubrics)
- [x] ADK format conversion (dict schema)
- [x] Example test file (perception_agent.test.json)
- [x] Evaluation config (test_config.json)
- [x] pytest integration (test_adk_evaluation.py)
- [ ] Test files for remaining agents (motion, collision, odd_spec, cod, compliance, report)
- [ ] Integration with Vertex AI Eval Service API

LLM-as-judge can be expensive:
- Development: `num_samples=3`, fewer rubrics
- Production: `num_samples=5-7`, full rubric set
- Use `hallucinations_v1` and `safety_v1` selectively

## References

- [Kaggle 5 Days of AI - Day 4b: Agent Evaluation](https://www.kaggle.com/code/kaggle5daysofai/day-4b-agent-evaluation)
- [Google ADK Evaluation Criteria](https://google.github.io/adk-docs/evaluate/criteria/)
- [LLM-as-Judge Best Practices](https://google.github.io/adk-docs/evaluate/criteria/#rubric_based_final_response_quality_v1)

## Roadmap

- [ ] Add tool trajectory evaluation (exact/ordered/any-order matching)
- [ ] Add hallucination detection (grounding check)
- [ ] Add safety evaluation (harmful content)
- [ ] Integration with Vertex AI Eval SDK
- [ ] Automated regression testing (detect quality regressions)
- [ ] Benchmark dataset for systematic evaluation
