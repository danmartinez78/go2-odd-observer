"""
Agent definitions for ODD analysis pipeline.
Extracted from odd_workflow_full.py (reference implementation).
"""

from .perception import create_perception_loop_agent, create_perception_summary_agent
from .motion import create_motion_loop_agent, create_motion_summary_agent
from .collision import create_collision_loop_agent, create_collision_summary_agent
from .odd_spec import create_odd_spec_agent
from .cod_classifier import create_cod_classifier_agent
from .compliance import create_odd_compliance_agent
from .report import create_report_agent

# Agent versions for metadata tracking
AGENT_VERSIONS = {
    'OddSpecAgent': '2.0.0',
    'PerceptionLoopAgent': '2.0.0',
    'PerceptionSummaryAgent': '2.0.0',
    'MotionLoopAgent': '2.0.0',
    'MotionSummaryAgent': '2.0.0',
    'CollisionLoopAgent': '2.0.0',
    'CollisionSummaryAgent': '2.0.0',
    # Note: Agent name is CodMeasurementAgent, not CodClassifierAgent
    'CodMeasurementAgent': '2.0.0',
    'OddComplianceAgent': '2.0.0',
    'ReportAgent': '2.0.0',
}

__all__ = [
    # Perception agents
    "create_perception_loop_agent",
    "create_perception_summary_agent",

    # Motion agents
    "create_motion_loop_agent",
    "create_motion_summary_agent",

    # Collision agents
    "create_collision_loop_agent",
    "create_collision_summary_agent",

    # Analysis agents
    "create_odd_spec_agent",
    "create_cod_classifier_agent",
    "create_odd_compliance_agent",
    "create_report_agent",

    # Metadata
    "AGENT_VERSIONS",
]
