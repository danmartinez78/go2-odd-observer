# ADK Evaluation Features Used in Toy Examples

This document maps the toy example tests to the ADK evaluation features from https://google.github.io/adk-docs/evaluate/

## Core ADK Features

### 1. Test File Approach (`*.test.json`)
- Using `.test.json` suffix for test files
- **EvalSet/EvalCase Pydantic schema** format
- Test files contain:
  - `user_content` - The user query
  - `final_response` - Expected agent response
  - `intermediate_data.tool_uses` - Expected tool trajectory

### 2. AgentEvaluator API
- **Method:** `AgentEvaluator.evaluate()`
- **Parameters:**
  - `agent_module` - Python module path to agent
  - `eval_dataset_file_path_or_dir` - Path to test file(s)

### 3. Test Configuration (`test_config.json`)
- Criteria specification with thresholds
- Match type configuration (EXACT, IN_ORDER, ANY_ORDER)
- LLM model selection for judging
- Custom rubric definitions

## Evaluation Criteria Used

ADK provides 7 built-in criteria. We use **5 of 7** in toy examples:

### ✅ Criteria 1: `tool_trajectory_avg_score`
**Used in:** test_simple_greeting, test_tool_trajectory, test_comprehensive

**Purpose:** Validate correct tool usage and sequencing

**Match Types Demonstrated:**
- `EXACT` - Tools must match exactly in order, no extras allowed
- `IN_ORDER` - Required tools in order, extra tools OK
- `ANY_ORDER` - All required tools present, any order (not demonstrated)

**Configuration:**
```json
{
  "tool_trajectory_avg_score": {
    "threshold": 1.0,
    "match_type": "EXACT"  // or "IN_ORDER"
  }
}
```

**Key Discovery:** All tools must have `"args": {}` field even if parameterless

**When to use:**
- CI/CD pipelines (fast, deterministic)
- Regression testing
- Validating tool selection logic

---

### ✅ Criteria 2: `response_match_score`
**Used in:** test_simple_greeting, test_response_similarity, test_comprehensive

**Purpose:** Semantic similarity between actual and expected responses

**Similarity Metric:** ROUGE-1 (word overlap scoring)

**Configuration:**
```json
{
  "response_match_score": {
    "threshold": 0.7,
    "similarity_metric": "rouge_1"
  }
}
```

**Threshold Guidelines:**
- `0.5` - Moderate similarity (flexible matching)
- `0.7` - High similarity (recommended)
- `0.8+` - Very strict (near-exact match)

**When to use:**
- CI/CD pipelines (fast, no LLM calls)
- Flexible response validation
- When exact text match too strict

---

### ✅ Criteria 3: `rubric_based_final_response_quality_v1`
**Used in:** test_rubric_quality, test_comprehensive

**Purpose:** LLM-as-judge evaluation of response quality

**Configuration:**
```json
{
  "rubric_based_final_response_quality_v1": {
    "threshold": 0.7,
    "model": "gemini-2.0-flash-thinking-exp",
    "num_samples": 3,
    "rubrics": [
      {
        "rubric_id": "accuracy",
        "rubric_content": {
          "text_property": "The response provides accurate information based on the tool results."
        }
      },
      {
        "rubric_id": "completeness",
        "rubric_content": {
          "text_property": "The response fully answers the user's question."
        }
      }
    ]
  }
}
```

**Parameters:**
- `threshold` - Minimum score (0.0-1.0)
- `model` - LLM model for judging
- `num_samples` - Number of judgments to average (reduces variance)
- `rubrics` - Custom quality criteria

**Cost:** `num_samples × num_rubrics × num_test_cases` LLM API calls

**When to use:**
- Evaluating quality without reference response
- Custom quality dimensions (tone, style, helpfulness)
- Development/validation (not CI/CD due to cost)

---

### ✅ Criteria 4: `hallucinations_v1`
**Used in:** test_comprehensive

**Purpose:** Detect unsupported or contradictory claims

**Configuration:**
```json
{
  "hallucinations_v1": {
    "threshold": 0.8
  }
}
```

**What it checks:**
- Claims grounded in tool outputs
- No contradictions with available context
- No invented facts

**When to use:**
- Agents that cite sources
- Factual accuracy requirements
- Grounding validation

---

### ✅ Criteria 5: `safety_v1`
**Used in:** test_comprehensive

**Purpose:** Ensure responses don't violate safety policies

**Configuration:**
```json
{
  "safety_v1": {
    "threshold": 0.9
  }
}
```

**What it checks:**
- Harmful content
- Hateful language
- Unsafe recommendations

**When to use:**
- Production deployments
- User-facing agents
- Compliance requirements

---

## Criteria NOT Used (Available in ADK)

### ❌ `final_response_match_v2`
- LLM-judged semantic equivalence to reference
- More expensive than ROUGE-1
- Use when semantic meaning matters more than word overlap

### ❌ `rubric_based_tool_use_quality_v1`
- LLM-judged tool usage quality
- Custom rubrics for tool selection reasoning
- Use when tool trajectory matching too rigid

## Test Coverage Matrix

| Test | tool_trajectory | response_match | rubric_quality | hallucinations | safety |
|------|----------------|----------------|----------------|----------------|--------|
| test_simple_greeting | ✅ IN_ORDER | ✅ ROUGE-1 | ❌ | ❌ | ❌ |
| test_tool_trajectory | ✅ EXACT | ❌ | ❌ | ❌ | ❌ |
| test_response_similarity | ❌ | ✅ ROUGE-1 | ❌ | ❌ | ❌ |
| test_rubric_quality | ❌ | ❌ | ✅ LLM judge | ❌ | ❌ |
| test_comprehensive | ✅ IN_ORDER | ✅ ROUGE-1 | ✅ LLM judge | ✅ | ✅ |

## ADK Recommendations Applied

From https://google.github.io/adk-docs/evaluate/criteria/

✅ **For CI/CD & Regression Testing:**
- Using `tool_trajectory_avg_score` (fast, deterministic)
- Using `response_match_score` (fast, no LLM calls)

✅ **For Quality Evaluation:**
- Using `rubric_based_final_response_quality_v1` (custom dimensions)
- Using `hallucinations_v1` (grounding validation)
- Using `safety_v1` (policy compliance)

## Key Learnings

1. **`args: {}` requirement** - All tools MUST have args field (even parameterless)
2. **Match type semantics:**
   - EXACT = no extras, strict order
   - IN_ORDER = required tools in order, extras OK
   - ANY_ORDER = all required tools, any order
3. **ROUGE-1 threshold tuning:**
   - Start at 0.5-0.7
   - Tune based on false positives/negatives
4. **LLM judging costs:**
   - Use `num_samples=1` for dev
   - Use `num_samples=3-5` for production
   - Each rubric = additional LLM call
5. **Config file isolation:**
   - One config per test isolates criteria
   - Makes learning patterns easier
   - Production uses combined configs

## Next Steps for Production Agents

1. **Start with fast criteria** (tool_trajectory + response_match)
2. **Add rubrics incrementally** as quality dimensions identified
3. **Use comprehensive config** for final validation
4. **Separate CI/CD config** (fast only) from validation config (all criteria)
