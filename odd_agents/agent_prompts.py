"""
Agent prompt templates for metadata tracking.

These are the canonical prompt templates used by each agent.
Used for computing prompt hashes to track prompt drift over time.

When you modify an agent's instruction, update the corresponding
template here to keep metadata accurate.
"""

# Read prompts directly from agent files to avoid duplication
# This ensures prompts stay in sync with actual agent code


def get_odd_spec_prompt():
    """Get ODD Spec agent prompt template."""
    from .agents.odd_spec import create_odd_spec_agent
    # Create dummy agent to extract instruction
    dummy = create_odd_spec_agent(api_key="dummy", model="dummy")
    return dummy.instruction


def get_perception_loop_prompt():
    """Get Perception Loop agent prompt template."""
    from .agents.perception import create_perception_loop_agent
    from pathlib import Path
    from google.genai import Client
    # Create dummy agent to extract instruction
    dummy = create_perception_loop_agent(
        scenario_path=Path("."),
        genai_client=None,  # Won't be used
        model="dummy",
        api_key="dummy"
    )
    return dummy.instruction


def get_perception_summary_prompt():
    """Get Perception Summary agent prompt template."""
    from .agents.perception import create_perception_summary_agent
    dummy = create_perception_summary_agent(api_key="dummy", model="dummy")
    return dummy.instruction


def get_motion_loop_prompt():
    """Get Motion Loop agent prompt template."""
    from .agents.motion import create_motion_loop_agent
    from pathlib import Path
    from google.genai import Client
    dummy = create_motion_loop_agent(
        scenario_path=".",
        genai_client=None,
        model="dummy",
        api_key="dummy"
    )
    return dummy.instruction


def get_motion_summary_prompt():
    """Get Motion Summary agent prompt template."""
    from .agents.motion import create_motion_summary_agent
    dummy = create_motion_summary_agent(api_key="dummy", model="dummy")
    return dummy.instruction


def get_collision_loop_prompt():
    """Get Collision Loop agent prompt template."""
    from .agents.collision import create_collision_loop_agent
    from google.genai import Client
    dummy = create_collision_loop_agent(
        scenario_path=".",
        genai_client=None,
        model="dummy",
        api_key="dummy"
    )
    return dummy.instruction


def get_collision_summary_prompt():
    """Get Collision Summary agent prompt template."""
    from .agents.collision import create_collision_summary_agent
    dummy = create_collision_summary_agent(api_key="dummy", model="dummy")
    return dummy.instruction


def get_cod_classifier_prompt():
    """Get COD Classifier agent prompt template."""
    from .agents.cod_classifier import create_cod_classifier_agent
    dummy = create_cod_classifier_agent(api_key="dummy", model="dummy")
    return dummy.instruction


def get_odd_compliance_prompt():
    """Get ODD Compliance agent prompt template."""
    from .agents.compliance import create_odd_compliance_agent
    dummy = create_odd_compliance_agent(api_key="dummy", model="dummy")
    return dummy.instruction


def get_report_prompt():
    """Get Report agent prompt template."""
    from .agents.report import create_report_agent
    dummy = create_report_agent(api_key="dummy", model="dummy")
    return dummy.instruction


# Lazy-loaded prompt registry
_PROMPT_CACHE = {}


def get_all_prompts():
    """Get all agent prompts as a dict."""
    if not _PROMPT_CACHE:
        _PROMPT_CACHE.update({
            'OddSpecAgent': get_odd_spec_prompt(),
            'PerceptionLoopAgent': get_perception_loop_prompt(),
            'PerceptionSummaryAgent': get_perception_summary_prompt(),
            'MotionLoopAgent': get_motion_loop_prompt(),
            'MotionSummaryAgent': get_motion_summary_prompt(),
            'CollisionLoopAgent': get_collision_loop_prompt(),
            'CollisionSummaryAgent': get_collision_summary_prompt(),
            'CodMeasurementAgent': get_cod_classifier_prompt(),
            'OddComplianceAgent': get_odd_compliance_prompt(),
            'ReportAgent': get_report_prompt(),
        })
    return _PROMPT_CACHE
