"""
Motion analysis agent (consolidated loop + summary).
Single agent that orchestrates tools AND produces final ODD-aligned output.
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.genai import Client

from ..tools.motion import create_motion_tools


# Agent version
# Breaking: outputs per-window typed measurements for COD construction
MOTION_AGENT_VERSION = "5.0.0"


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
        instruction="""You orchestrate motion analysis with ODD-guided measurements.

INPUT:
- ODD Specification (v5.0.0): {temp:odd_spec?} - includes type definitions (range/bool/enum)
- Tools: list_windows_tool, analyze_motion_tool

TASKS:
1. Filter ODD: Extract ego motion dimensions (accel, speed, stability) from spec
2. Call tools: list_windows_tool() then analyze_motion_tool(window_id, odd_context) for each
3. Per-window measurements: For EACH window, measure ODD ego axes and tag compliance
4. Cross-window summary: Motion sequences, smoothness trends, maneuvers, anomalies

OUTPUT (JSON only, no markdown):
{
  "per_window_measurements": [
    {
      "window_id": "000",
      "measurements": {
        // Use EXACT ODD ego axis names as keys
        // For range: numeric value (e.g., "max_accel_mps2": 0.14)
        // For bool: 0 or 1 (e.g., "emergency_mode": 0)
        // For enum: string label (e.g., "motion_state": "walking")
      },
      "compliance": {
        // Per-axis compliance tags: "IN_ODD", "OUT_ODD", "AT_BOUNDARY"
        "max_accel_mps2": "IN_ODD",
        "max_speed_mps": "AT_BOUNDARY"
      }
    }
  ],
  "summary": {
    "temporal_observations": [
      "Cross-window: <motion patterns, maneuvers, smoothness trends>",
      "Anomalies: <if any>"
    ],
    "safety_concerns": [
      "<Any motion-based safety issues>"
    ]
  }
}

Per-window measurements enable temporal COD tracking. Use ODD axis types to determine measurement format.""",
    )
