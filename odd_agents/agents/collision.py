"""
Collision detection agent (consolidated loop + summary).
Single agent that orchestrates tools AND produces final output.
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.genai import Client

from ..tools.collision import create_collision_tools


# Agent version
# Breaking: merged loop + summary into single agent
COLLISION_AGENT_VERSION = "4.0.0"


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
        instruction="""You orchestrate collision detection with cross-window analysis.

INPUT:
- ODD Specification: {temp:odd_spec?}
- Tools: list_windows_tool, analyze_collision_tool

TASKS:
1. Call tools: list_windows_tool() then analyze_collision_tool(window_id, odd_context={}) for each
2. Cross-window reasoning: Collision clustering, temporal patterns, severity trends
3. Final statistics: Count collisions, calculate detection rate

OUTPUT (JSON only, no markdown):
{
  "windows_analyzed": [...],
  "overall_collision_stats": {
    "total_windows": <int>,
    "collisions_detected_count": <int>,
    "collision_detection_rate": <float 0-1>
  },
  "observations": [
    "Cross-window: <collision patterns, clustering, temporal context>",
    "Severity: <trends if multiple collisions>",
    "Assessment: <collision-free vs problematic>"
  ],
  "collisions_detected": [
    {
      "window_id": "...",
      "confidence": <float>,
      "evidence": {...}
    }
  ]
}

Be concise.""",
    )
