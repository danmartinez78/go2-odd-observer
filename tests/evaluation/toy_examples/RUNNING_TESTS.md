# Running Toy Evaluation Tests

## Problem: pytest-asyncio Event Loop Conflicts

When running multiple toy tests together with pytest, subsequent tests fail with:
```
RuntimeError: Event loop is closed
TypeError: object of type 'NoneType' has no len()
```

This is caused by ADK's internal state not cleaning up properly between test runs in the same pytest session.

## Solutions

### ✅ Option 1: Sequential Script Runner (Recommended)

Run each test in a separate subprocess for complete isolation:

```bash
# Fast tests only (3 tests, ~60s)
python tests/evaluation/toy_examples/run_all_toy_tests.py

# Include slow tests (5 tests, ~120s+, makes LLM API calls)
python tests/evaluation/toy_examples/run_all_toy_tests.py --include-slow

# Custom output file
python tests/evaluation/toy_examples/run_all_toy_tests.py --output my_results.json
```

**Benefits:**
- ✅ Each test runs in fresh subprocess (clean event loop)
- ✅ Captures all results and generates JSON report
- ✅ Clear pass/fail summary with timing
- ✅ No additional dependencies
- ✅ Works with any pytest version

**Output:**
```
🧪 Running 3 toy evaluation tests sequentially
📊 Results will be saved to: toy_test_results.json

============================================================
Running: test_simple_greeting
============================================================
✅ PASSED in 19.96s

...

SUMMARY
Total: 3 tests
✅ Passed: 3
❌ Failed: 0
⏱️  Total time: 58.19s

📄 Full results saved to: toy_test_results.json
```

### Option 2: pytest-xdist Parallel Workers

Install pytest-xdist to run tests in separate worker processes:

```bash
# Install plugin
pip install pytest-xdist

# Run with custom config
pytest -c tests/evaluation/toy_examples/pytest_isolated.ini \
       tests/evaluation/toy_examples/test_toy_evaluation.py -v -m "not slow"

# Or use -n flag directly
pytest tests/evaluation/toy_examples/test_toy_evaluation.py -n auto -v
```

**Benefits:**
- ✅ Parallel execution (faster on multi-core)
- ✅ Automatic worker management
- ✅ Standard pytest interface

**Drawbacks:**
- ❌ Requires additional dependency
- ❌ More complex configuration

### Option 3: Run Individual Tests

Use pytest to run tests one at a time:

```bash
# Run each test individually
pytest tests/evaluation/toy_examples/test_toy_evaluation.py::test_simple_greeting -v
pytest tests/evaluation/toy_examples/test_toy_evaluation.py::test_tool_trajectory -v
pytest tests/evaluation/toy_examples/test_toy_evaluation.py::test_response_similarity -v

# Slow tests (LLM judging)
pytest tests/evaluation/toy_examples/test_toy_evaluation.py::test_rubric_quality -v
pytest tests/evaluation/toy_examples/test_toy_evaluation.py::test_comprehensive -v
```

**Benefits:**
- ✅ Simple, no scripts needed
- ✅ Standard pytest workflow

**Drawbacks:**
- ❌ Manual, no aggregated results
- ❌ Tedious for multiple tests

## Recommended Workflow

**Development (learning ADK patterns):**
```bash
# Run single test to learn specific pattern
pytest tests/evaluation/toy_examples/test_toy_evaluation.py::test_tool_trajectory -v
```

**Validation (verify all patterns work):**
```bash
# Run all fast tests with script
python tests/evaluation/toy_examples/run_all_toy_tests.py

# View results
cat toy_test_results.json | jq '.results[] | {test, passed, duration}'
```

**CI/CD (automated testing):**
```bash
# Fast tests only (no LLM API calls)
python tests/evaluation/toy_examples/run_all_toy_tests.py --output ci_results.json

# Upload results as artifact
# (exit code 1 if any test fails)
```

## Test Categories

### Fast Tests (~20s each, no LLM calls)
- `test_simple_greeting` - Basic evaluation flow
- `test_tool_trajectory` - Tool matching (EXACT)
- `test_response_similarity` - ROUGE-1 matching

### Slow Tests (~30-60s each, makes LLM API calls)
- `test_rubric_quality` - LLM-as-judge evaluation
- `test_comprehensive` - All criteria combined

Mark slow tests with `-m "not slow"` to skip in CI:
```bash
python tests/evaluation/toy_examples/run_all_toy_tests.py  # skips slow by default
```

## Results Format

The sequential runner produces JSON with:
```json
{
  "timestamp": "2025-11-22T...",
  "total_tests": 3,
  "passed": 3,
  "failed": 0,
  "total_duration": 58.19,
  "include_slow": false,
  "results": [
    {
      "test": "test_simple_greeting",
      "passed": true,
      "duration": 19.96,
      "returncode": 0,
      "output_lines": 142
    },
    ...
  ]
}
```

Use this for:
- CI/CD validation
- Performance tracking
- Regression detection
- Test suite health monitoring
