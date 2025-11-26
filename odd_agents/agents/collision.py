"""
Collision detection agent (consolidated loop + summary).
Single agent that orchestrates tools AND produces final output.
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.genai import Client

from ..tools.collision import create_collision_tools


# Agent version
# Breaking: outputs per-window typed measurements for COD construction
COLLISION_AGENT_VERSION = "5.0.0"


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
        instruction="""You orchestrate collision detection with ODD-aligned measurements.

INPUT:
- ODD Specification (v5.0.0): {temp:odd_spec?} - includes type definitions (range/bool/enum)
- Tools: list_windows_tool, analyze_collision_tool

TASKS:
1. Filter ODD: Extract collision-related dimensions if present (e.g., min_clearance, collision_free)
2. Call tools: list_windows_tool() then analyze_collision_tool(window_id, odd_context={}) for each
3. Per-window measurements: For EACH window, measure collision metrics and tag compliance
4. Cross-window summary: Collision clustering, temporal patterns, severity trends

OUTPUT (JSON only, no markdown):
{
  "per_window_measurements": [
    {
      "window_id": "000",
      "measurements": {
        // If ODD includes collision axes, measure them (e.g., "min_clearance_m": 0.5)
        // Otherwise, use generic collision indicator (e.g., "collision_detected": 0)
      },
      "compliance": {
        // Per-axis compliance tags if ODD has collision axes
        // Otherwise: "collision_detected": "IN_ODD" (0=no collision=compliant)
      }
    }
  ],
  "summary": {
    "temporal_observations": [
      "Cross-window: <collision patterns, clustering, temporal context>",
      "Severity: <trends if multiple collisions>",
      "Assessment: <collision-free vs problematic>"
    ],
    "safety_concerns": [
      "<Collision-based safety issues>"
    ],
    "overall_stats": {
      "total_windows": <int>,
      "collisions_detected_count": <int>,
      "collision_detection_rate": <float 0-1>
    }
  }
}

Per-window measurements enable temporal COD tracking. Use ODD axis types to determine measurement format.""",
    )
