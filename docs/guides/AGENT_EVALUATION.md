# Agent Evaluation Integration Guide

This guide shows how to integrate ADK's evaluation framework into your workflow.

## Overview

We use **Google ADK's AgentEvaluator** for agent quality assessment. This provides:
- ✅ Built-in evaluation criteria (tool trajectory, rubrics, hallucination detection)
- ✅ Multiple interfaces (pytest, CLI, web UI)
- ✅ Vertex AI integration
- ✅ Standard test data format (EvalSet/EvalCase)

## Quick Start

### 1. Run Evaluation via pytest

```bash
# Run all evaluation tests
pytest tests/test_adk_evaluation.py -v

# Run specific agent evaluation
pytest tests/test_adk_evaluation.py::test_perception_agent_evaluation -v

# Skip slow evaluation tests during development
pytest tests/test_adk_evaluation.py -v -m "not slow"
```

### 2. Run Evaluation via CLI

```bash
# Evaluate perception agent
adk eval \
  --agent-module odd_agents.agents.perception \
  --eval-dataset tests/evaluation/perception_agent.test.json \
  --config tests/evaluation/test_config.json

# Evaluate all agents
adk eval \
  --agent-module odd_agents \
  --eval-dataset tests/evaluation/ \
  --config tests/evaluation/test_config.json
```

### 3. Run Evaluation via Web UI

```bash
# Launch ADK web interface
adk web

# Then:
# 1. Navigate to "Evaluation" section
# 2. Select agent module (odd_agents.agents.perception)
# 3. Upload test file (perception_agent.test.json)
# 4. Select config (test_config.json)
# 5. Click "Run Evaluation"
```

## Integration Patterns

### Pattern 1: pytest Integration

Add evaluation tests to your test suite:

```python
import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator

@pytest.mark.asyncio
@pytest.mark.slow
async def test_perception_agent_quality():
    """Test perception agent meets quality standards."""
    results = await AgentEvaluator.evaluate(
        agent_module="odd_agents.agents.perception",
        eval_dataset_file_path_or_dir="tests/evaluation/perception_agent.test.json",
        config_file_path="tests/evaluation/test_config.json",
    )
    
    # Assert quality thresholds
    for result in results:
        # Check tool trajectory
        assert result.criteria_results["tool_trajectory_avg_score"].score == 1.0, \
            "Tool trajectory doesn't match expected sequence"
        
        # Check rubric quality
        rubric_result = result.criteria_results["rubric_based_final_response_quality_v1"]
        assert rubric_result.score >= 0.7, \
            f"Response quality too low: {rubric_result.score:.2f}"
        
        # Check no hallucinations
        hallucination_result = result.criteria_results.get("hallucinations_v1")
        if hallucination_result:
            assert hallucination_result.score >= 0.8, \
                "Hallucinations detected in output"
```

### Pattern 2: Programmatic Evaluation

Evaluate agents programmatically in scripts:

```python
from google.adk.evaluation.agent_evaluator import AgentEvaluator
import asyncio

async def evaluate_all_agents():
    """Evaluate all agents and print results."""
    results = await AgentEvaluator.evaluate(
        agent_module="odd_agents",
        eval_dataset_file_path_or_dir="tests/evaluation/",
        config_file_path="tests/evaluation/test_config.json",
    )
    
    for result in results:
        print(f"\n{'='*70}")
        print(f"Eval ID: {result.eval_id}")
        print(f"Overall Score: {result.overall_score:.2f}")
        print(f"{'='*70}")
        
        # Tool trajectory results
        if "tool_trajectory_avg_score" in result.criteria_results:
            traj = result.criteria_results["tool_trajectory_avg_score"]
            status = "✅" if traj.score == 1.0 else "❌"
            print(f"{status} Tool Trajectory: {traj.score:.2f}")
        
        # Rubric results
        if "rubric_based_final_response_quality_v1" in result.criteria_results:
            rubric = result.criteria_results["rubric_based_final_response_quality_v1"]
            status = "✅" if rubric.score >= 0.7 else "❌"
            print(f"{status} Response Quality: {rubric.score:.2f}")
            
            # Per-rubric breakdown
            for rubric_id, rubric_score in rubric.rubric_scores.items():
                print(f"  - {rubric_id}: {rubric_score:.2f}")
        
        # Hallucination check
        if "hallucinations_v1" in result.criteria_results:
            hall = result.criteria_results["hallucinations_v1"]
            status = "✅" if hall.score >= 0.8 else "⚠️"
            print(f"{status} Grounding: {hall.score:.2f}")

if __name__ == "__main__":
    asyncio.run(evaluate_all_agents())
```

