"""
Agent definitions for ODD analysis pipeline.
Consolidated architecture: 6 agents (merged loop + summary into single agents).
"""

from .perception import create_perception_agent, PERCEPTION_AGENT_VERSION
from .motion import create_motion_agent, MOTION_AGENT_VERSION
from .collision import create_collision_agent, COLLISION_AGENT_VERSION
from .odd_spec import create_odd_spec_agent, AGENT_VERSION as ODD_SPEC_VERSION
from .cod_classifier import create_cod_classifier_agent, COD_CLASSIFIER_VERSION
from .compliance import create_odd_compliance_agent, ODD_COMPLIANCE_VERSION
from .report import create_report_agent, REPORT_AGENT_VERSION

# Agent versions for metadata tracking
AGENT_VERSIONS = {
    'OddSpecAgent': ODD_SPEC_VERSION,
    'PerceptionAgent': PERCEPTION_AGENT_VERSION,
    'MotionAgent': MOTION_AGENT_VERSION,
    'CollisionAgent': COLLISION_AGENT_VERSION,
    'CodMeasurementAgent': COD_CLASSIFIER_VERSION,
    'OddComplianceAgent': ODD_COMPLIANCE_VERSION,
    'ReportAgent': REPORT_AGENT_VERSION,
}

__all__ = [
    # Consolidated agents (v4.0.0)
    "create_perception_agent",
    "create_motion_agent",
    "create_collision_agent",

    # Analysis agents
    "create_odd_spec_agent",
    "create_cod_classifier_agent",
    "create_odd_compliance_agent",
    "create_report_agent",

    # Metadata
    "AGENT_VERSIONS",
]
