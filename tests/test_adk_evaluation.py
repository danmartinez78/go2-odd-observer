"""
Agent evaluation tests using ADK's AgentEvaluator.

This uses ADK's built-in evaluation framework following toy example patterns.
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
async def test_perception_response_similarity():
    """
    Test perception agent response similarity (ROUGE-1 only).
    
    Validates that agent responses semantically match expected output
    without requiring exact text match.
    
    Runtime: ~20s
    """
    import shutil
    config_main = EVAL_DIR / "test_config.json"
    config_response = EVAL_DIR / "test_config_response_only.json"
    config_backup = EVAL_DIR / "test_config_backup.json"

    # Create response-only config if it doesn't exist
    if not config_response.exists():
        config_response.write_text('''{
    "criteria": {
        "response_match_score": {
            "threshold": 0.6,
            "similarity_metric": "rouge_1"
        }
    }
}''')

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_response, config_main)

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
    
    Evaluates:
    - Environment classification accuracy
    - Multimodal consistency
    - JSON format compliance
    
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
    Full perception agent evaluation with all criteria.
    
    Tests:
    - Tool trajectory (IN_ORDER match)
    - Response similarity (ROUGE-1)
    - Rubric-based quality (LLM judging)
    - Hallucinations (grounding validation)
    - Safety (policy compliance)
    
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
