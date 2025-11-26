"""
Report generation agent.
Uses file-reading tool for efficient data access, LLM for summarization.
"""

from pathlib import Path
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.genai import Client
from google.adk.tools import Tool
from pydantic import BaseModel, Field
import json


# Agent version
# Breaking: uses file-reading tool instead of blackboard
REPORT_AGENT_VERSION = "4.0.0"


class ReadAnalysisResultsInput(BaseModel):
    """Input for read_analysis_results tool."""
    scenario_path: str = Field(
        description="Absolute path to scenario directory")


def create_report_tools(scenario_path: Path):
    """Create file-reading tool for Report Agent."""

    def read_analysis_results_tool(scenario_path: str) -> str:
        """
        Read all analysis results from files.

        Returns JSON with ODD spec, sensor outputs, and evaluator output.
        Avoids loading massive data onto blackboard.
        """
        from pathlib import Path
        import json

        scenario = Path(scenario_path)
        results = {}

        # Read all agent outputs
        for agent_file in ["odd_spec.json", "perception_output.json",
                           "motion_output.json", "collision_output.json",
                           "evaluator_output.json"]:
            file_path = scenario / agent_file
            if file_path.exists():
                with open(file_path, 'r') as f:
                    agent_name = agent_file.replace(
                        "_output.json", "").replace(".json", "")
                    results[agent_name] = json.load(f)

        return json.dumps(results, indent=2)

    read_analysis = Tool(
        name="read_analysis_results",
        description="Read all analysis results from files to generate report",
        parameters=ReadAnalysisResultsInput,
        callable=read_analysis_results_tool
    )

    return [read_analysis]


def create_report_agent(scenario_path: Path, api_key: str, model: str) -> Agent:
    """Create a new ReportAgent instance with file-reading tool."""
    tools = create_report_tools(scenario_path)

    return Agent(
        name="ReportAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=tools,
        instruction="""You generate comprehensive human-readable reports for ODD/COD analysis.

TASK: Produce executive summary and structured report.

INPUT:
- ODD Specification (v5.0.0): {temp:odd_spec?} (optional, can also read from file)
- Tool: read_analysis_results(scenario_path) - reads all agent outputs from files

STEPS:
1. Call read_analysis_results() to load all analysis results
2. Extract key findings from:
   - ODD spec: designed operating conditions
   - Sensor outputs: what was observed per window
   - Evaluator: COD region, compliance verdict, violations
3. Generate executive summary (2-3 sentences)
4. Identify key findings and recommendations

OUTPUT (JSON only, no markdown):
{
  "executive_summary": "<2-3 sentence overview of scenario and compliance>",
  "scenario_metadata": {
    "total_windows_analyzed": <int>,
    "scenario_name": "<from path>",
    "data_source": "simulation|real_world"
  },
  "compliance_summary": {
    "verdict": "IN_ODD|OUT_ODD|BOUNDARY",
    "region_distance": <float from evaluator>,
    "critical_axes": ["<axes with violations>"],
    "temporal_stability": "<from evaluator>"
  },
  "key_findings": [
    "<Finding 1: perception highlights>",
    "<Finding 2: motion highlights>",
    "<Finding 3: compliance highlights>"
  ],
  "recommendations": [
    "<Recommendation based on violations>",
    "<Recommendation for ODD refinement if needed>"
  ],
  "detailed_analysis": {
    "perception": "<Summary of perception observations>",
    "motion": "<Summary of motion observations>",
    "collision": "<Summary of collision findings>",
    "evaluator": "<Summary of COD and compliance analysis>"
  }
}

Focus on actionable insights. Use Python tool for data loading, LLM for summarization.""",
    )
