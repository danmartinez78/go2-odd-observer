# Agent Evaluation Guide (ADK)

Comprehensive rubric-based evaluations for all agents using Google ADK.

## What we evaluate
- Loop agents: Perception, Motion, Collision – tool-use + output quality (+ hallucinations in comprehensive).
- Aggregators: Evaluator (COD construction), Report (narrative synthesis).
- Single-call: ODD Spec (NL → JSON).

## How to run
```bash
# Full suite (slow, live LLMs)
pytest tests/test_adk_evaluation.py -q

# Fast agent checks
pytest tests/test_adk_evaluation.py::test_perception_rubric_quality -q
pytest tests/test_adk_evaluation.py::test_motion_rubric_quality -q
pytest tests/test_adk_evaluation.py::test_collision_rubric_quality -q
pytest tests/test_adk_evaluation.py::test_evaluator_rubric_quality -q
pytest tests/test_adk_evaluation.py::test_report_rubric_quality -q
pytest tests/test_adk_evaluation.py::test_odd_spec_rubric_quality -q
```

## Criteria (what is checked)
- `rubric_based_tool_use_quality_v1`: LLM judge confirms required tools and window coverage.
- `rubric_based_final_response_quality_v1`: JSON shape, completeness, insight quality.
- `hallucinations_v1`: Enabled for perception/motion/collision/evaluator. Report omitted (ADK cannot ground function_call-only outputs).
- Tool trajectory metrics removed (too brittle). Rubric-based tool-use captures sequencing intent without arg matching.

## Configs and fixtures
- Configs live in `tests/evaluation/<agent>/test_config*.json`.
- Perception/Motion/Collision use scenario `data/test/sim/sim_test_w010_w011`.
- Evaluator/Report use fixtures `tests/evaluation/fixtures/eval_report` (ODD + sensor outputs + evaluator state).
- Results log: `tests/evaluation/RESULTS.md`.

## Thresholds
- Final response quality: 0.7
- Tool-use quality: 0.7
- Hallucinations: 1.0 where enabled; evaluator 0.5 (fixtures echo content); report disabled until ADK grounds function_call outputs.

## CI guidance
- Slow tests are marked `@pytest.mark.slow`. Run rubric-only tests in PRs, comprehensive before release/nightly.

## Future tightening
- When ADK supports grounding for function_call outputs, re-enable report hallucinations and raise evaluator hallucination threshold to 1.0.
