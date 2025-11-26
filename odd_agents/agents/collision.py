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
COLLISION_AGENT_VERSION = "6.0.0"


def create_collision_agent(
    scenario_path: str, genai_client: Client, model: str, api_key: str
) -> Agent:
    """Create consolidated collision agent (loop + summary merged)."""
    from ..tools.perception import create_perception_tools

    list_windows_tool, _ = create_perception_tools(
        scenario_path, genai_client, model)
    analyze_collision_tool = create_collision_tools(
        scenario_path, genai_client, model)

    return Agent(
        name="CollisionAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=[list_windows_tool, analyze_collision_tool],
        output_key="temp:collision_output",
        instruction="""You orchestrate collision detection using tools and provide temporal reasoning.

INPUT:
- ODD Specification: {temp:odd_spec?} - extract collision-related dimensions if any
- Tools: list_windows_tool(), analyze_collision_tool(window_id, odd_context)

WORKFLOW:
1. Extract relevant ODD dimensions for collision (if any defined)
2. Call list_windows_tool() to get available windows
3. For EACH window: Call analyze_collision_tool(window_id, odd_context={})
4. Collect tool outputs (each has: odd_measurements, explanation, key_insights, collision_detected)
5. Analyze temporal patterns - do collisions cluster? escalate?
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
    "odd_trends": "Collision patterns across windows",
    "anomalies": ["Window IDs with collisions or near-misses"],
    "concerns": ["Safety issues requiring attention"]
  },
  "summary_insights": [
    "Overall collision status",
    "Key safety observations"
  ],
  "collision_stats": {
    "total_windows": 0,
    "collisions_detected": 0
  }
}

RULES:
1. per_window.measurements: COPY from tool's odd_measurements verbatim
2. temporal_analysis: YOUR reasoning about collision patterns
3. summary_insights: Aggregate key_insights from tools + your observations""",
    )
