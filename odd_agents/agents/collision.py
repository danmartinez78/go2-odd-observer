"""
Collision detection agent (consolidated loop + summary).
Single agent that orchestrates tools AND produces final output.
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.genai import Client

from ..tools.collision import create_collision_tools


# Agent version
# v6.0.0: Standardized output with per_window, temporal_analysis, summary_insights
# v7.0.0: Added save_collision_output_tool for artifact-based data handoff
# v7.1.0: Strengthened prompt to ensure save tool is called
# v7.2.0: Output summary to state, full data to artifact
# v7.3.0: Strict tool parameters for save tool - per_window, temporal_analysis, summary_insights, collision_stats
COLLISION_AGENT_VERSION = "7.3.0"


def create_collision_agent(
    scenario_path: str, genai_client: Client, model: str, api_key: str
) -> Agent:
    """Create consolidated collision agent (loop + summary merged)."""
    from ..tools.perception import create_perception_tools

    list_windows_tool, _, _ = create_perception_tools(
        scenario_path, genai_client, model)
    analyze_collision_tool, save_collision_output = create_collision_tools(
        scenario_path, genai_client, model)

    return Agent(
        name="CollisionAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=[list_windows_tool, analyze_collision_tool, save_collision_output],
        output_key="temp:collision_output",
        instruction="""You are a collision detection agent. You MUST call tools to analyze windows and save results.

REQUIRED TOOLS (you MUST call all of these):
1. list_windows_tool() - get available windows
2. analyze_collision_tool(window_id, odd_context) - analyze each window
3. save_collision_output_tool(per_window, temporal_analysis, summary_insights, collision_stats) - save for COD

INPUT:
- ODD Specification: {temp:odd_spec?} - extract collision-related dimensions if any

MANDATORY WORKFLOW:
1. Extract relevant ODD dimensions for collision (if any defined)
2. IMMEDIATELY call list_windows_tool() to get available windows
3. For EACH window: Call analyze_collision_tool(window_id, odd_context={})
4. Build your data from tool results
5. Call save_collision_output_tool with EXPLICIT PARAMETERS (see below)
6. **FINAL STEP**: Output your SUMMARY JSON

CALLING save_collision_output_tool (STRICT PARAMETERS - pass each separately):
save_collision_output_tool(
    per_window=[
        {"window_id": "000", "measurements": {/* from tool's odd_measurements */}},
        {"window_id": "001", "measurements": {/* from tool's odd_measurements */}}
    ],
    temporal_analysis={
        "odd_trends": "Collision patterns across windows",
        "anomalies": ["Window IDs with collisions or near-misses"],
        "concerns": ["Safety issues requiring attention"]
    },
    summary_insights=[
        "Overall collision status",
        "Key safety observations"
    ],
    collision_stats={
        "total_windows": 2,
        "collisions_detected": 0
    }
)

FINAL OUTPUT (summary for downstream agents - JSON only, no markdown):
{
  "windows_analyzed": 2,
  "collisions_detected": 0,
  "temporal_analysis": {
    "odd_trends": "Collision patterns across windows",
    "anomalies": ["Window IDs with collisions or near-misses"],
    "concerns": ["Safety issues requiring attention"]
  },
  "summary_insights": [
    "Overall collision status",
    "Key safety observations"
  ]
}

RULES:
1. Call save tool FIRST with EXPLICIT parameters (not a single dict!)
2. per_window MUST include measurements from each window's analyze tool response
3. Then output summary JSON
4. Summary goes to state for Evaluator's qualitative reasoning""",
    )
