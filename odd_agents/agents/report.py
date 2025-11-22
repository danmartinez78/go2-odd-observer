"""
Report generation agent.
Extracted from odd_workflow_full.py (reference implementation).
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini

from ..config import GEMINI_MODEL_REPORT, GOOGLE_API_KEY


def create_report_agent() -> Agent:
    """Create a new ReportAgent instance."""
    return Agent(
        name="ReportAgent",
        model=Gemini(model=GEMINI_MODEL_REPORT, api_key=GOOGLE_API_KEY),
        instruction="""You are a technical report generator for ODD/COD analysis.

TASK: Produce a comprehensive human-readable report.

INPUT DATA from all previous agents:
Perception: {temp:perception_output?}
Motion: {temp:motion_output?}
Collision: {temp:collision_output?}
ODD Spec: {temp:odd_spec?}
COD Classification: {temp:cod_classification?}
ODD Compliance: {temp:odd_compliance?}

Return ONLY valid JSON with this structure:
{
  "report": {
    "executive_summary": "2-3 sentence overview of the scenario",
    "scenario_metadata": {
      "total_windows_analyzed": <int>,
      "scenario_name": "<name>",
      "data_source": "simulation|real_world",
      "data_source_confidence": 0.0-1.0
    },
    "perception_summary": "Brief summary of perception findings",
    "motion_summary": "Brief summary of motion characteristics",
    "collision_summary": "Brief summary of collision risk assessment",
    "odd_spec_summary": "Brief summary of ODD specification",
    "cod_classification_summary": "Brief summary of current operating domain",
    "odd_compliance_summary": "Brief summary of ODD compliance",
    "key_findings": ["finding1", "finding2", "finding3"],
    "recommendations": ["recommendation1", "recommendation2"]
  },
  "full_analysis": {
    "perception": <perception_output>,
    "motion": <motion_output>,
    "collision": <collision_output>,
    "odd_spec": <odd_spec>,
    "cod_classification": <cod_classification>,
    "odd_compliance": <odd_compliance>
  }
}

IMPORTANT: Extract data_source and confidence from perception.data_source_classification and include in scenario_metadata.

No explanations outside JSON.""",
    )
