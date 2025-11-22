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


# =============================================================================
# PERCEPTION AGENT EVALUATION TESTS
# =============================================================================


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
            eval_dataset_file_path_or_dir=str(
                EVAL_DIR / "perception_agent.test.json"),
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
            eval_dataset_file_path_or_dir=str(
                EVAL_DIR / "perception_agent.test.json"),
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
            eval_dataset_file_path_or_dir=str(
                EVAL_DIR / "perception_agent.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()


# =============================================================================
# PERCEPTION TOOL (INFERENCE) EVALUATION TESTS
# These test the actual multimodal perception analysis - the REAL AI work
# =============================================================================


@pytest.mark.asyncio
async def test_perception_tool_only():
    """
    Fast perception tool test - validates tool call only.

    Tests the actual perception inference (multimodal vision analysis).
    Runtime: ~10s per window
    """
    import shutil
    config_main = EVAL_DIR / "test_config.json"
    config_tool = EVAL_DIR / "test_config_perception_tool_only.json"
    config_backup = EVAL_DIR / "test_config_backup.json"

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_tool, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.perception_tool",
            eval_dataset_file_path_or_dir=str(
                EVAL_DIR / "perception_tool.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_perception_tool_inference_quality():
    """
    Test perception tool inference quality with LLM judge.

    Evaluates actual AI inference quality:
    - Multimodal analysis (camera + LiDAR BEV fusion)
    - Scene classification accuracy (lighting, terrain)
    - Quantitative metrics validity (visibility, occupancy, traversability)
    - Constraint detection (humans, environmental factors)
    - JSON output structure

    Runtime: ~60s (2 windows × 3 samples × LLM calls)
    """
    import shutil
    config_main = EVAL_DIR / "test_config.json"
    config_rubric = EVAL_DIR / "test_config_perception_tool_rubric.json"
    config_backup = EVAL_DIR / "test_config_backup.json"

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_rubric, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.perception_tool",
            eval_dataset_file_path_or_dir=str(
                EVAL_DIR / "perception_tool.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_perception_tool_comprehensive():
    """
    Full perception tool evaluation - inference quality + hallucinations.

    Tests:
    - Tool trajectory (EXACT match)
    - Rubric-based inference quality (5 rubrics)
    - Hallucinations (ensures grounding in visual data)

    Runtime: ~120s+ (comprehensive evaluation)
    """
    import shutil
    config_main = EVAL_DIR / "test_config.json"
    config_comprehensive = EVAL_DIR / "test_config_perception_tool_comprehensive.json"
    config_backup = EVAL_DIR / "test_config_backup.json"

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_comprehensive, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.perception_tool",
            eval_dataset_file_path_or_dir=str(
                EVAL_DIR / "perception_tool.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()


# =============================================================================
# MOTION AGENT EVALUATION TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_motion_tool_trajectory_only():
    """
    Fast motion test - tool trajectory only.

    Validates correct tool usage (list_windows, analyze_motion for each window).
    Runtime: ~20s
    """
    import shutil
    motion_dir = EVAL_DIR / "motion"
    config_main = motion_dir / "test_config.json"
    config_tool = motion_dir / "test_config_tool_only.json"
    config_backup = motion_dir / "test_config_backup.json"

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_tool, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.motion.motion_agent",
            eval_dataset_file_path_or_dir=str(
                motion_dir / "motion_agent.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_motion_rubric_quality():
    """
    Test motion agent with rubric-based LLM judging.

    Evaluates JSON output quality:
    - Valid JSON structure (windows_analyzed, overall_stats, per_window_motion)
    - Motion analysis completeness (all windows, statistics calculated)
    - Motion metrics validity (physically plausible values)

    Runtime: ~80s (makes LLM API calls)
    """
    import shutil
    motion_dir = EVAL_DIR / "motion"
    config_main = motion_dir / "test_config.json"
    config_rubric = motion_dir / "test_config_rubric_only.json"
    config_backup = motion_dir / "test_config_backup.json"

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_rubric, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.motion.motion_agent",
            eval_dataset_file_path_or_dir=str(
                motion_dir / "motion_agent.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_motion_comprehensive():
    """
    Full motion agent evaluation with all applicable criteria.

    Tests:
    - Tool trajectory (IN_ORDER match)
    - Rubric-based quality (structure, completeness, validity)
    - Hallucinations (grounding validation)

    Runtime: ~200s+ (includes LLM API calls)
    """
    import shutil
    motion_dir = EVAL_DIR / "motion"
    config_main = motion_dir / "test_config.json"
    config_comprehensive = motion_dir / "test_config_comprehensive.json"
    config_backup = motion_dir / "test_config_backup.json"

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_comprehensive, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.motion.motion_agent",
            eval_dataset_file_path_or_dir=str(
                motion_dir / "motion_agent.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()
