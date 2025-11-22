"""
Agent evaluation framework using LLM-as-judge pattern.

This module provides evaluation capabilities for assessing agent output quality
using a different/larger model as judge to avoid model similarity bias.

Key patterns:
- Use gemini-2.5-pro (or larger) as judge for agents using flash-lite
- Majority voting across multiple samples for robustness
- Custom rubrics for different agent types
- Structured evaluation reports with per-rubric scores
"""

from .base import AgentEvaluator, EvaluationResult, EvaluationCriteria
from .rubrics import (
    PERCEPTION_RUBRICS,
    MOTION_RUBRICS,
    COLLISION_RUBRICS,
    ODD_SPEC_RUBRICS,
    COD_RUBRICS,
    COMPLIANCE_RUBRICS,
    REPORT_RUBRICS,
)
from .llm_judge import LLMJudge
from .reporter import EvaluationReporter, compare_evaluations

__all__ = [
    "AgentEvaluator",
    "EvaluationResult",
    "EvaluationCriteria",
    "LLMJudge",
    "EvaluationReporter",
    "compare_evaluations",
    "PERCEPTION_RUBRICS",
    "MOTION_RUBRICS",
    "COLLISION_RUBRICS",
    "ODD_SPEC_RUBRICS",
    "COD_RUBRICS",
    "COMPLIANCE_RUBRICS",
    "REPORT_RUBRICS",
]
