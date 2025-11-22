"""
Tests for ADK-based agent evaluation.
Uses Google ADK's evaluation framework for comprehensive agent testing.

Toy tests (learning examples) are segregated in toy_examples/ subdirectory.
"""

import pytest
from pathlib import Path
from google.adk.evaluation import AgentEvaluator

# Evaluation files directory
EVAL_DIR = Path(__file__).parent / "evaluation"
TOY_EVAL_DIR = EVAL_DIR / "toy_examples"


# ============================================================================
# PRODUCTION AGENT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_perception_tool_trajectory_only():
    """
    Fast test - only check tool trajectory (no expensive LLM judging).
    Uses simple config with just tool_trajectory_avg_score.
    """
    # Temporarily use tool-only config
    import shutil
    config_full = EVAL_DIR / "test_config.json"
    config_tool = EVAL_DIR / "test_config_tool_only.json"
    config_backup = EVAL_DIR / "test_config_backup.json"

    if config_full.exists():
        shutil.copy(config_full, config_backup)
        shutil.copy(config_tool, config_full)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.perception_agent",
            eval_dataset_file_path_or_dir=str(
                EVAL_DIR / "perception_agent.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_full)
            config_backup.unlink()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_perception_agent_evaluation():
    """
    Full perception agent evaluation with all criteria.

    This evaluates:
    - Tool trajectory: Correct sequence of list_windows → analyze_window calls
    - Response quality: Environment classification, multimodal consistency
    - Grounding: No hallucinations in output

    Note: test_config.json in the same directory is automatically used for criteria.
    """
    await AgentEvaluator.evaluate(
        agent_module="tests.evaluation.perception_agent",
        eval_dataset_file_path_or_dir=str(
            EVAL_DIR / "perception_agent.test.json"),
    )


# ============================================================================
# TOY EXAMPLE TESTS (LEARNING & VALIDATION)
# ============================================================================

@pytest.mark.asyncio
async def test_toy_agent_simple():
    """
    Minimal toy test to learn how ADK evaluation works.
    Simple greeting agent with one tool call.
    """
    import shutil
    config_full = EVAL_DIR / "test_config.json"
    config_toy = TOY_EVAL_DIR / "toy_config.json"
    config_backup = EVAL_DIR / "test_config_backup.json"

    if config_full.exists():
        shutil.copy(config_full, config_backup)
        shutil.copy(config_toy, config_full)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.toy_examples.toy_agent",
            eval_dataset_file_path_or_dir=str(
                TOY_EVAL_DIR / "toy_agent.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_full)
            config_backup.unlink()


@pytest.mark.asyncio
async def test_toy_tool_trajectory():
    """
    Learn: Tool trajectory matching (EXACT match type).
    Fast test (~10s) - no LLM judging.
    """
    import shutil
    config_full = EVAL_DIR / "test_config.json"
    config_tool = TOY_EVAL_DIR / "toy_config_tool_only.json"
    config_backup = EVAL_DIR / "test_config_backup.json"

    if config_full.exists():
        shutil.copy(config_full, config_backup)
        shutil.copy(config_tool, config_full)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.toy_examples.toy_agent",
            eval_dataset_file_path_or_dir=str(TOY_EVAL_DIR / "toy_tests.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_full)
            config_backup.unlink()


@pytest.mark.asyncio
async def test_toy_response_match():
    """
    Learn: Response similarity with ROUGE-1.
    Fast test (~10s) - no LLM judging.
    """
    import shutil
    config_full = EVAL_DIR / "test_config.json"
    config_response = TOY_EVAL_DIR / "toy_config_response_only.json"
    config_backup = EVAL_DIR / "test_config_backup.json"

    if config_full.exists():
        shutil.copy(config_full, config_backup)
        shutil.copy(config_response, config_full)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.toy_examples.toy_agent",
            eval_dataset_file_path_or_dir=str(TOY_EVAL_DIR / "toy_tests.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_full)
            config_backup.unlink()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_toy_rubric_quality():
    """
    Learn: Rubric-based LLM judging.
    Slower test (~30s) - makes LLM calls for judging.
    """
    import shutil
    config_full = EVAL_DIR / "test_config.json"
    config_rubric = TOY_EVAL_DIR / "toy_config_rubric_only.json"
    config_backup = EVAL_DIR / "test_config_backup.json"

    if config_full.exists():
        shutil.copy(config_full, config_backup)
        shutil.copy(config_rubric, config_full)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.toy_examples.toy_agent",
            eval_dataset_file_path_or_dir=str(TOY_EVAL_DIR / "toy_tests.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_full)
            config_backup.unlink()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_toy_comprehensive():
    """
    Learn: All ADK evaluation criteria combined.
    Comprehensive test (~60s+) - all criteria including LLM judging.
    """
    import shutil
    config_full = EVAL_DIR / "test_config.json"
    config_comp = TOY_EVAL_DIR / "toy_config_comprehensive.json"
    config_backup = EVAL_DIR / "test_config_backup.json"

    if config_full.exists():
        shutil.copy(config_full, config_backup)
        shutil.copy(config_comp, config_full)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.toy_examples.toy_agent",
            eval_dataset_file_path_or_dir=str(TOY_EVAL_DIR / "toy_tests.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_full)
            config_backup.unlink()
