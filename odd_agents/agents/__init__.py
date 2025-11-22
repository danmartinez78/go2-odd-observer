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
]

__all__ = [
    # Perception agents
    "perception_loop_agent",
    "perception_summary_agent",

    # Motion agents
    "motion_loop_agent",
    "motion_summary_agent",

    # Collision agents
    "collision_loop_agent",
    "collision_summary_agent",

    # Analysis agents
    "odd_spec_agent",
    "cod_classifier_agent",
    "odd_compliance_agent",
    "report_agent",
]
