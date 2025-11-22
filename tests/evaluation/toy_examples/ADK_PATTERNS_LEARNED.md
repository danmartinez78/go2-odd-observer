# ADK Evaluation Patterns - Validated Examples

This document captures working patterns learned from toy examples. **All patterns below have been validated and tested**.

## Test Results Summary

| Test | Criteria | Runtime | Status |
|------|----------|---------|--------|
| `test_toy_agent_simple` | Tool trajectory (basic) | ~14s | ✅ PASS |
| `test_toy_tool_trajectory` | Tool trajectory (EXACT) | ~14s | ✅ PASS |
| `test_toy_response_match` | Response similarity (ROUGE-1) | ~14s | ✅ PASS |
| `test_toy_rubric_quality` | LLM judging (2 rubrics, 1 sample) | ~30s | ✅ PASS |
| `test_perception_tool_trajectory_only` | Real agent - tool trajectory | ~26s | ✅ PASS |

## Critical Schema Requirements

### 1. All Tools Must Have `args` Field ⚠️

**MOST COMMON ERROR**: Missing `args` field causes tool trajectory to score 0.0 even when tools match perfectly.

```json
// ✅ CORRECT
{
  "name": "list_cities",
  "args": {}  // Empty dict for parameterless tools
}

// ❌ WRONG - Silently fails with score 0.0
{
  "name": "list_cities"  // Missing args - DO NOT DO THIS
}
```

### 2. EvalSet Schema Structure

**Top-level structure** (eval_set):
```json
{
  "eval_set_id": "unique_identifier",
  "name": "Human Readable Name",
  "description": "What this test suite covers",
  "eval_cases": [...]
}
```

**Individual eval_case** (NO name/description at this level):
```json
{
  "eval_id": "unique_test_id",
  "conversation": [...],
  "session_input": {
    "app_name": "YourAppName",
    "user_id": "test_user"
  }
}
```

**Conversation turn**:
```json
{
  "invocation_id": "unique_turn_id",
  "user_content": {
    "parts": [{"text": "User message here"}],
    "role": "user"
  },
  "final_response": {
    "parts": [{"text": "Agent response here"}],
    "role": "model"
  },
  "intermediate_data": {
    "tool_uses": [
      {"name": "tool_name", "args": {"param": "value"}}
    ],
    "intermediate_responses": []
  }
}
```

## Configuration Patterns

### Pattern 1: Tool Trajectory Only (Fastest ~14s)

**Use case**: Quick validation that agent calls correct tools in correct order.

```json
{
  "criteria": {
    "tool_trajectory_avg_score": {
      "threshold": 1.0,
      "match_type": "EXACT"  // or "IN_ORDER" or "ANY_ORDER"
    }
  }
}
```

**Match types**:
- `EXACT`: Tools must match exactly (same order, same count, no extras)
- `IN_ORDER`: Expected tools must appear in specified order (extras allowed)
- `ANY_ORDER`: Expected tools must all be present (any order, extras allowed)

### Pattern 2: Response Similarity (~14s)

**Use case**: Check semantic similarity without requiring exact text match.

```json
{
  "criteria": {
    "response_match_score": {
      "threshold": 0.7,  // 70% similarity (0.0 to 1.0)
      "similarity_metric": "rouge_1"
    }
  }
}
```

**Thresholds**:
- `0.9-1.0`: Nearly identical responses
- `0.7-0.9`: High similarity, semantically equivalent
- `0.5-0.7`: Moderate similarity, same general content
- `<0.5`: Low similarity, different content

### Pattern 3: Rubric-Based Quality (~30s per sample)

**Use case**: LLM judges response quality against custom criteria.
**Cost**: Makes LLM API calls (num_samples × num_rubrics calls).

```json
{
  "criteria": {
    "rubric_based_final_response_quality_v1": {
      "threshold": 0.7,
      "model": "gemini-2.0-flash-thinking-exp",
      "num_samples": 1,  // Dev: 1, CI: 3, Prod: 5-7
      "rubrics": [
        {
          "rubric_id": "accuracy",
          "rubric_content": {
            "text_property": "Response provides accurate information based on tool results. Calculations are correct."
          }
        },
        {
          "rubric_id": "completeness",
          "rubric_content": {
            "text_property": "Response fully answers the question without omitting details."
          }
        }
      ]
    }
  }
}
```

**Cost optimization**:
- **Development**: `num_samples: 1`, fast model (`gemini-2.0-flash-lite`)
- **CI/PR**: `num_samples: 3`, balanced model (`gemini-2.0-flash-thinking-exp`)
- **Production**: `num_samples: 5-7`, best model

### Pattern 4: Hallucination Detection (~15s)

