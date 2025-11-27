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
# v7.0.0: Added save_motion_output_tool for artifact-based data handoff
# v7.1.0: Strengthened prompt to ensure save tool is called
# v7.2.0: Output summary to state, full data to artifact
# v7.3.0: Strict tool parameters for save tool - per_window, temporal_analysis, summary_insights
MOTION_AGENT_VERSION = "7.3.0"


def create_motion_agent(
    scenario_path: str, genai_client: Client, model: str, api_key: str
) -> Agent:
    """Create consolidated motion agent (loop + summary merged)."""
    from ..tools.perception import create_perception_tools

    list_windows_tool, _, _ = create_perception_tools(
        scenario_path, genai_client, model)
    analyze_motion_tool, save_motion_output = create_motion_tools(
        scenario_path, genai_client, model)

    return Agent(
        name="MotionAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=[list_windows_tool, analyze_motion_tool, save_motion_output],
        output_key="temp:motion_output",
        instruction="""You are a motion analysis agent. You MUST call tools to analyze windows and save results.

REQUIRED TOOLS (you MUST call all of these):
1. list_windows_tool() - get available windows
2. analyze_motion_tool(window_id, odd_context) - analyze each window
3. save_motion_output_tool(per_window, temporal_analysis, summary_insights) - save for COD

INPUT:
- ODD Specification: {temp:odd_spec?} - extract ego motion dimensions

MANDATORY WORKFLOW:
1. Extract relevant ODD dimensions for motion (ego: speed, accel, stability, etc.)
2. IMMEDIATELY call list_windows_tool() to get available windows
3. For EACH window: Call analyze_motion_tool(window_id, odd_context)
4. Build your data from tool results
5. Call save_motion_output_tool with EXPLICIT PARAMETERS (see below)
6. **FINAL STEP**: Output your SUMMARY JSON

CALLING save_motion_output_tool (STRICT PARAMETERS - pass each separately):
save_motion_output_tool(
    per_window=[
        {"window_id": "000", "measurements": {/* from tool's odd_measurements */}},
        {"window_id": "001", "measurements": {/* from tool's odd_measurements */}}
    ],
    temporal_analysis={
        "odd_trends": "How motion measurements change across windows",
        "anomalies": ["Window IDs with unusual motion patterns"],
        "concerns": ["Safety or stability issues detected"]
    },
    summary_insights=[
        "Key motion pattern from tool outputs",
        "Cross-window motion trend"
    ]
)

FINAL OUTPUT (summary for downstream agents - JSON only, no markdown):
{
  "windows_analyzed": 2,
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
1. Call save tool FIRST with EXPLICIT parameters (not a single dict!)
2. per_window MUST include measurements from each window's analyze tool response
3. Then output summary JSON
4. Summary goes to state for Evaluator's qualitative reasoning""",
    )
