"""
Agent definitions for ODD analysis pipeline.
Extracted from odd_workflow_full.py (reference implementation).
"""

from .perception import perception_loop_agent, perception_summary_agent
from .motion import motion_loop_agent, motion_summary_agent
from .collision import collision_loop_agent, collision_summary_agent
from .odd_spec import odd_spec_agent
from .cod_classifier import cod_classifier_agent
from .compliance import odd_compliance_agent
from .report import report_agent

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
