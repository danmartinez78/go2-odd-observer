"""
Agent evaluation tests using ADK's AgentEvaluator.

This uses ADK's built-in evaluation framework following toy example patterns.

NOTE: Perception agent returns structured JSON, not natural language.
Response similarity tests (ROUGE-1) are NOT appropriate for JSON output.
Use rubric-based evaluation to validate JSON structure and content.
"""

import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator
from pathlib import Path


# Path to evaluation test files
EVAL_DIR = Path(__file__).parent / "evaluation"


@pytest.mark.asyncio
async def test_perception_tool_trajectory_only():
    """
    Fast perception test - tool trajectory only.
    
    Validates correct tool usage without LLM judging.
    Runtime: ~20s
    """
    import shutil
    config_main = EVAL_DIR / "test_config.json"
    config_tool = EVAL_DIR / "test_config_tool_only.json"
    config_backup = EVAL_DIR / "test_config_backup.json"

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_tool, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.perception_agent",
            eval_dataset_file_path_or_dir=str(EVAL_DIR / "perception_agent.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_perception_rubric_quality():
    """
    Test perception agent with rubric-based LLM judging.
    
    Evaluates JSON output structure and completeness:
    - Valid JSON structure
    - Complete window analysis (all windows processed)
    - Data integrity (tool outputs preserved)
    
    Runtime: ~30s (makes LLM API calls)
    """
    import shutil
    config_main = EVAL_DIR / "test_config.json"
    config_rubric = EVAL_DIR / "test_config_rubric_only.json"
    config_backup = EVAL_DIR / "test_config_backup.json"

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_rubric, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.perception_agent",
            eval_dataset_file_path_or_dir=str(EVAL_DIR / "perception_agent.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_perception_comprehensive():
    """
    Full perception agent evaluation with all applicable criteria.
    
    Tests:
    - Tool trajectory (IN_ORDER match)
    - Rubric-based quality (JSON structure, completeness, integrity)
    - Hallucinations (grounding validation)
    
    NOTE: Response similarity (ROUGE-1) removed - not appropriate for JSON output
    NOTE: Safety removed - requires Vertex AI configuration
    
    Runtime: ~60s+ (includes LLM API calls)
    """
    import shutil
    config_main = EVAL_DIR / "test_config.json"
    config_comprehensive = EVAL_DIR / "test_config_comprehensive.json"
    config_backup = EVAL_DIR / "test_config_backup.json"

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_comprehensive, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.perception_agent",
            eval_dataset_file_path_or_dir=str(EVAL_DIR / "perception_agent.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()
