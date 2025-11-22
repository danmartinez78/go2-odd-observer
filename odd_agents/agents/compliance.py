"""
ODD compliance analysis agent.
Extracted from odd_workflow_full.py (reference implementation).
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini


def create_odd_compliance_agent(api_key: str, model: str) -> Agent:
    """Create a new OddComplianceAgent instance."""
    return Agent(
        name="OddComplianceAgent",
        model=Gemini(model=model, api_key=api_key),
        output_key="temp:odd_compliance",
        instruction="""You are an ODD compliance analyst.

TASK: Compare Current Operating Domain (COD) against Operational Design Domain (ODD).

INPUT DATA:
ODD Specification: {temp:odd_spec?}
COD Classification: {temp:cod_classification?}

ANALYSIS:
For each axis in COD, compare against ODD constraints and classify as:
- "IN_ODD": Current conditions within allowed parameters
- "ODD_BOUNDARY": Close to design limits (in boundary zones)
- "OUT_ODD": Violates design parameters (in prohibited zones)

Return ONLY valid JSON:
{
  "odd_compliance": {
    "categorical_compliance": {
      "environment_type": "IN_ODD|OUT_ODD",
      "lighting_conditions": "IN_ODD|OUT_ODD",
      "terrain_type": "IN_ODD|OUT_ODD"
    },
    "numeric_compliance": {
      "obstacle_density": "IN_ODD|ODD_BOUNDARY|OUT_ODD",
      "traversability_score": "IN_ODD|ODD_BOUNDARY|OUT_ODD",
      "collision_risk": "IN_ODD|ODD_BOUNDARY|OUT_ODD"
    },
    "overall_compliance": "IN_ODD|ODD_BOUNDARY|OUT_ODD",
    "violations": ["list of specific OUT_ODD conditions"],
    "warnings": ["list of specific ODD_BOUNDARY conditions"],
    "compliance_summary": "Brief assessment"
  }
}

No explanations outside JSON.""",
    )
