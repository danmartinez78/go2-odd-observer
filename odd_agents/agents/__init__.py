"""
Agent definitions for ODD analysis pipeline.
Phase 1.6 - Temporal analysis pattern: tools do per-window, agents do higher-order.
"""

from .perception import create_perception_agent, PERCEPTION_AGENT_VERSION
from .motion import create_motion_agent, MOTION_AGENT_VERSION
from .collision import create_collision_agent, COLLISION_AGENT_VERSION
from .odd_spec import create_odd_spec_agent, AGENT_VERSION as ODD_SPEC_VERSION
from .evaluator import create_evaluator_agent, EVALUATOR_AGENT_VERSION
from .report import create_report_agent, REPORT_AGENT_VERSION

# Import tool versions
from ..tools.cod_construction import COD_TOOL_VERSION, CATEGORICAL_AGENT_MODEL

# Agent versions for metadata tracking
AGENT_VERSIONS = {
    'OddSpecAgent': ODD_SPEC_VERSION,
    'PerceptionAgent': PERCEPTION_AGENT_VERSION,
    'MotionAgent': MOTION_AGENT_VERSION,
    'CollisionAgent': COLLISION_AGENT_VERSION,
    'EvaluatorAgent': EVALUATOR_AGENT_VERSION,
    'ReportAgent': REPORT_AGENT_VERSION,
    # Tool versions (not ADK agents, but use LLM calls)
    'CODTool': COD_TOOL_VERSION,
    'CategoricalMicroAgent': f"1.0.0 ({CATEGORICAL_AGENT_MODEL})",
}

__all__ = [
    # Sensor agents (v10.0.0 - temporal analysis pattern)
    "create_perception_agent",
    "create_motion_agent",
    "create_collision_agent",

    # Analysis agents
    "create_odd_spec_agent",
    "create_evaluator_agent",
    "create_report_agent",

    # Metadata
    "AGENT_VERSIONS",
]
