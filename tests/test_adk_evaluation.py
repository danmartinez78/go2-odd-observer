"""
Agent evaluation tests using ADK's AgentEvaluator.

This uses ADK's built-in evaluation framework following toy example patterns.

NOTE: Loop agents test BOTH orchestration AND inference quality.
When loop agents call tools (e.g., analyze_window_perception_tool), those tools
make actual LLM calls for inference. Rubric tests evaluate that inference quality.
"""

import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator
from pathlib import Path


# Path to evaluation test files
EVAL_DIR = Path(__file__).parent / "evaluation"


# =============================================================================
# PERCEPTION AGENT EVALUATION TESTS
# Tests orchestration + multimodal inference (camera + LiDAR BEV analysis)
# =============================================================================


@pytest.mark.asyncio
async def test_perception_tool_trajectory_only():
    """
    Fast perception test - tool trajectory only.
    
    Validates correct tool usage without LLM judging.
    Tests: list_windows → analyze_window_perception (x2)
    Runtime: ~20s
    """
    import shutil
    perception_dir = EVAL_DIR / "perception"
    config_main = perception_dir / "test_config.json"
    config_tool = perception_dir / "test_config_tool_traj.json"
    config_backup = perception_dir / "test_config_backup.json"

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_tool, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.perception.perception_agent",
            eval_dataset_file_path_or_dir=str(perception_dir / "perception_agent.test.json"),
            num_runs=1,
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
    
    Evaluates JSON output structure AND inference quality:
    - Valid JSON structure
    - Complete window analysis (all windows processed)
    - Data integrity (tool outputs preserved)
    
    NOTE: This tests INFERENCE quality because the loop agent calls
    analyze_window_perception_tool which makes actual multimodal LLM calls.
    
    Runtime: ~80s (makes LLM API calls for inference + judging)
    """
    import shutil
    perception_dir = EVAL_DIR / "perception"
    config_main = perception_dir / "test_config.json"
    config_rubric = perception_dir / "test_config_rubric_only.json"
    config_backup = perception_dir / "test_config_backup.json"

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_rubric, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.perception.perception_agent",
            eval_dataset_file_path_or_dir=str(perception_dir / "perception_agent.test.json"),
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
    
    Runtime: ~120s+ (includes inference + judging LLM calls)
    """
    import shutil
    perception_dir = EVAL_DIR / "perception"
    config_main = perception_dir / "test_config.json"
    config_comprehensive = perception_dir / "test_config_comprehensive.json"
    config_backup = perception_dir / "test_config_backup.json"

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_comprehensive, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.perception.perception_agent",
            eval_dataset_file_path_or_dir=str(perception_dir / "perception_agent.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()


# =============================================================================
# MOTION AGENT EVALUATION TESTS
# Tests orchestration + motion inference (IMU data analysis)
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
    config_tool = motion_dir / "test_config_tool_traj.json"
    config_backup = motion_dir / "test_config_backup.json"

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_tool, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.motion.motion_agent",
            eval_dataset_file_path_or_dir=str(motion_dir / "motion_agent.test.json"),
            num_runs=1,
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
    
    Evaluates JSON output quality AND inference quality:
    - Valid JSON structure (windows_analyzed, overall_stats, per_window_motion)
    - Motion analysis completeness (all windows, statistics calculated)
    - Motion metrics validity (physically plausible values)
    
    NOTE: This tests INFERENCE quality because the loop agent calls
    analyze_motion_tool which makes actual LLM calls to analyze IMU data.
    
    Runtime: ~80s (makes LLM API calls for inference + judging)
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
            eval_dataset_file_path_or_dir=str(motion_dir / "motion_agent.test.json"),
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
    
    Runtime: ~200s+ (includes inference + judging LLM calls)
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
            eval_dataset_file_path_or_dir=str(motion_dir / "motion_agent.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()


# =============================================================================
# COLLISION AGENT EVALUATION TESTS
# Tests orchestration + collision inference (IMU-based collision detection)
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.slow
async def test_collision_rubric_quality():
    """
    Collision agent with rubric-based judging (tool use + output quality).

    Runtime: ~70-90s (inference + judging)
    """
    import shutil
    import importlib
    collision_dir = EVAL_DIR / "collision"
    config_main = collision_dir / "test_config.json"
    config_rubric = collision_dir / "test_config.json"
    config_backup = collision_dir / "test_config_backup.json"

    # Reload module so each test gets a fresh agent + genai client (avoids stale event loops)
    import tests.evaluation.collision.collision_agent as collision_agent_module
    importlib.reload(collision_agent_module)

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        if config_rubric != config_main:
            shutil.copy(config_rubric, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.collision.collision_agent",
            eval_dataset_file_path_or_dir=str(collision_dir / "collision_agent.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_collision_comprehensive():
    """
    Full collision agent evaluation (tool use + output + hallucinations).

    Runtime: ~90-120s (inference + judging)
    """
    import shutil
    import importlib
    collision_dir = EVAL_DIR / "collision"
    config_main = collision_dir / "test_config.json"
    config_comprehensive = collision_dir / "test_config_comprehensive.json"
    config_backup = collision_dir / "test_config_backup.json"

    # Reload module so each test gets a fresh agent + genai client (avoids stale event loops)
    import tests.evaluation.collision.collision_agent as collision_agent_module
    importlib.reload(collision_agent_module)

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_comprehensive, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.collision.collision_agent",
            eval_dataset_file_path_or_dir=str(collision_dir / "collision_agent.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()


# =============================================================================
# EVALUATOR AGENT EVALUATION TESTS
# Tests COD construction + verdict synthesis (uses artifacts/fixtures)
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.slow
async def test_evaluator_rubric_quality():
    """
    Evaluator agent with rubric-based judging (tool use + output quality).

    Runtime: ~70-90s (inference + judging)
    """
    import shutil
    import importlib
    evaluator_dir = EVAL_DIR / "evaluator"
    config_main = evaluator_dir / "test_config.json"
    config_rubric = evaluator_dir / "test_config.json"
    config_backup = evaluator_dir / "test_config_backup.json"

    import tests.evaluation.evaluator.evaluator_agent as evaluator_agent_module
    importlib.reload(evaluator_agent_module)

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        if config_rubric != config_main:
            shutil.copy(config_rubric, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.evaluator.evaluator_agent",
            eval_dataset_file_path_or_dir=str(evaluator_dir / "evaluator_agent.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_evaluator_comprehensive():
    """
    Full evaluator agent evaluation (tool use + output + hallucinations).

    Runtime: ~90-120s (inference + judging)
    """
    import shutil
    import importlib
    evaluator_dir = EVAL_DIR / "evaluator"
    config_main = evaluator_dir / "test_config.json"
    config_comprehensive = evaluator_dir / "test_config_comprehensive.json"
    config_backup = evaluator_dir / "test_config_backup.json"

    import tests.evaluation.evaluator.evaluator_agent as evaluator_agent_module
    importlib.reload(evaluator_agent_module)

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_comprehensive, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.evaluator.evaluator_agent",
            eval_dataset_file_path_or_dir=str(evaluator_dir / "evaluator_agent.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()


# =============================================================================
# REPORT AGENT EVALUATION TESTS
# Tests report synthesis (single tool call, state-fed)
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.slow
async def test_report_rubric_quality():
    """
    Report agent with rubric-based judging (tool use + output quality).

    Runtime: ~60-80s (inference + judging)
    """
    import shutil
    import importlib
    report_dir = EVAL_DIR / "report"
    config_main = report_dir / "test_config.json"
    config_rubric = report_dir / "test_config.json"
    config_backup = report_dir / "test_config_backup.json"

    import tests.evaluation.report.report_agent as report_agent_module
    importlib.reload(report_agent_module)

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        if config_rubric != config_main:
            shutil.copy(config_rubric, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.report.report_agent",
            eval_dataset_file_path_or_dir=str(report_dir / "report_agent.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_report_comprehensive():
    """
    Full report agent evaluation (tool use + output + hallucinations).

    Runtime: ~80-100s (inference + judging)
    """
    import shutil
    import importlib
    report_dir = EVAL_DIR / "report"
    config_main = report_dir / "test_config.json"
    config_comprehensive = report_dir / "test_config_comprehensive.json"
    config_backup = report_dir / "test_config_backup.json"

    import tests.evaluation.report.report_agent as report_agent_module
    importlib.reload(report_agent_module)

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_comprehensive, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.report.report_agent",
            eval_dataset_file_path_or_dir=str(report_dir / "report_agent.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()


# =============================================================================
# ODD SPEC AGENT EVALUATION TESTS
# Tests single-inference agent (NO TOOLS) - NL text → structured JSON
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.slow
async def test_odd_spec_rubric_quality():
    """
    Test ODD Spec agent with rubric-based LLM judging.
    
    NOTE: This agent has NO TOOLS - it's a single inference agent.
    Input: Natural language ODD description (user request string)
    Output: Structured JSON specification
    
    Evaluates:
    - JSON structure validity (required keys, correct nesting)
    - Categorical constraint extraction (allowed vs prohibited)
    - Numeric constraint inference (vague terms → precise ranges)
    - Default inference (conservative assumptions when info sparse)
    
    Pattern difference from loop agents:
    - No expected_tool_uses (this agent doesn't call tools)
    - Test cases are different NL descriptions, not window IDs
    - Rubrics focus on NL→JSON conversion quality
    
    Runtime: ~40-50s (2 test cases × LLM inference + judging)
    """
    import shutil
    odd_spec_dir = EVAL_DIR / "odd_spec"
    config_main = odd_spec_dir / "test_config.json"
    config_rubric = odd_spec_dir / "test_config_rubric_only.json"
    config_backup = odd_spec_dir / "test_config_backup.json"

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_rubric, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.odd_spec.odd_spec_agent",
            eval_dataset_file_path_or_dir=str(odd_spec_dir / "odd_spec_agent.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_odd_spec_comprehensive():
    """
    Full ODD Spec agent evaluation.
    
    Tests:
    - Rubric-based quality (structure, extraction, inference)
    - Hallucinations (no fabricated constraints)
    
    Note: No tool_trajectory criterion (this agent has no tools!)
    
    Runtime: ~60-80s (includes inference + judging + hallucination detection)
    """
    import shutil
    odd_spec_dir = EVAL_DIR / "odd_spec"
    config_main = odd_spec_dir / "test_config.json"
    config_comprehensive = odd_spec_dir / "test_config_comprehensive.json"
    config_backup = odd_spec_dir / "test_config_backup.json"

    import importlib
    import tests.evaluation.odd_spec.odd_spec_agent as odd_spec_agent_module
    importlib.reload(odd_spec_agent_module)

    if config_main.exists():
        shutil.copy(config_main, config_backup)
        shutil.copy(config_comprehensive, config_main)

    try:
        await AgentEvaluator.evaluate(
            agent_module="tests.evaluation.odd_spec.odd_spec_agent",
            eval_dataset_file_path_or_dir=str(odd_spec_dir / "odd_spec_agent.test.json"),
        )
    finally:
        if config_backup.exists():
            shutil.copy(config_backup, config_main)
            config_backup.unlink()