### Pattern 3: Continuous Integration

Add to GitHub Actions or CI/CD pipeline:

```yaml
# .github/workflows/evaluation.yml
name: Agent Evaluation

on:
  pull_request:
    paths:
      - 'odd_agents/**'
      - 'tests/evaluation/**'

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run agent evaluation
        env:
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
        run: |
          pytest tests/test_adk_evaluation.py -v --tb=short
      
      - name: Upload evaluation results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: evaluation-results
          path: evaluation_results/
```

### Pattern 4: Regression Detection

Compare evaluation results before/after changes:

```python
import json
from pathlib import Path
from google.adk.evaluation.agent_evaluator import AgentEvaluator

async def detect_regressions():
    """Detect quality regressions between baseline and current."""
    # Load baseline results
    baseline_file = Path("evaluation_results/baseline.json")
    baseline = json.loads(baseline_file.read_text())
    
    # Run current evaluation
    current_results = await AgentEvaluator.evaluate(
        agent_module="odd_agents",
        eval_dataset_file_path_or_dir="tests/evaluation/",
        config_file_path="tests/evaluation/test_config.json",
    )
    
    # Compare results
    regressions = []
    for current in current_results:
        baseline_result = next(
            (b for b in baseline if b['eval_id'] == current.eval_id),
            None
        )
        
        if baseline_result:
            baseline_score = baseline_result['overall_score']
            current_score = current.overall_score
            
            if current_score < baseline_score - 0.1:  # 10% threshold
                regressions.append({
                    'eval_id': current.eval_id,
                    'baseline_score': baseline_score,
                    'current_score': current_score,
                    'delta': current_score - baseline_score,
                })
    
    if regressions:
        print("⚠️  Quality regressions detected:")
        for reg in regressions:
            print(f"  {reg['eval_id']}: {reg['baseline_score']:.2f} → {reg['current_score']:.2f} ({reg['delta']:+.2f})")
        return False
    
    print("✅ No regressions detected")
    return True
```
```

## Creating Test Files

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
        "parts": [{"text": "{\"windows_analyzed\": 2, \"environment_classification\": \"outdoor\", ...}"}]
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

Key components:
- **eval_set_id**: Identifier for the test set
- **eval_cases**: List of test cases
- **user_content**: Input to the agent
- **final_response**: Expected final output (optional, for response_match_score)
- **tool_uses**: Expected tool call sequence (for tool_trajectory_avg_score)
- **session_input**: Session configuration (app_name, user_id, etc.)

## Configuring Evaluation Criteria

`test_config.json` defines which criteria to use and their thresholds:

```json
{
  "criteria": {
    "tool_trajectory_avg_score": {
      "threshold": 1.0,
      "match_type": "IN_ORDER"
    },
    "response_match_score": {
      "threshold": 0.7
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
            "text_property": "The agent correctly identifies environment type (indoor, outdoor, mixed) based on camera data and multimodal consistency."
          }
        }
      ]
    },
    "hallucinations_v1": {
      "threshold": 0.8
    }
  }
}
```

Available criteria:
- **tool_trajectory_avg_score**: Tool usage verification (EXACT, IN_ORDER, ANY_ORDER)
- **response_match_score**: ROUGE-1 similarity to reference
- **final_response_match_v2**: LLM-judged semantic equivalence
- **rubric_based_final_response_quality_v1**: Custom quality rubrics
- **rubric_based_tool_use_quality_v1**: Custom tool usage rubrics
- **hallucinations_v1**: Grounding/factuality check
- **safety_v1**: Harmful content detection

## Cost Optimization

LLM-as-judge evaluation can be expensive. Optimize with:

### 1. Adjust num_samples Based on Importance

```json
{
  "judge_model_options": {
    "num_samples": 1  // Development: fast iteration (~$0.001/eval)
    // OR
    "num_samples": 3  // CI/Testing: moderate robustness (~$0.003/eval)
    // OR
    "num_samples": 7  // Production: high confidence (~$0.007/eval)
  }
}
```

### 2. Use Fewer Rubrics for Quick Checks

```json
{
  "rubrics": [
    // Just critical rubrics for fast iteration
    {"rubric_id": "json_format_compliance", ...},
    {"rubric_id": "safety_critical", ...}
  ]
}
```

### 3. Skip Expensive Criteria During Development

```json
{
  "criteria": {
    // Always cheap
    "tool_trajectory_avg_score": {...},
    
    // Moderate cost - use in CI
    "response_match_score": {...},
    
    // Expensive - use selectively
    // "rubric_based_final_response_quality_v1": {...},
    // "hallucinations_v1": {...}
  }
}
```

### 4. Use Different Configs for Different Environments

```bash
# Development: fast, cheap
adk eval --config tests/evaluation/test_config_dev.json ...

