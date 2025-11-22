"""
Tests for ADK-based agent evaluation.
Uses Google ADK's evaluation framework for comprehensive agent testing.

Production agent tests only - toy examples are in toy_examples/test_toy_evaluation.py
"""

import pytest
from pathlib import Path
from google.adk.evaluation import AgentEvaluator

# Evaluation files directory
EVAL_DIR = Path(__file__).parent / "evaluation"


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
