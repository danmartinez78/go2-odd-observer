"""
Agent definitions for ODD analysis pipeline.
Phase 1.4.4 - Type-driven COD construction with Python tools.
"""

from .perception import create_perception_agent, PERCEPTION_AGENT_VERSION
from .motion import create_motion_agent, MOTION_AGENT_VERSION
from .collision import create_collision_agent, COLLISION_AGENT_VERSION
from .odd_spec import create_odd_spec_agent, AGENT_VERSION as ODD_SPEC_VERSION
from .evaluator import create_evaluator_agent, EVALUATOR_AGENT_VERSION
from .report import create_report_agent, REPORT_AGENT_VERSION

# Agent versions for metadata tracking
AGENT_VERSIONS = {
    'OddSpecAgent': ODD_SPEC_VERSION,
    'PerceptionAgent': PERCEPTION_AGENT_VERSION,
    'MotionAgent': MOTION_AGENT_VERSION,
    'CollisionAgent': COLLISION_AGENT_VERSION,
    'EvaluatorAgent': EVALUATOR_AGENT_VERSION,
    'ReportAgent': REPORT_AGENT_VERSION,
}

__all__ = [
    # Sensor agents (v5.0.0 - per-window typed measurements)
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
