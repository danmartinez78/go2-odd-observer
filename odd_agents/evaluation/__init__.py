"""
Agent evaluation framework using ADK's built-in evaluation capabilities.

This module provides evaluation rubrics and test data for assessing agent
output quality using ADK's AgentEvaluator with criteria like:
- tool_trajectory_avg_score: Tool call trajectory matching
- rubric_based_final_response_quality_v1: Custom rubrics for response quality
- rubric_based_tool_use_quality_v1: Custom rubrics for tool usage
- hallucinations_v1: Grounding check
- safety_v1: Safety check

Key patterns:
- Use different judge model (gemini-2.5-pro) than agent model (gemini-flash-lite)
- Define custom rubrics for each agent type
- Create .test.json files in ADK EvalSet/EvalCase schema
- Use AgentEvaluator.evaluate() for programmatic testing
"""

from .rubrics import (
    PERCEPTION_RUBRICS,
    MOTION_RUBRICS,
    COLLISION_RUBRICS,
    ODD_SPEC_RUBRICS,
    COD_RUBRICS,
    COMPLIANCE_RUBRICS,
    REPORT_RUBRICS,
)

__all__ = [
    "PERCEPTION_RUBRICS",
    "MOTION_RUBRICS",
    "COLLISION_RUBRICS",
    "ODD_SPEC_RUBRICS",
    "COD_RUBRICS",
    "COMPLIANCE_RUBRICS",
    "REPORT_RUBRICS",
]