**Use case**: Check if response contains information not grounded in tool outputs.

```json
{
  "criteria": {
    "hallucinations_v1": {
      "threshold": 0.8  // Higher = stricter (must be well-grounded)
    }
  }
}
```

### Pattern 5: Safety Check (~15s)

**Use case**: Detect harmful, hateful, or dangerous content.

```json
{
  "criteria": {
    "safety_v1": {
      "threshold": 0.9  // Higher = stricter
    }
  }
}
```

### Pattern 6: Comprehensive (All Criteria)

**Use case**: Full evaluation for production validation.
**Runtime**: ~60s+ depending on num_samples.

```json
{
  "criteria": {
    "tool_trajectory_avg_score": {
      "threshold": 1.0,
      "match_type": "IN_ORDER"
    },
    "response_match_score": {
      "threshold": 0.5,
      "similarity_metric": "rouge_1"
    },
    "rubric_based_final_response_quality_v1": {
      "threshold": 0.7,
      "model": "gemini-2.0-flash-thinking-exp",
      "num_samples": 3,
      "rubrics": [...]
    },
    "hallucinations_v1": {
      "threshold": 0.8
    },
    "safety_v1": {
      "threshold": 0.9
    }
  }
}
```

## Multi-Turn Conversations

Multiple conversation turns are represented as an array within one `eval_case`:

```json
{
  "eval_id": "multi_turn_example",
  "conversation": [
    {
      "invocation_id": "turn-1",
      "user_content": {...},
      "final_response": {...},
      "intermediate_data": {
        "tool_uses": [...]
      }
    },
    {
      "invocation_id": "turn-2",
      "user_content": {...},
      "final_response": {...},
      "intermediate_data": {
        "tool_uses": [...]
      }
    }
  ],
  "session_input": {...}
}
```

**Tool trajectory matching** evaluates each turn independently, then averages.

## Running Tests

### Fast Iteration (tool trajectory only)
```bash
pytest tests/test_adk_evaluation.py::test_toy_tool_trajectory -v
# ~14s runtime
```

### Response Similarity
```bash
pytest tests/test_adk_evaluation.py::test_toy_response_match -v
# ~14s runtime
```

### LLM Judging (slower)
```bash
pytest tests/test_adk_evaluation.py::test_toy_rubric_quality -v
# ~30s runtime (makes LLM API calls)
```

### Skip slow tests
```bash
pytest tests/test_adk_evaluation.py -v -m "not slow"
# Skips rubric-based and comprehensive tests
```

## Common Pitfalls

### 1. Tool Trajectory Scores 0.0 Despite Matching
**Cause**: Missing `args: {}` field on parameterless tools.
**Fix**: Always include `"args": {}` even for tools with no parameters.

### 2. "Must contain list of dictionaries" Error
**Cause**: ADK's format detection confused by extra fields in eval_case.
**Fix**: Remove `name` and `description` from individual eval_cases (only at eval_set level).

### 3. Response Match Score Low
**Cause**: ROUGE-1 is strict - small wording changes reduce score.
**Fix**: Lower threshold (0.5-0.7) or verify response format (text, not JSON).

### 4. Rubric Evaluation Too Slow
**Cause**: High `num_samples` or expensive model.
**Fix**: 
- Dev: `num_samples: 1`, use `gemini-2.0-flash-lite`
- CI: `num_samples: 3`, use `gemini-2.0-flash-thinking-exp`
- Prod: `num_samples: 5-7`, best model

### 5. Tool Names Don't Match
**Cause**: Expected tool name doesn't match actual function name.
**Fix**: Use exact function name as it appears in agent's tools list.

## Next Steps: Applying to Real Agents

1. **Start with tool trajectory** - Fastest feedback, catches most issues
2. **Add response matching** - Validate semantic correctness
3. **Develop rubrics** - Use existing rubrics from `odd_agents/evaluation/rubrics.py`
4. **Test incrementally** - Add one criterion at a time
5. **Optimize for CI** - Balance thoroughness with runtime

## Files Reference

- **Toy Agent**: `tests/evaluation/toy_agent.py`
- **Simple Test**: `tests/evaluation/toy_agent.test.json`
- **Comprehensive Tests**: `tests/evaluation/toy_tests_full.test.json`
- **Configs**:
  - Tool only: `toy_config_tool_only.json`
  - Response only: `toy_config_response_only.json`
  - Rubric only: `toy_config_rubric_only.json`
  - Comprehensive: `toy_config_comprehensive.json`
- **Test Functions**: `tests/test_adk_evaluation.py`
- **Detailed Guide**: `tests/evaluation/TOY_EXAMPLES_README.md`
