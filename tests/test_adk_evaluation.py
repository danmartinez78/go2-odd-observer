"""
Agent evaluation tests using ADK's AgentEvaluator.

This uses ADK's built-in evaluation framework with:
- tool_trajectory_avg_score: Verify correct tool usage
- rubric_based_final_response_quality_v1: Custom quality rubrics
- hallucinations_v1: Grounding check
"""

import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator
from pathlib import Path


# Path to evaluation test files
EVAL_DIR = Path(__file__).parent / "evaluation"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_perception_agent_evaluation():
    """
    Test perception agent using ADK evaluation framework.

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


@pytest.mark.asyncio
async def test_toy_agent_simple():
    """
    Minimal toy test to learn how ADK evaluation works.
    Simple greeting agent with one tool call.
    """
    # Temporarily swap configs
    import shutil
    config_full = EVAL_DIR / "test_config.json"
    config_toy = EVAL_DIR / "toy_config.json"
    config_backup = EVAL_DIR / "test_config_backup.json"

    if config_full.exists():
        shutil.copy(config_full, config_backup)
        shutil.copy(config_toy, config_full)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.toy_agent",
            eval_dataset_file_path_or_dir=str(
                EVAL_DIR / "toy_agent.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_full)
            config_backup.unlink()


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
async def test_all_evaluation_files():
    """
    Run all evaluation test files in the evaluation directory.

    This is a comprehensive test that evaluates all agents
    against their respective test cases.

    Note: test_config.json in the evaluation directory is automatically used.
    """
    # Skip for now - requires wrapper modules for each agent
    pytest.skip("Requires wrapper modules for all agents - TODO")

    print("\n✅ Evaluation complete!")
