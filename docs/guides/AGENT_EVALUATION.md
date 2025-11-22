# Agent Evaluation Integration Guide

This guide shows how to integrate the LLM-as-judge evaluation framework into your workflow.

## Quick Start

### 1. Run the Demo

```bash
python scripts/evaluation_demo.py
```

This evaluates sample outputs from perception, motion, and collision agents using:
- **Judge model**: `gemini-2.5-pro` (different from agent models to avoid bias)
- **Majority voting**: 3 samples per rubric for robustness
- **Custom rubrics**: Agent-specific quality criteria

Output:
- Console summary with scores and pass/fail status
- `data/examples/evaluation_demo_report.md` - Detailed markdown report
- `data/examples/evaluation_demo_summary.json` - JSON metrics

### 2. Run Unit Tests

```bash
# Run all evaluation tests
pytest tests/test_llm_judge.py -v

# Run specific test
pytest tests/test_llm_judge.py::TestLLMJudge::test_perception_evaluation_perfect_output -v

# Skip slow LLM tests during development
pytest tests/test_llm_judge.py -v -m "not slow"
```

## Integration Patterns

### Pattern 1: Standalone Evaluation

Use when you want to evaluate agent outputs independently:

```python
from odd_agents.evaluation import LLMJudge, PERCEPTION_RUBRICS

# Run your agent
perception_output = run_perception_agent(window_data)

# Evaluate output
judge = LLMJudge("perception", PERCEPTION_RUBRICS, num_samples=5)
result = judge.evaluate(
    agent_output=perception_output,
    reference_output=golden_perception_output,  # Optional
)

if not result.passed:
    print(f"Quality issue detected! Score: {result.overall_score:.2f}")
    for rs in result.rubric_scores:
        if not rs.passed:
            print(f"  Failed: {rs.rubric_id} - {rs.reasoning}")
```

### Pattern 2: Test Integration

Use in pytest tests to assert quality standards:

```python
import pytest
from odd_agents.evaluation import LLMJudge, MOTION_RUBRICS

@pytest.mark.slow
def test_motion_agent_quality():
    """Test that motion agent meets quality standards."""
    # Arrange
    window_data = load_test_window()
    
    # Act
    motion_output = run_motion_agent(window_data)
    
    # Assert with LLM judge
    judge = LLMJudge("motion", MOTION_RUBRICS, num_samples=3)
    result = judge.evaluate(
        agent_output=motion_output,
        context={"window_data": window_data},
    )
    
    assert result.overall_score >= 0.7, (
        f"Motion agent quality below threshold: {result.overall_score:.2f}\n"
        f"Failed rubrics:\n" + "\n".join(
            f"  - {rs.rubric_id}: {rs.reasoning}"
            for rs in result.rubric_scores if not rs.passed
        )
    )
```

### Pattern 3: Batch Evaluation with Reporting

Use for evaluating multiple agents across multiple scenarios:

```python
from odd_agents.evaluation import LLMJudge, EvaluationReporter
from odd_agents.evaluation import PERCEPTION_RUBRICS, MOTION_RUBRICS

reporter = EvaluationReporter()

# Evaluate across multiple windows
for window_id in range(10):
    window_data = load_window(window_id)
    
    # Evaluate perception
    perception_output = run_perception_agent(window_data)
    perception_judge = LLMJudge("perception", PERCEPTION_RUBRICS)
    result = perception_judge.evaluate(perception_output)
    reporter.add_result(result)
    
    # Evaluate motion
    motion_output = run_motion_agent(window_data)
    motion_judge = LLMJudge("motion", MOTION_RUBRICS)
    result = motion_judge.evaluate(motion_output)
    reporter.add_result(result)

# Generate comprehensive report
reporter.print_summary()
reporter.save_report(Path("evaluation_report.md"))
```

### Pattern 4: Regression Testing

Use to detect quality regressions when changing code:

```python
from odd_agents.evaluation import compare_evaluations

# Evaluate before changes
results_before = [evaluate_agent(...) for _ in test_cases]

# Make changes to agent
update_agent_code()

# Evaluate after changes
results_after = [evaluate_agent(...) for _ in test_cases]

# Compare
comparison = compare_evaluations(results_before, results_after)

if comparison['overall']['score_improvement'] < 0:
    print(f"⚠️  Quality regression detected!")
    print(f"Score decreased by {-comparison['overall']['score_improvement']:.2f}")
    print("Per-agent regressions:")
    for agent, improvement in comparison['per_agent_improvements'].items():
        if improvement < 0:
            print(f"  - {agent}: {improvement:.2f}")
```

## Cost Optimization

LLM-as-judge calls can be expensive. Optimize costs with:

### 1. Adjust num_samples Based on Importance

```python
# Development: Fast iteration
judge = LLMJudge(..., num_samples=1)  # ~$0.001/evaluation

# CI/Testing: Moderate robustness
judge = LLMJudge(..., num_samples=3)  # ~$0.003/evaluation

# Production: High confidence
judge = LLMJudge(..., num_samples=7)  # ~$0.007/evaluation
```

### 2. Use Smaller Judge Model for Less Critical Evaluations

```python
# For format validation (less critical)
judge = LLMJudge(..., judge_model="gemini-2.5-flash", num_samples=1)

# For accuracy assessment (critical)
judge = LLMJudge(..., judge_model="gemini-2.5-pro", num_samples=5)
```

### 3. Cache Evaluation Results

```python
import hashlib
import json
from pathlib import Path

def get_cached_evaluation(agent_output, cache_dir="eval_cache"):
    """Check for cached evaluation result."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(exist_ok=True)
    
    # Generate cache key from output
    output_str = json.dumps(agent_output, sort_keys=True)
    cache_key = hashlib.sha256(output_str.encode()).hexdigest()
    cache_file = cache_dir / f"{cache_key}.json"
    
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    return None

def save_evaluation_cache(agent_output, result, cache_dir="eval_cache"):
    """Save evaluation result to cache."""
    cache_dir = Path(cache_dir)
    
    output_str = json.dumps(agent_output, sort_keys=True)
    cache_key = hashlib.sha256(output_str.encode()).hexdigest()
    cache_file = cache_dir / f"{cache_key}.json"
    
    cache_file.write_text(json.dumps(result.to_dict(), indent=2))
```

### 4. Prioritize Critical Rubrics

```python
# Only evaluate high-importance rubrics
critical_rubrics = [
    r for r in PERCEPTION_RUBRICS 
    if r.importance >= 0.9
]

judge = LLMJudge("perception", critical_rubrics, num_samples=3)
```

## Next Steps

1. **Integrate into CI/CD**: Add evaluation tests to GitHub Actions
2. **Build Benchmark Dataset**: Create golden outputs for systematic evaluation
3. **Monitor Quality Trends**: Track evaluation scores over time
4. **Expand Rubrics**: Add domain-specific quality criteria as needed

See `odd_agents/evaluation/README.md` for detailed documentation.
