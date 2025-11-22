# Toy Examples - ADK Evaluation Learning

This directory contains **toy examples only** - minimal agents for learning and validating ADK evaluation patterns.

## Purpose

🎓 **Learning environment** - Simple examples to understand ADK without complex agent code  
🧪 **Pattern validation** - Test each evaluation criterion independently  
📚 **Reference implementations** - Working examples to copy when creating real agent tests  

## ⚠️ Not for Production

These are **educational examples** only. For production agent evaluation, see parent directory:
- `../perception_agent.test.json` - Real perception agent tests
- `../test_config.json` - Production evaluation config
- `../../test_adk_evaluation.py` - All agent evaluation tests

## Quick Start

```bash
# Run all toy tests (fast)
pytest tests/test_adk_evaluation.py -v -k "toy" -m "not slow"

# Run specific pattern
pytest tests/test_adk_evaluation.py::test_toy_tool_trajectory -v

# Skip toy tests when running real evaluations
pytest tests/test_adk_evaluation.py -v -k "not toy"
```

## Documentation

- **ADK_PATTERNS_LEARNED.md** - Complete validated patterns reference
- **TOY_EXAMPLES_README.md** - Detailed usage guide
- **TOY_EXAMPLE_SUMMARY.md** - Success summary and impact analysis

## Files

- `toy_agent.py` - Simple agent with 4 tools
- `toy_agent.test.json` - Basic single test
- `toy_tests.test.json` - Minimal multi-test
- `toy_tests_full.test.json` - Comprehensive test suite
- `toy_config_*.json` - Configuration files for each evaluation type

All toy tests are marked in `test_adk_evaluation.py` and can be filtered with `-k "toy"`.
