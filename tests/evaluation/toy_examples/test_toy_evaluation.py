"""
Toy example tests for learning ADK evaluation patterns.

These tests demonstrate different ADK evaluation criteria in isolation.
Run these to learn how ADK evaluation works before applying to production agents.

Usage:
    # Run all toy tests (fast only)
    pytest tests/evaluation/toy_examples/test_toy_evaluation.py -v -m "not slow"
    
    # Run all toy tests including slow ones
    pytest tests/evaluation/toy_examples/test_toy_evaluation.py -v
    
    # Run specific test
    pytest tests/evaluation/toy_examples/test_toy_evaluation.py::test_tool_trajectory -v
"""

import pytest
from pathlib import Path
from google.adk.evaluation import AgentEvaluator

# Toy examples directory
TOY_DIR = Path(__file__).parent


@pytest.mark.asyncio
async def test_simple_greeting():
    """
    Minimal toy test to learn how ADK evaluation works.
    Simple greeting agent with one tool call.

    Validates: Basic ADK evaluation flow
    Runtime: ~14s
    """
    import shutil
    config_main = TOY_DIR.parent / "test_config.json"
    config_toy = TOY_DIR / "toy_config.json"
    config_backup = TOY_DIR.parent / "test_config_backup.json"

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_toy, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.toy_examples.toy_agent",
            eval_dataset_file_path_or_dir=str(TOY_DIR / "toy_agent.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()


@pytest.mark.asyncio
async def test_tool_trajectory():
    """
    Learn: Tool trajectory matching (EXACT match type).

    Demonstrates:
    - Tool sequence validation
    - EXACT match type (order matters, no extras)
    - args: {} requirement for parameterless tools

    Validates: Correct tool usage
    Runtime: ~14s
    """
    import shutil
    config_main = TOY_DIR.parent / "test_config.json"
    config_tool = TOY_DIR / "toy_config_tool_only.json"
    config_backup = TOY_DIR.parent / "test_config_backup.json"

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_tool, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.toy_examples.toy_agent",
            eval_dataset_file_path_or_dir=str(TOY_DIR / "toy_tests.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()


@pytest.mark.asyncio
async def test_response_similarity():
    """
    Learn: Response similarity with ROUGE-1.

    Demonstrates:
    - ROUGE-1 semantic similarity scoring
    - Flexible response matching (not exact text)
    - Threshold tuning (0.5 = moderate similarity)

    Validates: Response quality without exact match
    Runtime: ~14s
    """
    import shutil
    config_main = TOY_DIR.parent / "test_config.json"
    config_response = TOY_DIR / "toy_config_response_only.json"
    config_backup = TOY_DIR.parent / "test_config_backup.json"

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_response, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.toy_examples.toy_agent",
            eval_dataset_file_path_or_dir=str(TOY_DIR / "toy_tests.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_rubric_quality():
    """
    Learn: Rubric-based LLM judging.

    Demonstrates:
    - LLM-as-judge evaluation
    - Custom quality rubrics
    - num_samples for score averaging
    - Cost considerations (makes LLM API calls)

    Validates: Response quality via LLM judgment
    Runtime: ~30s (makes API calls)
    Cost: num_samples × num_rubrics LLM calls
    """
    import shutil
    config_main = TOY_DIR.parent / "test_config.json"
    config_rubric = TOY_DIR / "toy_config_rubric_only.json"
    config_backup = TOY_DIR.parent / "test_config_backup.json"

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_rubric, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.toy_examples.toy_agent",
            eval_dataset_file_path_or_dir=str(TOY_DIR / "toy_tests.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_comprehensive():
    """
    Learn: All ADK evaluation criteria combined.

    Demonstrates:
    - Tool trajectory matching
    - Response similarity (ROUGE-1)
    - Rubric-based quality (LLM judging)
    - Hallucination detection
    - Safety checking

    Validates: Complete evaluation pipeline
    Runtime: ~60s+ (includes LLM judging)
    Cost: Multiple LLM API calls
    """
    import shutil
    config_main = TOY_DIR.parent / "test_config.json"
    config_comp = TOY_DIR / "toy_config_comprehensive.json"
    config_backup = TOY_DIR.parent / "test_config_backup.json"

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_comp, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.toy_examples.toy_agent",
            eval_dataset_file_path_or_dir=str(TOY_DIR / "toy_tests.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()
