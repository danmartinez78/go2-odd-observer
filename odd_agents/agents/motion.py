"""
Motion analysis agent (consolidated loop + summary).
Single agent that orchestrates tools AND produces final ODD-aligned output.
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.genai import Client

from ..tools.motion import create_motion_tools


# Agent version
# v6.0.0: Standardized output with per_window, temporal_analysis, summary_insights
MOTION_AGENT_VERSION = "6.0.0"


def create_motion_agent(
    scenario_path: str, genai_client: Client, model: str, api_key: str
) -> Agent:
    """Create consolidated motion agent (loop + summary merged)."""
    from ..tools.perception import create_perception_tools

    list_windows_tool, _ = create_perception_tools(
        scenario_path, genai_client, model)
    analyze_motion_tool = create_motion_tools(
        scenario_path, genai_client, model)

    return Agent(
        name="MotionAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=[list_windows_tool, analyze_motion_tool],
        output_key="temp:motion_output",
        instruction="""You orchestrate motion analysis using tools and provide temporal reasoning.

INPUT:
- ODD Specification: {temp:odd_spec?} - extract ego motion dimensions
- Tools: list_windows_tool(), analyze_motion_tool(window_id, odd_context)

WORKFLOW:
1. Extract relevant ODD dimensions for motion (ego: speed, accel, stability, etc.)
2. Call list_windows_tool() to get available windows
3. For EACH window: Call analyze_motion_tool(window_id, odd_context)
4. Collect tool outputs (each has: odd_measurements, explanation, key_insights, motion_state)
5. Analyze temporal patterns across windows
6. Produce structured output

CRITICAL: You MUST call the tools for each window. Do NOT skip tool calls.

OUTPUT (JSON only, no markdown):
{
  "per_window": [
    {
      "window_id": "000",
      "measurements": {
        // COPY directly from tool's odd_measurements
      }
    }
  ],
  "temporal_analysis": {
    "odd_trends": "How motion measurements change across windows",
    "anomalies": ["Window IDs with unusual motion patterns"],
    "concerns": ["Safety or stability issues detected"]
  },
  "summary_insights": [
    "Key motion pattern from tool outputs",
    "Cross-window motion trend"
  ]
}

RULES:
1. per_window.measurements: COPY from tool's odd_measurements verbatim
2. temporal_analysis: YOUR reasoning about motion patterns across windows
3. summary_insights: Aggregate key_insights from tools + your observations""",
    )
