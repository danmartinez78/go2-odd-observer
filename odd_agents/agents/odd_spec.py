"""
ODD specification agent.
Extracted from odd_workflow_full.py (reference implementation).
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini

from ..config import GEMINI_MODEL_ODD_SPEC, GOOGLE_API_KEY


odd_spec_agent = Agent(
    name="OddSpecAgent",
    model=Gemini(model=GEMINI_MODEL_ODD_SPEC, api_key=GOOGLE_API_KEY),
    output_key="temp:odd_spec",
    instruction="""You are an Operational Design Domain (ODD) specification expert.

TASK: Convert the provided natural language ODD description into a formal specification.

The user will provide the ODD description in their query.

CONVERT the natural language description to formal specification with clear thresholds:

Return ONLY valid JSON:
{
  "odd_specification": {
    "categorical_constraints": {
      "environment_type": {
        "allowed": ["indoor_office", "indoor_corridor"],
        "prohibited": ["outdoor_urban", "outdoor_natural", "stairs"]
      },
      "lighting_conditions": {
        "allowed": ["bright", "dim"],
        "prohibited": ["dark", "low_light"]
      },
      "terrain_type": {
        "allowed": ["smooth"],
        "prohibited": ["moderate", "rough", "very_rough"]
      }
    },
    "numeric_constraints": {
      "max_speed_mps": {
        "in_odd": [0.0, 1.5],
        "boundary": [1.5, 2.0],
        "out_odd": [2.0, "inf"]
      },
      "obstacle_density": {
        "in_odd": [0.0, 0.6],
        "boundary": [0.6, 0.8],
        "out_odd": [0.8, 1.0]
      },
      "traversability_score": {
        "in_odd": [0.5, 1.0],
        "boundary": [0.3, 0.5],
        "out_odd": [0.0, 0.3]
      },
      "collision_risk": {
        "in_odd": [0.0, 0.3],
        "boundary": [0.3, 0.5],
        "out_odd": [0.5, 1.0]
      }
    }
  },
  "odd_summary": "Brief description of what this ODD specification defines"
}

No explanations outside JSON.""",
)
