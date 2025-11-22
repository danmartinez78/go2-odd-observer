# Agent Evaluation Framework

LLM-as-judge evaluation system for assessing agent output quality using best practices from the Kaggle 5 Days of AI course and Google ADK documentation.

## Key Principles

### 1. Avoid Model Similarity Bias

**Problem:** Using the same model as both agent and judge creates agreement bias - the model tends to rate its own outputs favorably.

**Solution:** Use a **different and more capable model** as the judge:
- **Agent models**: `gemini-flash-lite` (fast, cost-effective)
- **Judge model**: `gemini-2.5-pro` (more capable, unbiased evaluation)

### 2. Majority Voting for Robustness

**Problem:** LLM evaluations can be inconsistent due to temperature/sampling.

**Solution:** Sample the judge LLM **multiple times** (default: 5) and use majority voting:
```python
judge = LLMJudge(
    agent_type="perception",
    rubrics=PERCEPTION_RUBRICS,
    num_samples=5,  # Majority voting across 5 samples
)
```

### 3. Custom Rubrics for Each Agent Type

**Problem:** Generic evaluation criteria miss agent-specific quality requirements.

**Solution:** Define **custom rubrics** for each agent type that capture domain-specific requirements:
- Perception: environment classification, lighting assessment, multimodal consistency
- Motion: velocity extraction, platform stability, stationary detection
- Collision: risk calibration, proximity analysis, multimodal fusion
- ODD Spec: conversational interpretation, range inference, boundary consistency
- COD: correct classification, violation identification, confidence calibration
- Compliance: accurate comparison, violation detection, importance weighting
- Report: executive summary quality, actionable recommendations, risk assessment

## Usage

### Basic Evaluation

```python
from odd_agents.evaluation import LLMJudge, PERCEPTION_RUBRICS

# Initialize judge
judge = LLMJudge(
    agent_type="perception",
    rubrics=PERCEPTION_RUBRICS,
    judge_model="gemini-2.5-pro",
    num_samples=5,
)

# Evaluate agent output
result = judge.evaluate(
    agent_output=perception_agent_output,
    reference_output=expected_output,  # Optional golden reference
    context={"input_data": ...},  # Optional context
)

# Check results
print(f"Overall Score: {result.overall_score:.2f}")
print(f"Passed: {result.passed}")

for rubric_score in result.rubric_scores:
    print(f"{rubric_score.rubric_id}: {rubric_score.score:.2f}")
    print(f"  Reasoning: {rubric_score.reasoning}")
```

### Batch Evaluation with Reporting

```python
from odd_agents.evaluation import LLMJudge, EvaluationReporter
from odd_agents.evaluation import PERCEPTION_RUBRICS, MOTION_RUBRICS

reporter = EvaluationReporter()

# Evaluate perception agent
perception_judge = LLMJudge("perception", PERCEPTION_RUBRICS)
result = perception_judge.evaluate(perception_output, expected_perception)
reporter.add_result(result)

# Evaluate motion agent
motion_judge = LLMJudge("motion", MOTION_RUBRICS)
result = motion_judge.evaluate(motion_output, expected_motion)
reporter.add_result(result)

# Generate report
reporter.print_summary()
reporter.save_report(Path("evaluation_report.md"))
reporter.save_summary_json(Path("evaluation_summary.json"))
```

### Integration with Tests

```python
import pytest
from odd_agents.evaluation import LLMJudge, COLLISION_RUBRICS

@pytest.mark.slow  # Mark as slow since it calls LLM
def test_collision_agent_quality():
    """Test collision agent output quality using LLM-as-judge."""
    # Run collision agent
    result = run_collision_agent(perception_data, motion_data)
    
    # Evaluate with LLM judge
    judge = LLMJudge("collision", COLLISION_RUBRICS, num_samples=3)
    eval_result = judge.evaluate(
        agent_output=result,
        context={
            "perception": perception_data,
            "motion": motion_data,
        }
    )
    
    # Assert quality standards
    assert eval_result.overall_score >= 0.7, (
        f"Collision agent quality too low: {eval_result.overall_score:.2f}\n"
        f"Failed rubrics: {[rs.rubric_id for rs in eval_result.rubric_scores if not rs.passed]}"
    )
```

## Rubric Design Guidelines

When creating custom rubrics:

1. **Be Specific**: Vague criteria lead to inconsistent judgments
   - ❌ Bad: "The output is good"
   - ✅ Good: "The agent correctly identifies environment type (indoor, outdoor, mixed) based on camera data"

2. **Be Measurable**: Include concrete success criteria
   - ❌ Bad: "Obstacle detection is accurate"
   - ✅ Good: "Obstacle count is within ±20% of reference, consistent with LiDAR density"

3. **Be Independent**: Each rubric should evaluate a distinct aspect
   - Avoid: Multiple rubrics checking the same thing in different ways
   - Prefer: Each rubric focuses on a unique quality dimension

4. **Set Importance Weights**: Critical rubrics should have higher weights
   ```python
   Rubric(
       rubric_id="safety_critical",
       description="...",
       importance=1.0,  # Critical
   )
   
   Rubric(
       rubric_id="formatting",
       description="...",
       importance=0.5,  # Less important
   )
   ```

## Evaluation Metrics

### Per-Rubric Metrics

- **Score**: 0.0 (all votes failed) to 1.0 (all votes passed)
- **Passed**: True if score ≥ 0.5 (majority vote)
- **Votes**: Individual judge decisions across samples
- **Reasoning**: Explanation from majority decision

### Overall Metrics

- **Overall Score**: Importance-weighted average of rubric scores
- **Passed**: True if overall score ≥ 0.5
- **Pass Rate**: Percentage of evaluations that passed
- **Per-Agent Scores**: Average scores grouped by agent type
- **Per-Rubric Scores**: Average scores grouped by rubric ID

## Best Practices

### 1. Use Reference Outputs When Available

```python
# With reference (more precise evaluation)
result = judge.evaluate(
    agent_output=actual_output,
    reference_output=golden_output,
)

# Without reference (rubric-only evaluation)
result = judge.evaluate(
    agent_output=actual_output,
)
```

### 2. Provide Context for Multimodal Agents

```python
# Collision agent evaluates fusion of perception + motion
result = judge.evaluate(
    agent_output=collision_output,
    context={
        "perception": perception_output,
        "motion": motion_output,
    }
)
```

### 3. Adjust num_samples Based on Importance

```python
# Quick iteration (faster, less robust)
judge = LLMJudge(..., num_samples=3)

# Production evaluation (slower, more robust)
judge = LLMJudge(..., num_samples=7)
```

### 4. Monitor Judge Model Costs

LLM-as-judge calls can be expensive. For cost optimization:
- Use `num_samples=3` during development
- Cache evaluation results when possible
- Use `gemini-flash` as judge for less critical evaluations
- Reserve `gemini-2.5-pro` for production/final evaluations

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