# CI: moderate coverage
adk eval --config tests/evaluation/test_config_ci.json ...

# Production: comprehensive
adk eval --config tests/evaluation/test_config_prod.json ...
```

## File Structure

```
tests/evaluation/
├── perception_agent.test.json      # Perception test cases
├── motion_agent.test.json          # Motion test cases (TODO)
├── collision_agent.test.json       # Collision test cases (TODO)
├── odd_spec_agent.test.json        # ODD spec test cases (TODO)
├── cod_agent.test.json             # COD classifier test cases (TODO)
├── compliance_agent.test.json      # Compliance test cases (TODO)
├── report_agent.test.json          # Report test cases (TODO)
├── test_config.json                # Evaluation criteria config
├── test_config_dev.json            # Dev config (fast, cheap) (TODO)
├── test_config_ci.json             # CI config (moderate) (TODO)
└── test_config_prod.json           # Prod config (comprehensive) (TODO)

odd_agents/evaluation/
├── __init__.py                     # Exports rubrics
├── rubrics.py                      # All rubrics in ADK format
└── README.md                       # Detailed evaluation docs

tests/
└── test_adk_evaluation.py          # pytest integration
```

## Next Steps

1. ✅ **Core infrastructure**: Rubrics, test file, config, pytest integration
2. **Create test files**: Add .test.json for motion, collision, odd_spec, cod, compliance, report agents
3. **Environment-specific configs**: Create dev/ci/prod config variants
4. **CI/CD integration**: Add evaluation to GitHub Actions
5. **Benchmark dataset**: Expand test cases with more scenarios
6. **Vertex AI integration**: Connect to Vertex Gen AI Evaluation Service

See `odd_agents/evaluation/README.md` for detailed documentation on:
- Test file format (EvalSet/EvalCase schema)
- Config file format (criteria and rubric definitions)
- Available evaluation criteria
- Rubric design guidelines
- Best practices

## References

- [Google ADK Evaluation Guide](https://google.github.io/adk-docs/evaluate/)
- [ADK Evaluation Criteria](https://google.github.io/adk-docs/evaluate/criteria/)
- [Kaggle 5 Days of AI - Agent Evaluation](https://www.kaggle.com/code/kaggle5daysofai/day-4b-agent-evaluation)
- [LLM-as-Judge Best Practices](https://google.github.io/adk-docs/evaluate/criteria/#rubric_based_final_response_quality_v1)
