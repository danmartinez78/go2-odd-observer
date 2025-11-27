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


def get_perception_prompt():
    """Get Perception agent prompt template (consolidated)."""
    from .agents.perception import create_perception_agent
    from pathlib import Path
    from google.genai import Client
    # Create dummy agent to extract instruction
    dummy = create_perception_agent(
        scenario_path=Path("."),
        genai_client=None,  # Won't be used
        model="dummy",
        api_key="dummy"
    )
    return dummy.instruction


def get_motion_prompt():
    """Get Motion agent prompt template (consolidated)."""
    from .agents.motion import create_motion_agent
    from pathlib import Path
    from google.genai import Client
    dummy = create_motion_agent(
        scenario_path=".",
        genai_client=None,
        model="dummy",
        api_key="dummy"
    )
    return dummy.instruction


def get_collision_prompt():
    """Get Collision agent prompt template (consolidated)."""
    from .agents.collision import create_collision_agent
    from google.genai import Client
    dummy = create_collision_agent(
        scenario_path=".",
        genai_client=None,
        model="dummy",
        api_key="dummy"
    )
    return dummy.instruction


def get_cod_classifier_prompt():
    """Get COD Classifier agent prompt template (deprecated - Phase 1.4.3)."""
    return "(deprecated - replaced by Evaluator in Phase 1.4.4)"


def get_odd_compliance_prompt():
    """Get ODD Compliance agent prompt template (deprecated - Phase 1.4.3)."""
    return "(deprecated - replaced by Evaluator in Phase 1.4.4)"


def get_evaluator_prompt():
    """Get Evaluator agent prompt template."""
    from .agents.evaluator import create_evaluator_agent
    from pathlib import Path
    from google.genai import Client
    # Create dummy instance just to extract prompt
    dummy = create_evaluator_agent(
        scenario_path=Path("/tmp/dummy"),
        genai_client=Client(api_key="dummy"),
        model="dummy",
        api_key="dummy"
    )
    return dummy.instruction


def get_report_prompt():
    """Get Report agent prompt template."""
    from .agents.report import create_report_agent
    from pathlib import Path
    dummy = create_report_agent(
        scenario_path=Path("/tmp/dummy"),
        api_key="dummy",
        model="dummy"
    )
    return dummy.instruction


# Lazy-loaded prompt registry
_PROMPT_CACHE = {}


def get_all_prompts():
    """Get all agent prompts as a dict."""
    if not _PROMPT_CACHE:
        _PROMPT_CACHE.update({
            'OddSpecAgent': get_odd_spec_prompt(),
            'PerceptionAgent': get_perception_prompt(),
            'MotionAgent': get_motion_prompt(),
            'CollisionAgent': get_collision_prompt(),
            'EvaluatorAgent': get_evaluator_prompt(),
            'ReportAgent': get_report_prompt(),
        })
    return _PROMPT_CACHE
