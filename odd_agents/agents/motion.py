"""
Motion analysis agent (consolidated loop + summary).
Single agent that orchestrates tools AND produces final ODD-aligned output.
"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.genai import Client

from ..tools.motion import create_motion_tools


# Agent version
MOTION_AGENT_VERSION = "4.0.0"  # Breaking: merged loop + summary into single agent


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
- ODD Specification: {temp:odd_spec?}
- Tools: list_windows_tool, analyze_motion_tool

TASKS:
1. Filter ODD: Extract ego motion dimensions (accel, speed, stability) from spec
2. Call tools: list_windows_tool() then analyze_motion_tool(window_id, odd_context) for each
3. Cross-window reasoning: Motion sequences, smoothness trends, maneuvers, anomalies
4. ODD measurements: Map to ego dimensions with quantitative values
5. General observations: Motion patterns, sensor quality, safety notes

OUTPUT (JSON only, no markdown):
{
  "windows_analyzed": [...],
  "odd_measurements": {
    // Use ODD ego dimension names as keys
    // Examples: "max_accel_mps2": 0.14, "max_angular_velocity_radps": 0.05
  },
  "observations": [
    "Cross-window: <motion patterns, maneuvers, smoothness trends>",
    "Anomalies: <if any>",
    "Safety: <concerns if any>"
  ],
  "per_window_motion": [...]
}

Be concise. Provide quantitative metrics.""",
    )
