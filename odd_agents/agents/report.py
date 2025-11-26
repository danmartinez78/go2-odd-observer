"""
Report generation agent.
Uses file-reading tool for efficient data access, LLM for summarization.
"""

from pathlib import Path
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool
import json


# Agent version
# Breaking: uses file-reading tool instead of blackboard
REPORT_AGENT_VERSION = "4.0.0"


def create_report_tools(scenario_path: Path):
    """Create file-reading tool for Report Agent."""
    from google.adk.tools.tool_context import ToolContext
    import json

    async def read_analysis_results_tool(tool_context: ToolContext) -> str:
        """
        Read all analysis results from blackboard.

        Returns JSON with ODD spec, sensor outputs, and evaluator output.
        No file I/O needed - reads directly from blackboard.
        """
        results = {
            "odd_spec": tool_context.get_value("temp:odd_spec") or {},
            "perception": tool_context.get_value("temp:perception_output") or {},
            "motion": tool_context.get_value("temp:motion_output") or {},
            "collision": tool_context.get_value("temp:collision_output") or {},
            "evaluator": tool_context.get_value("temp:evaluator_output") or {},
        }

        return json.dumps(results, indent=2)

    # Return FunctionTool wrapper
    return [FunctionTool(func=read_analysis_results_tool)]


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
- ODD Specification (v5.0.0): {temp:odd_spec?} (optional, can also read via tool)
- Tool: read_analysis_results() - reads all agent outputs from blackboard

STEPS:
1. Call read_analysis_results() to load all analysis results from blackboard
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
