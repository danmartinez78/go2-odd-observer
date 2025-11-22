# ADK Evaluation Toy Examples

This directory contains minimal "toy" examples to learn and validate ADK evaluation patterns before applying them to complex agents.

## Purpose

Use these simple examples to:
1. **Learn ADK schemas** - Understand correct JSON structure for test files
2. **Test criteria types** - Validate each evaluation criterion independently
3. **Debug issues** - Isolate problems with minimal complexity
4. **Document patterns** - Capture working examples as reference

## Files

### Agent
- `toy_agent.py` - Simple agent with 4 tools (greet, weather, age calculation, list cities)

### Test Data
- `toy_agent.test.json` - Original single-test case (basic greeting)
- `toy_tests.test.json` - Comprehensive test suite covering:
  - Single tool call (exact match)
  - No tools (direct response)
  - Multiple tools (in-order trajectory)
  - Multi-turn conversations
  - Response similarity (partial match)
  - Rubric-based quality assessment

### Configurations

#### Individual Criteria (Fast)
- `toy_config_tool_only.json` - Tool trajectory matching only (~10s)
- `toy_config_response_only.json` - Response similarity only (~10s)
- `toy_config_rubric_only.json` - LLM judging only (~30s, uses LLM)

#### Combined Criteria
- `toy_config.json` - Original simple config (tool trajectory)
- `toy_config_comprehensive.json` - All criteria combined (~60s+)
  - Tool trajectory (IN_ORDER)
  - Response matching (ROUGE-1, threshold 0.5)
  - Rubric-based quality (3 rubrics, 3 samples)
  - Hallucinations (threshold 0.8)
  - Safety (threshold 0.9)

## Key Learnings

### 1. Tool Uses Schema
**CRITICAL**: All tools must have `"args"` field, even if empty!

```json
// ✅ CORRECT
{
  "name": "list_cities",
  "args": {}  // Empty dict for parameterless tools
}

// ❌ WRONG - Will cause tool trajectory to score 0.0
{
  "name": "list_cities"  // Missing args field
}
```

### 2. Match Types for Tool Trajectory

- **EXACT**: Tools must match exactly in order and count
- **IN_ORDER**: Expected tools must appear in order (extras allowed)
- **ANY_ORDER**: Expected tools must appear (any order, extras allowed)

```json
{
  "criteria": {
    "tool_trajectory_avg_score": {
      "threshold": 1.0,
      "match_type": "IN_ORDER"  // or "EXACT" or "ANY_ORDER"
    }
  }
}
```

### 3. Response Matching

Uses ROUGE-1 similarity (0.0 to 1.0). Good for checking semantic similarity without exact match.

```json
{
  "criteria": {
    "response_match_score": {
      "threshold": 0.7,  // 70% similarity required
      "similarity_metric": "rouge_1"
    }
  }
}
```

### 4. Rubric-Based Quality

LLM judges response quality against custom rubrics. **Expensive** - uses LLM calls.

```json
{
  "criteria": {
    "rubric_based_final_response_quality_v1": {
      "threshold": 0.7,
      "model": "gemini-2.0-flash-thinking-exp",
      "num_samples": 3,  // Number of LLM judgments to average
      "rubrics": [
        {
          "rubric_id": "accuracy",
          "rubric_content": {
            "text_property": "Response is factually accurate..."
          }
        }
      ]
    }
  }
}
```

### 5. Multi-Turn Conversations

Each turn is a separate object in the `conversation` array:

```json
{
  "conversation": [
    {
      "invocation_id": "turn-1",
      "user_content": {...},
      "final_response": {...},
      "intermediate_data": {...}
    },
    {
      "invocation_id": "turn-2",
      "user_content": {...},
      "final_response": {...},
      "intermediate_data": {...}
    }
  ]
}
```

## Running Tests

### Quick Tool Trajectory Test (~10s)
```bash
# Use toy_config_tool_only.json
pytest tests/test_adk_evaluation.py::test_toy_tool_trajectory -v
```

### Response Similarity Test (~10s)
```bash
# Use toy_config_response_only.json
pytest tests/test_adk_evaluation.py::test_toy_response_match -v
```

### Rubric Quality Test (~30s)
```bash
# Use toy_config_rubric_only.json - makes LLM calls
pytest tests/test_adk_evaluation.py::test_toy_rubric_quality -v
```

### Comprehensive Test (~60s+)
```bash
# Use toy_config_comprehensive.json - all criteria
pytest tests/test_adk_evaluation.py::test_toy_comprehensive -v
```

## Applying to Real Agents

Once patterns are validated with toy examples:

1. **Copy test structure** - Use toy_tests.test.json as template
2. **Adapt tool calls** - Replace toy tools with agent-specific tools
3. **Customize rubrics** - Use rubrics from `odd_agents/evaluation/rubrics.py`
4. **Start simple** - Begin with tool_only config, then add criteria
5. **Iterate** - Test each criterion independently before combining

## Common Issues

### Tool Trajectory Score 0.0
- Check all tools have `"args": {}` (even empty)
- Verify tool names match exactly
- Check match_type in config

### Response Match Score Low
- ROUGE-1 is strict - lower threshold if needed
- Check response is in expected format (text, not JSON)
- Verify final_response includes actual agent output

### Rubric Evaluation Slow
- Reduce `num_samples` (1-3 for dev, 5-7 for prod)
- Use faster model (flash-lite vs flash-thinking)
- Test rubrics individually first

## Next Steps

After mastering toy examples, apply patterns to:
1. `perception_agent.test.json` - Already working!
2. `motion_agent.test.json` - Motion analysis evaluation
3. `collision_agent.test.json` - Collision detection evaluation
4. Additional agents as needed
