"""
Perception analysis agent (consolidated loop + summary).
Single agent that orchestrates tools AND produces final ODD-aligned output.
"""

from pathlib import Path
from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google import genai

from ..tools.perception import create_perception_tools


# Agent version
# Breaking: outputs per-window typed measurements for COD construction
PERCEPTION_AGENT_VERSION = "5.0.0"

# Consolidated prompt
PERCEPTION_AGENT_PROMPT = """You orchestrate perception analysis with ODD-guided measurements.

INPUT:
- ODD Specification (v5.0.0): {temp:odd_spec?} - includes type definitions (range/bool/enum)
- Tools: list_windows_tool, analyze_window_perception_tool

TASKS:
1. Filter ODD: Extract environment/actors dimensions observable from camera + LiDAR BEV
2. Call tools: list_windows_tool() then analyze_window_perception_tool(window_id, odd_context) for each
3. Per-window measurements: For EACH window, measure ODD axes and tag compliance
4. Cross-window summary: Analyze temporal patterns, transitions, safety concerns

OUTPUT (JSON only, no markdown):
{
  "per_window_measurements": [
    {
      "window_id": "000",
      "measurements": {
        // Use EXACT ODD axis names as keys
        // For range: numeric value (e.g., "obstacle_density": 0.35)
        // For enum: string label (e.g., "lighting_conditions": "bright")
        // For bool: 0 or 1 (e.g., "stairs_present": 0)
      },
      "compliance": {
        // Per-axis compliance tags: "IN_ODD", "OUT_ODD", "AT_BOUNDARY"
        "obstacle_density": "IN_ODD",
        "lighting_conditions": "IN_ODD"
      }
    }
  ],
  "summary": {
    "temporal_observations": [
      "Cross-window: <patterns, stability, transitions>",
      "Sensor quality: <issues if any>",
      "Data source: <simulation vs real>"
    ],
    "safety_concerns": [
      "<Any perception-based safety issues>"
    ]
  }
}

Per-window measurements enable temporal COD tracking. Use ODD axis types to determine measurement format."""


def create_perception_agent(scenario_path: Path, genai_client: genai.Client, model: str, api_key: str):
    """Create consolidated perception agent (loop + summary merged)."""
    list_windows, analyze_window = create_perception_tools(
        scenario_path, genai_client, model)

    return Agent(
        name="PerceptionAgent",
        model=Gemini(model=model, api_key=api_key),
        tools=[list_windows, analyze_window],
        output_key="temp:perception_output",
        instruction=PERCEPTION_AGENT_PROMPT,
    )
